"""Testes para sistema de resiliência (retry e circuit breaker)"""

import time
from unittest.mock import Mock, patch
from unittest import mock

import pytest
import requests

from sicoob.exceptions import (
    CircuitBreakerOpenError,
    MaxRetriesExceededError,
)
from sicoob.resilience import (
    CircuitBreaker,
    CircuitBreakerState,
    RetryConfig,
    RetryableErrors,
    ResilientHTTPAdapter,
    create_resilient_session,
    resilient_request,
)


class TestRetryableErrors:
    """Testes para classificação de erros retentáveis"""

    def test_network_errors_are_retryable(self):
        """Testa se erros de rede são classificados como retentáveis"""
        errors = [
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.Timeout("Request timed out"),
            requests.exceptions.ConnectTimeout("Connection timed out"),
            requests.exceptions.ReadTimeout("Read timed out"),
        ]
        
        for error in errors:
            assert RetryableErrors.is_retryable_error(error)
            assert not RetryableErrors.is_permanent_error(error)

    def test_temporary_http_errors_are_retryable(self):
        """Testa se erros HTTP temporários são retentáveis"""
        temporary_codes = [408, 429, 500, 502, 503, 504]
        
        for code in temporary_codes:
            response = Mock()
            response.status_code = code
            error = requests.exceptions.HTTPError(response=response)
            
            assert RetryableErrors.is_retryable_error(error)
            assert not RetryableErrors.is_permanent_error(error)

    def test_permanent_http_errors_not_retryable(self):
        """Testa se erros HTTP permanentes não são retentáveis"""
        permanent_codes = [400, 401, 403, 404, 422]
        
        for code in permanent_codes:
            response = Mock()
            response.status_code = code
            error = requests.exceptions.HTTPError(response=response)
            
            assert not RetryableErrors.is_retryable_error(error)
            assert RetryableErrors.is_permanent_error(error)

    def test_other_errors_not_retryable(self):
        """Testa se outros erros não são retentáveis por padrão"""
        error = ValueError("Invalid value")
        
        assert not RetryableErrors.is_retryable_error(error)
        assert not RetryableErrors.is_permanent_error(error)


class TestRetryConfig:
    """Testes para configuração de retry"""

    def test_default_config(self):
        """Testa configuração padrão de retry"""
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True

    def test_delay_calculation(self):
        """Testa cálculo de delay com backoff exponencial"""
        config = RetryConfig(
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=10.0,
            jitter=False
        )
        
        # Primeira tentativa: 1.0s
        assert config.calculate_delay(0) == 1.0
        
        # Segunda tentativa: 2.0s
        assert config.calculate_delay(1) == 2.0
        
        # Terceira tentativa: 4.0s
        assert config.calculate_delay(2) == 4.0
        
        # Quarta tentativa: limitado a max_delay
        assert config.calculate_delay(3) == 8.0
        assert config.calculate_delay(4) == 10.0  # Limitado por max_delay

    def test_delay_with_jitter(self):
        """Testa se jitter adiciona aleatoriedade ao delay"""
        config = RetryConfig(base_delay=4.0, jitter=True)
        
        delays = [config.calculate_delay(0) for _ in range(100)]
        
        # Verifica se há variação nos delays
        assert len(set(delays)) > 1, "Jitter deveria produzir delays diferentes"
        
        # Verifica se delays estão no range esperado (±25% de 4.0s)
        for delay in delays:
            assert 3.0 <= delay <= 5.0, f"Delay {delay} fora do range esperado"


class TestCircuitBreaker:
    """Testes para circuit breaker"""

    def test_initial_state_closed(self):
        """Testa se circuit breaker inicia fechado"""
        cb = CircuitBreaker()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_success_keeps_closed(self):
        """Testa se sucessos mantêm circuit breaker fechado"""
        cb = CircuitBreaker(failure_threshold=3)
        
        def successful_operation():
            return "success"
        
        result = cb.call(successful_operation)
        
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_failures_open_circuit(self):
        """Testa se falhas consecutivas abrem circuit breaker"""
        cb = CircuitBreaker(failure_threshold=3)
        
        def failing_operation():
            raise Exception("Simulated failure")
        
        # Primeira e segunda falhas: circuit ainda fechado
        for i in range(2):
            with pytest.raises(Exception):
                cb.call(failing_operation)
            assert cb.state == CircuitBreakerState.CLOSED
            assert cb.failure_count == i + 1
        
        # Terceira falha: circuit abre
        with pytest.raises(Exception):
            cb.call(failing_operation)
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.failure_count == 3

    def test_open_circuit_rejects_calls(self):
        """Testa se circuit aberto rejeita chamadas"""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        
        # Causa falha para abrir circuit
        with pytest.raises(Exception):
            cb.call(lambda: 1/0)
        
        # Próxima chamada deve ser rejeitada
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: "success")

    def test_circuit_recovers_after_timeout(self):
        """Testa se circuit breaker se recupera após timeout"""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)  # 100ms
        
        # Abre circuit
        with pytest.raises(Exception):
            cb.call(lambda: 1/0)
        assert cb.state == CircuitBreakerState.OPEN
        
        # Espera timeout
        time.sleep(0.2)
        
        # Próxima chamada deveria ir para HALF_OPEN
        result = cb.call(lambda: "recovered")
        assert result == "recovered"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0


