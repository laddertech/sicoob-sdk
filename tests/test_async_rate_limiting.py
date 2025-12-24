"""Testes para rate limiting, circuit breaker e retry no async_client."""

import asyncio
import time

import pytest

from sicoob.async_client import (
    AsyncCircuitBreaker,
    gather_with_concurrency,
    gather_with_rate_limit,
)
from sicoob.exceptions import CircuitBreakerOpenError


class TestGatherWithRateLimit:
    """Testes para a função gather_with_rate_limit."""

    @pytest.mark.asyncio
    async def test_respects_rate_limit(self):
        """Verifica que respeita o rate limit entre requisições."""
        execution_times: list[float] = []

        async def track_time():
            execution_times.append(time.time())
            return 'ok'

        tasks = [track_time() for _ in range(5)]

        # 2 requisições por segundo = 500ms entre cada
        await gather_with_rate_limit(
            tasks,
            max_concurrency=5,
            requests_per_second=2.0,
        )

        assert len(execution_times) == 5

        # Verifica intervalos entre execuções (deve ser ~500ms)
        for i in range(1, len(execution_times)):
            interval = execution_times[i] - execution_times[i - 1]
            # Aceita variação de 100ms para tolerância
            assert interval >= 0.4, f'Intervalo {i} muito curto: {interval:.3f}s'

    @pytest.mark.asyncio
    async def test_respects_concurrency_limit(self):
        """Verifica que respeita o limite de concorrência."""
        concurrent_count = 0
        max_concurrent = 0

        async def track_concurrency():
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.1)
            concurrent_count -= 1
            return 'ok'

        tasks = [track_concurrency() for _ in range(10)]

        await gather_with_rate_limit(
            tasks,
            max_concurrency=3,
            requests_per_second=100.0,  # Alta taxa para não limitar
        )

        assert max_concurrent <= 3

    @pytest.mark.asyncio
    async def test_stagger_delay_distributes_tasks(self):
        """Verifica que stagger_delay distribui as tasks.

        Com stagger_delay=0.1 e max_concurrency=3:
        - Task 0: delay = 0 (index 0, não aplica)
        - Task 1: delay = 0.1 * (1 % 3) = 0.1
        - Task 2: delay = 0.1 * (2 % 3) = 0.2
        - Task 3: delay = 0.1 * (3 % 3) = 0
        - Task 4: delay = 0.1 * (4 % 3) = 0.1
        - Task 5: delay = 0.1 * (5 % 3) = 0.2
        """
        start_times: list[float] = []
        execution_order: list[int] = []

        async def track_start(index: int):
            start_times.append(time.time())
            execution_order.append(index)
            return 'ok'

        # Importante: capturar o índice no momento da criação
        tasks = [track_start(i) for i in range(6)]
        start = time.time()

        await gather_with_rate_limit(
            tasks,
            max_concurrency=3,
            requests_per_second=100.0,  # Alta taxa para não interferir
            stagger_delay=0.1,  # 100ms entre ondas
        )

        # Primeira task deve iniciar imediatamente
        assert start_times[0] - start < 0.1

        # Verificar que o tempo total é maior que 0 (houve staggering)
        total_time = max(start_times) - min(start_times)
        # Com stagger de 0.1 e 6 tasks, deve ter algum spread
        assert total_time > 0.05, f'Tempo total muito curto: {total_time}'

    @pytest.mark.asyncio
    async def test_returns_results_in_order(self):
        """Verifica que retorna resultados na ordem das tasks."""

        async def numbered_task(n: int):
            await asyncio.sleep(0.05 * (5 - n))  # Tasks mais lentas primeiro
            return n

        tasks = [numbered_task(i) for i in range(5)]

        results = await gather_with_rate_limit(
            tasks,
            max_concurrency=5,
            requests_per_second=100.0,
        )

        assert results == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_empty_task_list(self):
        """Verifica que lista vazia retorna lista vazia."""
        results = await gather_with_rate_limit(
            [],
            max_concurrency=5,
            requests_per_second=5.0,
        )
        assert results == []


