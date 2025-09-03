"""Sistema de resiliência com retry e circuit breaker para o Sicoob SDK.

Este módulo implementa padrões de resiliência para lidar com falhas temporárias
e proteger contra cascata de falhas em produção.

Características:
    - Retry com backoff exponencial e jitter
    - Circuit breaker para prevenir cascata de falhas
    - Timeouts configuráveis por operação
    - Métricas de observabilidade
    - Configuração flexível por ambiente

Example:
    >>> from sicoob.resilience import resilient_request
    >>> 
    >>> @resilient_request(max_retries=3, circuit_breaker_enabled=True)
    >>> def make_api_call(session, url):
    ...     return session.get(url)
    ...
    >>> response = make_api_call(session, "https://api.sicoob.com/endpoint")
"""

import random
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, Set, Type, Union

import requests
from requests.adapters import HTTPAdapter

from sicoob.exceptions import (
    CircuitBreakerOpenError, 
    MaxRetriesExceededError,
    SicoobError
)
from sicoob.logging_config import get_logger


class CircuitBreakerState(Enum):
    """Estados do circuit breaker"""
    CLOSED = "closed"      # Funcionando normalmente
    OPEN = "open"          # Bloqueando requisições
    HALF_OPEN = "half_open"  # Testando se voltou a funcionar


class RetryableErrors:
    """Erros que devem ser retentados"""
    
    # Erros de rede/temporários
    NETWORK_ERRORS = (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectTimeout,
        requests.exceptions.ReadTimeout,
    )
    
    # Status HTTP que indicam erro temporário
    TEMPORARY_HTTP_ERRORS = {
        408,  # Request Timeout
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable 
        504,  # Gateway Timeout
    }
    
    # Status HTTP que nunca devem ser retentados
    PERMANENT_HTTP_ERRORS = {
        400,  # Bad Request
        401,  # Unauthorized
        403,  # Forbidden
        404,  # Not Found
        422,  # Unprocessable Entity
    }
    
    @classmethod
    def is_retryable_error(cls, error: Exception) -> bool:
        """Verifica se o erro pode ser retentado"""
        # Erros de rede/conexão
        if isinstance(error, cls.NETWORK_ERRORS):
            return True
            
        # Erros HTTP temporários
        if isinstance(error, requests.exceptions.HTTPError):
            if hasattr(error.response, 'status_code'):
                return error.response.status_code in cls.TEMPORARY_HTTP_ERRORS
                
        return False
    
    @classmethod 
    def is_permanent_error(cls, error: Exception) -> bool:
        """Verifica se o erro é permanente (não deve ser retentado)"""
        if isinstance(error, requests.exceptions.HTTPError):
            if hasattr(error.response, 'status_code'):
                return error.response.status_code in cls.PERMANENT_HTTP_ERRORS
        return False


