"""Testes para módulo de resiliência."""

from unittest.mock import Mock, patch

import pytest
import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from sicoob.exceptions import (
    CircuitBreakerOpenError,
    MaxRetriesExceededError,
)
from sicoob.resilience import (
    CircuitBreaker,
    CircuitBreakerState,
    ResilientHTTPAdapter,
    RetryableErrors,
    RetryConfig,
    create_resilient_session,
    get_circuit_breaker,
    resilient_request,
)


class TestRetryableErrors:
    """Testes para classificação de erros retentáveis."""

    def test_network_errors_are_retryable(self):
        """Testa que erros de rede são retentáveis."""
        # Testa cada tipo de erro de rede
        network_errors = [
            ConnectionError('Connection failed'),
            Timeout('Request timeout'),
            requests.exceptions.ConnectTimeout('Connect timeout'),
            requests.exceptions.ReadTimeout('Read timeout'),
        ]

        for error in network_errors:
            assert RetryableErrors.is_retryable_error(error) is True

    def test_temporary_http_errors_are_retryable(self):
        """Testa que erros HTTP temporários são retentáveis."""
        # Mock response com status codes temporários
        for status_code in [408, 429, 500, 502, 503, 504]:
            response_mock = Mock()
            response_mock.status_code = status_code

            http_error = HTTPError('HTTP Error')
            http_error.response = response_mock

            assert RetryableErrors.is_retryable_error(http_error) is True

    def test_permanent_http_errors_are_not_retryable(self):
        """Testa que erros HTTP permanentes não são retentáveis."""
        for status_code in [400, 401, 403, 404, 422]:
            response_mock = Mock()
            response_mock.status_code = status_code

            http_error = HTTPError('HTTP Error')
            http_error.response = response_mock

            assert RetryableErrors.is_permanent_error(http_error) is True
            assert RetryableErrors.is_retryable_error(http_error) is False

    def test_unknown_errors_are_not_retryable(self):
        """Testa que erros desconhecidos não são retentáveis."""
        unknown_error = ValueError('Some value error')
        assert RetryableErrors.is_retryable_error(unknown_error) is False
        assert RetryableErrors.is_permanent_error(unknown_error) is False