class TestAsyncCircuitBreaker:
    """Testes para o AsyncCircuitBreaker."""

    @pytest.mark.asyncio
    async def test_starts_closed(self):
        """Verifica que inicia no estado fechado."""
        cb = AsyncCircuitBreaker()
        assert cb.state == AsyncCircuitBreaker.CLOSED
        assert cb.failures == 0

    @pytest.mark.asyncio
    async def test_opens_after_failures(self):
        """Verifica que abre após atingir threshold de falhas."""
        cb = AsyncCircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        async def failing_func():
            raise ValueError('Erro simulado')

        # Falha 3 vezes
        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        # Agora o circuit breaker deve estar aberto
        assert cb.state == AsyncCircuitBreaker.OPEN
        assert cb.failures == 3

    @pytest.mark.asyncio
    async def test_blocks_when_open(self):
        """Verifica que bloqueia requisições quando aberto."""
        cb = AsyncCircuitBreaker(failure_threshold=2, recovery_timeout=10.0)

        async def failing_func():
            raise ValueError('Erro simulado')

        # Abre o circuit breaker
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        # Próxima chamada deve ser bloqueada
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(failing_func)

    @pytest.mark.asyncio
    async def test_half_open_after_recovery_timeout(self):
        """Verifica que entra em half-open após recovery_timeout."""
        cb = AsyncCircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        async def failing_func():
            raise ValueError('Erro simulado')

        async def success_func():
            return 'ok'

        # Abre o circuit breaker
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        assert cb.state == AsyncCircuitBreaker.OPEN

        # Aguarda recovery timeout
        await asyncio.sleep(0.15)

        # Próxima chamada deve ser permitida (half-open)
        result = await cb.call(success_func)
        assert result == 'ok'
        assert cb.state == AsyncCircuitBreaker.CLOSED

    @pytest.mark.asyncio
    async def test_closes_after_success_in_half_open(self):
        """Verifica que fecha após sucesso em half-open."""
        cb = AsyncCircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        async def failing_func():
            raise ValueError('Erro')

        async def success_func():
            return 'ok'

        # Abre
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        # Aguarda e testa
        await asyncio.sleep(0.15)
        result = await cb.call(success_func)

        assert result == 'ok'
        assert cb.state == AsyncCircuitBreaker.CLOSED
        assert cb.failures == 0

    @pytest.mark.asyncio
    async def test_reset(self):
        """Verifica que reset restaura estado inicial."""
        cb = AsyncCircuitBreaker(failure_threshold=2)

        async def failing_func():
            raise ValueError('Erro')

        # Abre
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        assert cb.state == AsyncCircuitBreaker.OPEN

        # Reset
        cb.reset()

        assert cb.state == AsyncCircuitBreaker.CLOSED
        assert cb.failures == 0
        assert cb.last_failure_time is None


class TestRetryDefaults:
    """Testes para os novos valores default de retry."""

    def test_default_max_tentativas_is_3(self):
        """Verifica que max_tentativas default é 3."""
        from unittest.mock import MagicMock

        from sicoob.async_client import AsyncAPIClient

        oauth_mock = MagicMock()
        client = AsyncAPIClient(oauth_client=oauth_mock)

        assert client.retry_config['max_tentativas'] == 3

    def test_default_delay_inicial_is_half_second(self):
        """Verifica que delay_inicial default é 0.5."""
        from unittest.mock import MagicMock

        from sicoob.async_client import AsyncAPIClient

        oauth_mock = MagicMock()
        client = AsyncAPIClient(oauth_client=oauth_mock)

        assert client.retry_config['delay_inicial'] == 0.5

    def test_default_delay_maximo_is_5_seconds(self):
        """Verifica que delay_maximo default é 5.0."""
        from unittest.mock import MagicMock

        from sicoob.async_client import AsyncAPIClient

        oauth_mock = MagicMock()
        client = AsyncAPIClient(oauth_client=oauth_mock)

        assert client.retry_config['delay_maximo'] == 5.0