class CircuitBreaker:
    """Implementa circuit breaker para prevenir cascata de falhas"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        """Inicializa circuit breaker
        
        Args:
            failure_threshold: Número de falhas consecutivas para abrir o circuit
            recovery_timeout: Tempo em segundos para tentar fechar o circuit
            expected_exception: Tipo de exceção que conta como falha
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout  
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitBreakerState.CLOSED
        
        self.logger = get_logger(__name__)
    
    def _can_attempt_reset(self) -> bool:
        """Verifica se pode tentar resetar o circuit breaker"""
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _record_success(self) -> None:
        """Registra uma operação bem-sucedida"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
        self.logger.info(
            "Circuit breaker fechado após sucesso",
            extra={'operation': 'circuit_breaker_closed'}
        )
    
    def _record_failure(self) -> None:
        """Registra uma falha"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(
                f"Circuit breaker aberto após {self.failure_count} falhas consecutivas",
                extra={
                    'operation': 'circuit_breaker_opened',
                    'failure_count': self.failure_count,
                    'threshold': self.failure_threshold
                }
            )
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Executa função com circuit breaker
        
        Args:
            func: Função a ser executada
            *args: Argumentos posicionais
            **kwargs: Argumentos nomeados
            
        Returns:
            Resultado da função
            
        Raises:
            CircuitBreakerOpenError: Se circuit breaker estiver aberto
        """
        if self.state == CircuitBreakerState.OPEN:
            if self._can_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.logger.info(
                    "Circuit breaker em half-open, tentando requisição",
                    extra={'operation': 'circuit_breaker_half_open'}
                )
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker aberto. Próxima tentativa em "
                    f"{self.recovery_timeout - (time.time() - self.last_failure_time):.1f}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        
        except self.expected_exception as e:
            self._record_failure()
            raise


class RetryConfig:
    """Configuração para sistema de retry"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retryable_errors: Optional[Set[Type[Exception]]] = None
    ):
        """Configuração de retry
        
        Args:
            max_retries: Número máximo de tentativas
            base_delay: Delay inicial em segundos
            max_delay: Delay máximo em segundos
            backoff_factor: Fator de multiplicação do backoff
            jitter: Se deve adicionar aleatoriedade ao delay
            retryable_errors: Tipos de erro que podem ser retentados
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retryable_errors = retryable_errors or set(RetryableErrors.NETWORK_ERRORS)
    
    def calculate_delay(self, attempt: int) -> float:
        """Calcula delay para uma tentativa específica"""
        delay = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)
        
        if self.jitter:
            # Adiciona ±25% de jitter
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
            
        return max(0, delay)


class ResilientHTTPAdapter(HTTPAdapter):
    """Adaptador HTTP com retry automático"""
    
    def __init__(self, retry_config: RetryConfig, *args, **kwargs):
        """Inicializa adaptador com configuração de retry
        
        Args:
            retry_config: Configuração de retry
        """
        super().__init__(*args, **kwargs)
        self.retry_config = retry_config
        self.logger = get_logger(__name__)
    
    def send(self, request, **kwargs) -> requests.Response:
        """Envia requisição com retry automático"""
        attempt = 0
        last_exception = None
        
        while attempt <= self.retry_config.max_retries:
            try:
                response = super().send(request, **kwargs)
                
                # Verifica se status indica erro temporário
                if response.status_code in RetryableErrors.TEMPORARY_HTTP_ERRORS:
                    raise requests.exceptions.HTTPError(
                        f"Erro HTTP temporário: {response.status_code}",
                        response=response
                    )
                
                return response
                
            except Exception as e:
                last_exception = e
                
                # Se é erro permanente, não tenta novamente
                if RetryableErrors.is_permanent_error(e):
                    self.logger.info(
                        f"Erro permanente detectado, não tentando novamente: {e}",
                        extra={'operation': 'permanent_error_no_retry'}
                    )
                    raise
                
                # Se não é retentável ou já tentou todas as vezes
                if not RetryableErrors.is_retryable_error(e) or attempt >= self.retry_config.max_retries:
                    break
                
                delay = self.retry_config.calculate_delay(attempt)
                
                self.logger.warning(
                    f"Tentativa {attempt + 1}/{self.retry_config.max_retries + 1} falhou: {e}. "
                    f"Tentando novamente em {delay:.2f}s",
                    extra={
                        'operation': 'retry_attempt',
                        'attempt': attempt + 1,
                        'max_retries': self.retry_config.max_retries + 1,
                        'delay': delay,
                        'error': str(e)
                    }
                )
                
                time.sleep(delay)
                attempt += 1
        
        # Se chegou aqui, todas as tentativas falharam
        raise MaxRetriesExceededError(
            f"Máximo de {self.retry_config.max_retries} tentativas excedido. "
            f"Último erro: {last_exception}"
        ) from last_exception


# Global circuit breakers por endpoint
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(endpoint: str, **kwargs) -> CircuitBreaker:
    """Obtém circuit breaker para um endpoint específico"""
    if endpoint not in _circuit_breakers:
        _circuit_breakers[endpoint] = CircuitBreaker(**kwargs)
    return _circuit_breakers[endpoint]


def create_resilient_session(
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_config: Optional[Dict[str, Any]] = None,
    timeout: Union[float, tuple] = (10, 30)
) -> requests.Session:
    """Cria sessão HTTP com resiliência configurada
    
    Args:
        retry_config: Configuração de retry
        circuit_breaker_config: Configuração do circuit breaker
        timeout: Timeout (connect, read) em segundos
        
    Returns:
        Sessão HTTP configurada com resiliência
    """
    session = requests.Session()
    
    # Configuração padrão de retry
    if retry_config is None:
        retry_config = RetryConfig()
    
    # Adaptador com retry
    adapter = ResilientHTTPAdapter(retry_config)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Timeout padrão
    session.timeout = timeout
    
    return session


def resilient_request(
    max_retries: int = 3,
    circuit_breaker_enabled: bool = True,
    circuit_breaker_config: Optional[Dict[str, Any]] = None,
    retry_config: Optional[RetryConfig] = None
):
    """Decorator para adicionar resiliência a funções de requisição HTTP
    
    Args:
        max_retries: Número máximo de retries
        circuit_breaker_enabled: Se deve usar circuit breaker
        circuit_breaker_config: Configuração do circuit breaker
        retry_config: Configuração detalhada de retry
        
    Example:
        >>> @resilient_request(max_retries=3, circuit_breaker_enabled=True)
        >>> def get_user_data(session, user_id):
        ...     return session.get(f"/users/{user_id}")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Usa configuração personalizada ou padrão
            config = retry_config or RetryConfig(max_retries=max_retries)
            
            # Circuit breaker por função
            if circuit_breaker_enabled:
                cb_config = circuit_breaker_config or {}
                circuit_breaker = get_circuit_breaker(func.__name__, **cb_config)
                
                return circuit_breaker.call(func, *args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        return wrapper
    return decorator