class TestCircuitBreaker:
    """Testes para circuit breaker."""

    def test_circuit_breaker_initialization(self):
        """Testa inicialização do circuit breaker."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 30
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.last_failure_time is None

    def test_successful_call(self):
        """Testa chamada bem-sucedida."""
        cb = CircuitBreaker()

        def success_func():
            return 'success'

        result = cb.call(success_func)
        assert result == 'success'
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_opens_after_failures(self):
        """Testa que circuit breaker abre após falhas consecutivas."""
        cb = CircuitBreaker(failure_threshold=3)

        def failing_func():
            raise Exception('Test failure')

        # Primeiras 2 falhas não abrem o circuit
        for i in range(2):
            with pytest.raises(Exception):
                cb.call(failing_func)
            assert cb.state == CircuitBreakerState.CLOSED
            assert cb.failure_count == i + 1

        # 3ª falha abre o circuit
        with pytest.raises(Exception):
            cb.call(failing_func)

        assert cb.state == CircuitBreakerState.OPEN
        assert cb.failure_count == 3

    def test_circuit_breaker_blocks_when_open(self):
        """Testa que circuit breaker bloqueia chamadas quando aberto."""
        cb = CircuitBreaker(failure_threshold=1)

        def failing_func():
            raise Exception('Test failure')

        # Causa falha para abrir circuit
        with pytest.raises(Exception):
            cb.call(failing_func)

        assert cb.state == CircuitBreakerState.OPEN

        # Próxima chamada deve ser bloqueada
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(failing_func)

    @patch('time.time')
    def test_circuit_breaker_half_open_after_timeout(self, mock_time):
        """Testa transição para half-open após timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)

        def failing_func():
            raise Exception('Test failure')

        # Simula tempo inicial
        mock_time.return_value = 1000

        # Abre o circuit
        with pytest.raises(Exception):
            cb.call(failing_func)

        assert cb.state == CircuitBreakerState.OPEN

        # Simula passagem do tempo de recovery
        mock_time.return_value = 1000 + 61  # 61 segundos depois

        # Próxima chamada deve ir para half-open
        with pytest.raises(Exception):
            cb.call(failing_func)

        # Estado deve ter mudado para HALF_OPEN primeiro
        # (mas volta para OPEN devido à falha)
        assert cb.state == CircuitBreakerState.OPEN

    @patch('time.time')
    def test_circuit_breaker_closes_after_success_in_half_open(self, mock_time):
        """Testa que circuit fecha após sucesso em half-open."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)

        # Simula tempo
        mock_time.return_value = 1000

        # Abre o circuit com falha
        def failing_func():
            raise Exception('Test failure')

        with pytest.raises(Exception):
            cb.call(failing_func)

        assert cb.state == CircuitBreakerState.OPEN

        # Simula passagem do tempo
        mock_time.return_value = 1061

        # Chama função que vai ter sucesso
        def success_func():
            return 'success'

        result = cb.call(success_func)

        assert result == 'success'
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0


class TestRetryConfig:
    """Testes para configuração de retry."""

    def test_retry_config_defaults(self):
        """Testa valores padrão da configuração."""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True

    def test_delay_calculation_without_jitter(self):
        """Testa cálculo de delay sem jitter."""
        config = RetryConfig(base_delay=1.0, backoff_factor=2.0, jitter=False)

        assert config.calculate_delay(0) == 1.0  # 1 * 2^0
        assert config.calculate_delay(1) == 2.0  # 1 * 2^1
        assert config.calculate_delay(2) == 4.0  # 1 * 2^2
        assert config.calculate_delay(3) == 8.0  # 1 * 2^3

    def test_delay_calculation_with_max_delay(self):
        """Testa que delay não excede o máximo."""
        config = RetryConfig(base_delay=10.0, max_delay=15.0, jitter=False)

        assert config.calculate_delay(0) == 10.0
        assert config.calculate_delay(1) == 15.0  # Limitado pelo max_delay
        assert config.calculate_delay(2) == 15.0  # Limitado pelo max_delay

    def test_delay_calculation_with_jitter(self):
        """Testa que jitter adiciona aleatoriedade."""
        config = RetryConfig(base_delay=4.0, jitter=True)

        delays = [config.calculate_delay(0) for _ in range(10)]

        # Todos devem ser diferentes devido ao jitter
        assert len(set(delays)) > 1

        # Todos devem estar no range esperado (±25% de 4.0)
        for delay in delays:
            assert 3.0 <= delay <= 5.0


class TestResilientHTTPAdapter:
    """Testes para adaptador HTTP resiliente."""

    def test_successful_request_no_retry(self):
        """Testa requisição bem-sucedida sem retry."""
        config = RetryConfig(max_retries=3)
        adapter = ResilientHTTPAdapter(config)

        # Mock da resposta bem-sucedida
        with patch.object(adapter, 'send', wraps=adapter.send) as mock_send:
            mock_response = Mock()
            mock_response.status_code = 200

            # Mock do método pai
            with patch(
                'requests.adapters.HTTPAdapter.send', return_value=mock_response
            ):
                request = Mock()
                response = adapter.send(request)

                assert response.status_code == 200
                # Send foi chamado apenas uma vez (sem retries)
                assert mock_send.call_count == 1

    def test_retry_on_temporary_error(self):
        """Testa retry em erro temporário."""
        config = RetryConfig(max_retries=2, base_delay=0.01)  # Delay baixo para teste
        adapter = ResilientHTTPAdapter(config)

        with patch('time.sleep') as mock_sleep:  # Mock sleep para acelerar teste
            # Mock de resposta com erro temporário seguido de sucesso
            responses = [
                Mock(status_code=503),  # Service Unavailable
                Mock(status_code=200),  # Success
            ]

            with patch('requests.adapters.HTTPAdapter.send', side_effect=responses):
                request = Mock()
                response = adapter.send(request)

                assert response.status_code == 200
                assert mock_sleep.call_count == 1  # 1 retry

    def test_no_retry_on_permanent_error(self):
        """Testa que não tenta novamente em erro permanente."""
        config = RetryConfig(max_retries=3)
        adapter = ResilientHTTPAdapter(config)

        # Mock de resposta com erro permanente
        mock_response = Mock()
        mock_response.status_code = 400

        http_error = HTTPError('Bad Request')
        http_error.response = mock_response

        with patch('requests.adapters.HTTPAdapter.send', side_effect=http_error):
            request = Mock()

            with pytest.raises(HTTPError):
                adapter.send(request)

    def test_max_retries_exceeded(self):
        """Testa que exceção é lançada quando retries se esgotam."""
        config = RetryConfig(max_retries=2, base_delay=0.01)
        adapter = ResilientHTTPAdapter(config)

        with patch('time.sleep'):
            # Mock que sempre falha
            connection_error = ConnectionError('Connection failed')

            with patch(
                'requests.adapters.HTTPAdapter.send', side_effect=connection_error
            ):
                request = Mock()

                with pytest.raises(MaxRetriesExceededError):
                    adapter.send(request)


class TestUtilityFunctions:
    """Testes para funções utilitárias."""

    def test_get_circuit_breaker(self):
        """Testa obtenção de circuit breaker por endpoint."""
        cb1 = get_circuit_breaker('endpoint1')
        cb2 = get_circuit_breaker('endpoint1')  # Mesmo endpoint
        cb3 = get_circuit_breaker('endpoint2')  # Endpoint diferente

        # Mesmo endpoint retorna a mesma instância
        assert cb1 is cb2

        # Endpoints diferentes retornam instâncias diferentes
        assert cb1 is not cb3

    def test_create_resilient_session(self):
        """Testa criação de sessão resiliente."""
        retry_config = RetryConfig(max_retries=5)
        session = create_resilient_session(retry_config=retry_config, timeout=(5, 15))

        assert isinstance(session, requests.Session)
        assert session.timeout == (5, 15)

        # Verifica se adaptador foi configurado
        http_adapter = session.get_adapter('http://example.com')
        https_adapter = session.get_adapter('https://example.com')

        assert isinstance(http_adapter, ResilientHTTPAdapter)
        assert isinstance(https_adapter, ResilientHTTPAdapter)

    def test_create_resilient_session_with_defaults(self):
        """Testa criação de sessão com configurações padrão."""
        session = create_resilient_session()

        assert isinstance(session, requests.Session)
        assert session.timeout == (10, 30)


class TestResilientRequestDecorator:
    """Testes para decorator resilient_request."""

    def test_decorator_without_circuit_breaker(self):
        """Testa decorator sem circuit breaker."""

        @resilient_request(circuit_breaker_enabled=False)
        def test_function(value):
            return value * 2

        result = test_function(5)
        assert result == 10

    def test_decorator_with_circuit_breaker(self):
        """Testa decorator com circuit breaker."""

        @resilient_request(circuit_breaker_enabled=True, max_retries=1)
        def test_function(should_fail=False):
            if should_fail:
                raise Exception('Test failure')
            return 'success'

        # Primeira chamada bem-sucedida
        result = test_function(should_fail=False)
        assert result == 'success'

        # Chamada que falha
        with pytest.raises(Exception):
            test_function(should_fail=True)

    def test_decorator_circuit_breaker_opens(self):
        """Testa que decorator abre circuit breaker após falhas."""

        @resilient_request(
            circuit_breaker_enabled=True,
            circuit_breaker_config={'failure_threshold': 1},
        )
        def failing_function():
            raise Exception('Always fails')

        # Primeira falha abre o circuit
        with pytest.raises(Exception):
            failing_function()

        # Segunda chamada deve ser bloqueada
        with pytest.raises(CircuitBreakerOpenError):
            failing_function()


class TestIntegration:
    """Testes de integração."""

    def test_full_resilience_flow(self):
        """Testa fluxo completo de resiliência."""
        # Simples teste que o sistema existe e funciona
        config = RetryConfig(max_retries=1, base_delay=0.01)
        session = create_resilient_session(retry_config=config)

        assert isinstance(session, requests.Session)
        assert session.timeout == (10, 30)