class TestResilientHTTPAdapter:
    """Testes para adaptador HTTP resiliente"""

    def test_successful_request_no_retry(self):
        """Testa requisição bem-sucedida sem retry"""
        retry_config = RetryConfig(max_retries=3)
        adapter = ResilientHTTPAdapter(retry_config)
        
        # Mock de requisição bem-sucedida
        request = Mock()
        response = Mock()
        response.status_code = 200
        
        with patch.object(adapter.__class__.__bases__[0], 'send', return_value=response):
            result = adapter.send(request)
        
        assert result == response

    def test_retryable_error_triggers_retry(self):
        """Testa se erro retentável dispara retry"""
        retry_config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        adapter = ResilientHTTPAdapter(retry_config)
        
        request = Mock()
        
        # Mock que falha 2 vezes e depois sucede
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise requests.exceptions.ConnectionError("Connection failed")
            response = Mock()
            response.status_code = 200
            return response
        
        with patch.object(adapter.__class__.__bases__[0], 'send', side_effect=side_effect):
            result = adapter.send(request)
        
        # Deveria ter tentado 3 vezes (1 inicial + 2 retries)
        assert call_count == 3
        assert result.status_code == 200

    def test_permanent_error_no_retry(self):
        """Testa se erro permanente não dispara retry"""
        retry_config = RetryConfig(max_retries=3)
        adapter = ResilientHTTPAdapter(retry_config)
        
        request = Mock()
        response = Mock()
        response.status_code = 400
        error = requests.exceptions.HTTPError(response=response)
        
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise error
        
        with patch.object(adapter.__class__.__bases__[0], 'send', side_effect=side_effect):
            with pytest.raises(requests.exceptions.HTTPError):
                adapter.send(request)
        
        # Deveria ter tentado apenas 1 vez
        assert call_count == 1

    def test_max_retries_exceeded(self):
        """Testa exceção quando máximo de retries é excedido"""
        retry_config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        adapter = ResilientHTTPAdapter(retry_config)
        
        request = Mock()
        
        def side_effect(*args, **kwargs):
            raise requests.exceptions.ConnectionError("Connection failed")
        
        with patch.object(adapter.__class__.__bases__[0], 'send', side_effect=side_effect):
            with pytest.raises(MaxRetriesExceededError) as exc_info:
                adapter.send(request)
        
        assert "2 tentativas excedido" in str(exc_info.value)


class TestCreateResilientSession:
    """Testes para criação de sessão resiliente"""

    def test_creates_session_with_resilient_adapters(self):
        """Testa se sessão é criada com adaptadores resilientes"""
        session = create_resilient_session()
        
        assert isinstance(session, requests.Session)
        
        # Verifica se adaptadores HTTP/HTTPS são resilientes
        http_adapter = session.get_adapter("http://example.com")
        https_adapter = session.get_adapter("https://example.com")
        
        assert isinstance(http_adapter, ResilientHTTPAdapter)
        assert isinstance(https_adapter, ResilientHTTPAdapter)

    def test_session_has_default_timeout(self):
        """Testa se sessão tem timeout padrão configurado"""
        session = create_resilient_session()
        assert session.timeout == (10, 30)

    def test_custom_timeout_configuration(self):
        """Testa configuração de timeout personalizado"""
        custom_timeout = (5, 15)
        session = create_resilient_session(timeout=custom_timeout)
        assert session.timeout == custom_timeout


@pytest.mark.integration
class TestResilientRequestDecorator:
    """Testes de integração para decorator de requisição resiliente"""

    def test_decorator_applies_circuit_breaker(self):
        """Testa se decorator aplica circuit breaker corretamente"""
        call_count = 0
        
        @resilient_request(max_retries=2, circuit_breaker_enabled=True)
        def sometimes_failing_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First failure")
            return "success"
        
        # Primeira chamada falha
        with pytest.raises(Exception, match="First failure"):
            sometimes_failing_function()
        
        # Segunda chamada deveria funcionar
        result = sometimes_failing_function()
        assert result == "success"

    def test_decorator_with_circuit_breaker(self):
        """Testa decorator com circuit breaker habilitado"""
        @resilient_request(max_retries=1, circuit_breaker_enabled=True)
        def operation():
            return "success"
        
        # Primeira chamada deveria funcionar
        result = operation()
        assert result == "success"