class TestDelayMaximo:
    """Testes para o delay_maximo no cálculo de backoff."""

    def test_delay_maximo_caps_backoff(self):
        """Verifica que delay_maximo limita o backoff exponencial."""
        from unittest.mock import MagicMock

        from sicoob.async_client import AsyncAPIClient

        oauth_mock = MagicMock()
        client = AsyncAPIClient(
            oauth_client=oauth_mock,
            retry_config={
                'max_tentativas': 10,
                'delay_inicial': 1.0,
                'delay_maximo': 3.0,
                'backoff_exponencial': True,
                'codigos_retry': [500],
            },
        )

        # Tentativa 0: 1.0 * 2^0 = 1.0 (sem cap)
        # Tentativa 1: 1.0 * 2^1 = 2.0 (sem cap)
        # Tentativa 2: 1.0 * 2^2 = 4.0 → cap em 3.0
        # Tentativa 5: 1.0 * 2^5 = 32.0 → cap em 3.0

        # O delay tem jitter de ±25%, então verificamos range
        for tentativa in range(10):
            delay = client._calcular_delay_retry(tentativa)
            # Delay máximo com jitter de +25% = 3.0 * 1.25 = 3.75
            assert delay <= 3.75, (
                f'Delay na tentativa {tentativa} excedeu máximo: {delay}'
            )
            # Mínimo é 0.1
            assert delay >= 0.1

    def test_delay_without_cap(self):
        """Verifica backoff exponencial sem cap funciona corretamente."""
        from unittest.mock import MagicMock

        from sicoob.async_client import AsyncAPIClient

        oauth_mock = MagicMock()
        client = AsyncAPIClient(
            oauth_client=oauth_mock,
            retry_config={
                'max_tentativas': 5,
                'delay_inicial': 0.5,
                'delay_maximo': 100.0,  # Cap alto para não limitar
                'backoff_exponencial': True,
                'codigos_retry': [500],
            },
        )

        # Tentativa 3: 0.5 * 2^3 = 4.0
        # Com jitter ±25%: 3.0 a 5.0
        delay = client._calcular_delay_retry(3)
        assert 3.0 <= delay <= 5.0


class TestCircuitBreakerIntegration:
    """Testes de integração do circuit breaker com AsyncAPIClient."""

    def test_circuit_breaker_config_creates_instance(self):
        """Verifica que circuit_breaker_config cria instância."""
        from unittest.mock import MagicMock

        from sicoob.async_client import AsyncAPIClient, AsyncCircuitBreaker

        oauth_mock = MagicMock()
        client = AsyncAPIClient(
            oauth_client=oauth_mock,
            circuit_breaker_config={
                'failure_threshold': 3,
                'recovery_timeout': 60.0,
            },
        )

        assert client._circuit_breaker is not None
        assert isinstance(client._circuit_breaker, AsyncCircuitBreaker)
        assert client._circuit_breaker.failure_threshold == 3
        assert client._circuit_breaker.recovery_timeout == 60.0

    def test_no_circuit_breaker_by_default(self):
        """Verifica que circuit breaker não é criado por padrão."""
        from unittest.mock import MagicMock

        from sicoob.async_client import AsyncAPIClient

        oauth_mock = MagicMock()
        client = AsyncAPIClient(oauth_client=oauth_mock)

        assert client._circuit_breaker is None


class TestGatherWithConcurrencyStillWorks:
    """Verifica que gather_with_concurrency original ainda funciona."""

    @pytest.mark.asyncio
    async def test_basic_functionality(self):
        """Verifica funcionalidade básica."""

        async def simple_task(n: int):
            await asyncio.sleep(0.01)
            return n * 2

        tasks = [simple_task(i) for i in range(5)]
        results = await gather_with_concurrency(tasks, max_concurrency=3)

        assert results == [0, 2, 4, 6, 8]

    @pytest.mark.asyncio
    async def test_respects_concurrency(self):
        """Verifica que respeita limite de concorrência."""
        concurrent = 0
        max_concurrent = 0

        async def track_task():
            nonlocal concurrent, max_concurrent
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
            await asyncio.sleep(0.05)
            concurrent -= 1
            return 'ok'

        tasks = [track_task() for _ in range(10)]
        await gather_with_concurrency(tasks, max_concurrency=2)

        assert max_concurrent <= 2
