"""Cliente HTTP assíncrono para o Sicoob SDK.

Este módulo fornece funcionalidades de requisições assíncronas para melhorar
a performance em cenários de high-throughput, permitindo múltiplas requisições
concorrentes.

Classes:
    AsyncAPIClient: Cliente base para requisições HTTP assíncronas
    AsyncSicoob: Cliente principal assíncrono para API do Sicoob

Example:
    >>> import asyncio
    >>> from sicoob.async_client import AsyncSicoob
    >>>
    >>> async def main():
    ...     async with AsyncSicoob(client_id="123", certificado_pfx=pfx) as client:
    ...         # Requisições concorrentes
    ...         tasks = [
    ...             client.conta_corrente.get_extrato(inicio, fim)
    ...             for inicio, fim in date_ranges
    ...         ]
    ...         results = await asyncio.gather(*tasks)
    >>> asyncio.run(main())
"""

import asyncio
import json
import logging
import os
import ssl
import tempfile
import time
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from aiohttp import ClientSession, ClientTimeout, TCPConnector

from sicoob.auth import OAuth2Client
from sicoob.config import Environment, SicoobConfig
from sicoob.exceptions import CircuitBreakerOpenError, SicoobError

# Logger para debugging
logger = logging.getLogger(__name__)


class AsyncCircuitBreaker:
    """Circuit breaker assíncrono para proteção contra falhas em cascata.

    O circuit breaker monitora falhas consecutivas e "abre" o circuito quando
    um threshold é atingido, bloqueando novas requisições temporariamente.

    Estados:
        - CLOSED: Operação normal, requisições passam
        - OPEN: Bloqueando requisições (muitas falhas recentes)
        - HALF_OPEN: Testando se o serviço voltou ao normal

    Example:
        >>> cb = AsyncCircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
        >>> try:
        ...     result = await cb.call(make_api_request, url, data)
        ... except CircuitBreakerOpenError:
        ...     print("Serviço temporariamente indisponível")
    """

    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
    ) -> None:
        """Inicializa o circuit breaker.

        Args:
            failure_threshold: Número de falhas consecutivas para abrir o circuito
            recovery_timeout: Tempo em segundos para tentar fechar o circuito
            half_open_max_calls: Número máximo de chamadas em estado half-open
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.failures = 0
        self.state = self.CLOSED
        self.last_failure_time: float | None = None
        self.half_open_calls = 0
        self._lock = asyncio.Lock()

    def _can_attempt_reset(self) -> bool:
        """Verifica se pode tentar resetar o circuit breaker."""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.recovery_timeout

    async def _on_success(self) -> None:
        """Registra uma operação bem-sucedida."""
        async with self._lock:
            self.failures = 0
            self.state = self.CLOSED
            logger.debug('Circuit breaker fechado após sucesso')

    async def _on_failure(self) -> None:
        """Registra uma falha."""
        async with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = self.OPEN
                logger.warning(
                    'Circuit breaker aberto após %d falhas consecutivas',
                    self.failures,
                    extra={
                        'operation': 'circuit_breaker_opened',
                        'failure_count': self.failures,
                        'threshold': self.failure_threshold,
                    },
                )

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Executa função com proteção do circuit breaker.

        Args:
            func: Função assíncrona a ser executada
            *args: Argumentos posicionais
            **kwargs: Argumentos nomeados

        Returns:
            Resultado da função

        Raises:
            CircuitBreakerOpenError: Se o circuit breaker estiver aberto
        """
        async with self._lock:
            if self.state == self.OPEN:
                if self._can_attempt_reset():
                    self.state = self.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info(
                        'Circuit breaker em half-open, testando requisição',
                        extra={'operation': 'circuit_breaker_half_open'},
                    )
                else:
                    time_remaining = self.recovery_timeout - (
                        time.time() - (self.last_failure_time or 0)
                    )
                    raise CircuitBreakerOpenError(
                        f'Circuit breaker aberto. Próxima tentativa em {time_remaining:.1f}s',
                        failure_count=self.failures,
                        recovery_timeout=self.recovery_timeout,
                    )

            if self.state == self.HALF_OPEN:
                self.half_open_calls += 1
                if self.half_open_calls > self.half_open_max_calls:
                    # Muitas chamadas em half-open, volta para open
                    self.state = self.OPEN
                    self.last_failure_time = time.time()
                    raise CircuitBreakerOpenError(
                        'Circuit breaker reaberto após limite de chamadas half-open',
                        failure_count=self.failures,
                        recovery_timeout=self.recovery_timeout,
                    )

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception:
            await self._on_failure()
            raise

    def reset(self) -> None:
        """Reseta o circuit breaker para o estado inicial."""
        self.failures = 0
        self.state = self.CLOSED
        self.last_failure_time = None
        self.half_open_calls = 0


class AsyncAPIClient:
    """Cliente base para requisições HTTP assíncronas."""

    def __init__(
        self,
        oauth_client: OAuth2Client,
        session: ClientSession | None = None,
        max_concurrent_requests: int = 10,
        request_timeout: int = 30,
        retry_config: dict[str, Any] | None = None,
        circuit_breaker_config: dict[str, Any] | None = None,
    ) -> None:
        """Inicializa cliente assíncrono.

        Args:
            oauth_client: Cliente OAuth2 para autenticação
            session: Sessão aiohttp existente (opcional)
            max_concurrent_requests: Limite de requisições concorrentes
            request_timeout: Timeout padrão para requisições em segundos
            retry_config: Configuração de retry automático (opcional)
                {
                    'max_tentativas': 3,
                    'delay_inicial': 0.5,
                    'delay_maximo': 5.0,
                    'backoff_exponencial': True,
                    'codigos_retry': [500, 502, 503, 504, 429],
                }
            circuit_breaker_config: Configuração do circuit breaker (opcional)
                {
                    'failure_threshold': 5,
                    'recovery_timeout': 30.0,
                    'half_open_max_calls': 3,
                }
        """
        self.oauth_client = oauth_client
        self.max_concurrent_requests = max_concurrent_requests
        self.request_timeout = request_timeout
        # self.logger = get_logger(__name__)  # Temporariamente comentado

        # Configuração de retry
        self.retry_config = retry_config or {
            'max_tentativas': 3,  # 2 retries por padrão
            'delay_inicial': 0.5,  # Delay inicial de 500ms
            'delay_maximo': 5.0,  # Cap máximo de 5s
            'backoff_exponencial': True,
            'codigos_retry': [500, 502, 503, 504, 429],
        }

        # Circuit breaker (opcional)
        if circuit_breaker_config is not None:
            self._circuit_breaker: AsyncCircuitBreaker | None = AsyncCircuitBreaker(
                **circuit_breaker_config
            )
        else:
            self._circuit_breaker = None

        # Semáforo para limitar requisições concorrentes
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._session = session
        self._owned_session = session is None

        # Arquivos temporários de certificado (para limpeza posterior)
        self._temp_cert_files: list[str] = []

    async def __aenter__(self) -> 'AsyncAPIClient':
        """Entrada do context manager."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Saída do context manager."""
        if self._owned_session and self._session:
            await self._session.close()

        # Limpa arquivos temporários de certificado
        self._cleanup_temp_cert_files()

    def _cleanup_temp_cert_files(self) -> None:
        """Limpa arquivos temporários de certificado."""
        for filepath in self._temp_cert_files:
            try:
                if os.path.exists(filepath):
                    os.unlink(filepath)
                    logger.debug(f'Arquivo temporário removido: {filepath}')
            except Exception as e:
                logger.warning(f'Falha ao remover arquivo temporário {filepath}: {e}')
        self._temp_cert_files.clear()

    def _load_pfx_certificate(
        self, ssl_context: ssl.SSLContext, pfx_path_or_data: str | bytes, password: str
    ) -> None:
        """Carrega certificado PFX/PKCS12 no contexto SSL.

        Args:
            ssl_context: Contexto SSL para carregar o certificado
            pfx_path_or_data: Caminho para o arquivo PFX ou dados binários
            password: Senha do certificado PFX

        Raises:
            ImportError: Se cryptography não estiver instalado
            ValueError: Se o certificado for inválido
        """
        try:
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.serialization import pkcs12
        except ImportError as e:
            raise ImportError(
                'O pacote cryptography é necessário para usar certificados PFX. '
                'Instale com: pip install cryptography'
            ) from e

        try:
            # Lê o PFX
            if isinstance(pfx_path_or_data, str):
                with open(pfx_path_or_data, 'rb') as f:
                    pfx_data = f.read()
            else:
                pfx_data = pfx_path_or_data

            # Extrai certificado e chave privada
            password_bytes = password.encode() if password else None
            private_key, certificate, _ = pkcs12.load_key_and_certificates(
                pfx_data, password_bytes, default_backend()
            )

            if not private_key or not certificate:
                raise ValueError('Certificado PFX inválido ou vazio')

            # Cria arquivos temporários para certificado e chave
            # (aiohttp/ssl requer arquivos em disco)
            with tempfile.NamedTemporaryFile(
                mode='wb', delete=False, suffix='.pem'
            ) as cert_file:
                cert_file.write(certificate.public_bytes(serialization.Encoding.PEM))
                cert_path = cert_file.name

            with tempfile.NamedTemporaryFile(
                mode='wb', delete=False, suffix='.key'
            ) as key_file:
                key_file.write(
                    private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )
                key_path = key_file.name

            # Registra arquivos para limpeza posterior
            self._temp_cert_files.extend([cert_path, key_path])

            # Carrega no contexto SSL
            ssl_context.load_cert_chain(cert_path, key_path)

            logger.info('Certificado PFX carregado com sucesso no contexto SSL')

        except Exception as e:
            logger.error(f'Erro ao carregar certificado PFX: {e}', exc_info=True)
            raise ValueError(f'Falha ao carregar certificado PFX: {e}') from e

    async def _ensure_session(self) -> None:
        """Garante que a sessão está inicializada."""
        if self._session is None:
            # Configuração SSL
            ssl_context = ssl.create_default_context()
            config = SicoobConfig.get_current_config()

            if not config.verify_ssl:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            # Carrega certificado cliente se necessário
            if config.require_certificate:
                oauth_client = self.oauth_client

                # Prioriza PFX
                if (
                    hasattr(oauth_client, 'certificado_pfx')
                    and oauth_client.certificado_pfx
                    and hasattr(oauth_client, 'senha_pfx')
                    and oauth_client.senha_pfx
                ):
                    logger.debug('Carregando certificado PFX para AsyncAPIClient')
                    self._load_pfx_certificate(
                        ssl_context,
                        oauth_client.certificado_pfx,
                        oauth_client.senha_pfx,
                    )
                # Fallback para PEM
                elif (
                    hasattr(oauth_client, 'certificado')
                    and oauth_client.certificado
                    and hasattr(oauth_client, 'chave_privada')
                    and oauth_client.chave_privada
                ):
                    logger.debug('Carregando certificado PEM para AsyncAPIClient')
                    ssl_context.load_cert_chain(
                        oauth_client.certificado, oauth_client.chave_privada
                    )
                else:
                    logger.warning(
                        'Certificado requerido mas não fornecido no OAuth2Client'
                    )

            # Configuração do conector
            connector = TCPConnector(
                ssl=ssl_context,
                limit=self.max_concurrent_requests * 2,
                limit_per_host=self.max_concurrent_requests,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )

            # Configuração de timeout
            timeout = ClientTimeout(total=self.request_timeout)

            self._session = ClientSession(
                connector=connector, timeout=timeout, raise_for_status=False
            )

    def _get_base_url(self) -> str:
        """Retorna a URL base conforme configuração do ambiente."""
        return SicoobConfig.get_base_url()

    def _get_headers(self, scope: str) -> dict[str, str]:
        """Retorna headers padrão com token de acesso."""
        token = self.oauth_client.get_access_token(scope)

        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Sicoob-SDK-Python/0.1.21',
        }

    def _validate_response_data(self, data: Any, status: int) -> dict[str, Any]:
        """Valida se os dados da resposta são JSON válidos."""
        if not isinstance(data, dict):
            raise SicoobError(f'Resposta não é JSON válido. Status: {status}')
        return data

    def _calcular_delay_retry(self, tentativa: int) -> float:
        """Calcula o delay para retry com exponential backoff e jitter.

        Args:
            tentativa: Número da tentativa (0-indexed)

        Returns:
            Delay em segundos
        """
        import random

        delay_inicial = self.retry_config.get('delay_inicial', 0.5)
        delay_maximo = self.retry_config.get('delay_maximo', 5.0)
        backoff_exponencial = self.retry_config.get('backoff_exponencial', True)

        if backoff_exponencial:
            # Exponential backoff: delay_inicial * (2 ** tentativa)
            delay = delay_inicial * (2**tentativa)
        else:
            # Delay fixo
            delay = delay_inicial

        # Aplica cap máximo para evitar delays muito longos
        delay = min(delay, delay_maximo)

        # Adiciona jitter (±25%) para evitar thundering herd
        jitter = delay * 0.25
        delay = delay + random.uniform(-jitter, jitter)

        return max(0.1, delay)  # Mínimo de 100ms

    def _should_retry(self, status_code: int, tentativa: int) -> bool:
        """Verifica se deve fazer retry baseado no status code e tentativa.

        Args:
            status_code: Código HTTP de status
            tentativa: Número da tentativa atual (0-indexed)

        Returns:
            True se deve fazer retry, False caso contrário
        """
        max_tentativas = self.retry_config.get('max_tentativas', 1)
        codigos_retry = self.retry_config.get(
            'codigos_retry', [500, 502, 503, 504, 429]
        )

        # Verifica se ainda tem tentativas disponíveis
        if tentativa >= max_tentativas - 1:
            return False

        # Verifica se o código de status permite retry
        return status_code in codigos_retry

    async def _make_request(
        self, method: str, url: str, scope: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Faz uma requisição HTTP assíncrona com retry automático e logging integrado.

        Args:
            method: Método HTTP (GET, POST, PUT, DELETE, etc.)
            url: URL completa da requisição
            scope: Escopo OAuth2 necessário
            **kwargs: Argumentos adicionais para aiohttp

        Returns:
            Dados JSON da resposta

        Raises:
            SicoobError: Em caso de erro na requisição
            CircuitBreakerOpenError: Se o circuit breaker estiver aberto
        """
        # Se circuit breaker estiver configurado, usa ele
        if self._circuit_breaker is not None:
            return await self._circuit_breaker.call(
                self._do_request, method, url, scope, **kwargs
            )
        return await self._do_request(method, url, scope, **kwargs)

    async def _do_request(
        self, method: str, url: str, scope: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Executa a requisição HTTP com retry e controle de concorrência.

        Este método interno contém a lógica real de requisição e é chamado
        diretamente ou através do circuit breaker.

        Args:
            method: Método HTTP
            url: URL completa
            scope: Escopo OAuth2
            **kwargs: Argumentos adicionais

        Returns:
            Dados JSON da resposta

        Raises:
            SicoobError: Em caso de erro na requisição
        """
        await self._ensure_session()

        # Headers padrão + headers customizados
        headers = self._get_headers(scope)
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers

        # Implementa retry com exponential backoff
        max_tentativas = self.retry_config.get('max_tentativas', 3)
        last_error = None

        for tentativa in range(max_tentativas):
            # Controle de concorrência
            async with self._semaphore:
                try:
                    # Log ANTES da requisição (apenas em DEBUG)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            f'Requisição HTTP: {method} {url}',
                            extra={
                                'method': method,
                                'url': url,
                                'tentativa': tentativa + 1,
                                'max_tentativas': max_tentativas,
                                # Não loga Authorization por segurança
                                'headers': {
                                    k: v
                                    for k, v in kwargs.get('headers', {}).items()
                                    if k.lower() not in ['authorization', 'client_id']
                                },
                            },
                        )

                    async with self._session.request(method, url, **kwargs) as response:
                        # Lê o corpo da resposta
                        response_text = await response.text()

                        # Log APÓS resposta
                        if logger.isEnabledFor(logging.DEBUG):
                            # Extrai headers de forma segura (pode falhar em mocks)
                            try:
                                resp_headers = dict(response.headers)
                            except (TypeError, AttributeError):
                                resp_headers = {}

                            logger.debug(
                                f'Resposta HTTP {response.status}: {method} {url}',
                                extra={
                                    'method': method,
                                    'url': url,
                                    'status': response.status,
                                    'response_size': len(response_text),
                                    # Primeiros 1000 chars apenas em DEBUG
                                    'response_preview': response_text[:1000]
                                    if response_text
                                    else '',
                                    'headers': resp_headers,
                                },
                            )

                        # Verifica se houve erro HTTP
                        if response.status >= 400:
                            # Tratamento especial para 404 (comportamento não-padrão da API Sicoob)
                            if response.status == 404:
                                try:
                                    error_data = json.loads(response_text)

                                    # Se contém dados válidos de boleto, processa como sucesso
                                    # (API Sicoob pode retornar 404 mas com dados válidos)
                                    if (
                                        'resultado' in error_data
                                        and 'nossoNumero'
                                        in error_data.get('resultado', {})
                                    ) or 'nossoNumero' in error_data:
                                        # Boleto emitido com sucesso apesar de status 404
                                        return self._validate_response_data(
                                            error_data, response.status
                                        )
                                except json.JSONDecodeError:
                                    pass  # Continua para o erro padrão

                            # Verifica se deve fazer retry
                            if self._should_retry(response.status, tentativa):
                                delay = self._calcular_delay_retry(tentativa)
                                # Calcula requisições concorrentes ativas
                                concurrent_active = (
                                    self.max_concurrent_requests
                                    - self._semaphore._value
                                )
                                logger.warning(
                                    'Requisição falhou - tentativa %d/%d - '
                                    'HTTP %d - retry em %.2fs',
                                    tentativa + 1,
                                    max_tentativas,
                                    response.status,
                                    delay,
                                    extra={
                                        'operation': 'http_retry',
                                        'tentativa': tentativa + 1,
                                        'max_tentativas': max_tentativas,
                                        'delay': delay,
                                        'status_code': response.status,
                                        'url': url,
                                        'method': method,
                                        'concurrent_active': concurrent_active,
                                    },
                                )
                                await asyncio.sleep(delay)
                                continue  # Tenta novamente

                            # Erro padrão para outros casos
                            try:
                                error_data = json.loads(response_text)
                                error_msg = error_data.get(
                                    'message', f'HTTP {response.status}'
                                )

                                # Extrai mensagens detalhadas se disponíveis
                                if 'mensagens' in error_data:
                                    mensagens_detalhadas = error_data['mensagens']
                                    if mensagens_detalhadas:
                                        error_msg = f'HTTP {response.status}: {mensagens_detalhadas}'
                            except json.JSONDecodeError:
                                error_msg = f'HTTP {response.status}: {response_text}'

                            # Extrai headers de forma segura (pode falhar em mocks)
                            try:
                                headers_dict = dict(response.headers)
                            except (TypeError, AttributeError):
                                headers_dict = None

                            raise SicoobError(
                                error_msg,
                                code=response.status,
                                response_text=response_text,
                                response_headers=headers_dict,
                            )

                        # Parse JSON - sucesso
                        try:
                            data = json.loads(response_text)
                            return self._validate_response_data(data, response.status)
                        except json.JSONDecodeError as e:
                            # Extrai headers de forma segura (pode falhar em mocks)
                            try:
                                headers_dict = dict(response.headers)
                            except (TypeError, AttributeError):
                                headers_dict = None

                            raise SicoobError(
                                f'Resposta não é JSON válido: {e!s}',
                                response_text=response_text,
                                response_headers=headers_dict,
                            ) from e

                except asyncio.TimeoutError as e:
                    last_error = e
                    # Verifica se deve fazer retry em caso de timeout
                    if tentativa < max_tentativas - 1:
                        delay = self._calcular_delay_retry(tentativa)
                        # TODO: Log quando disponível
                        await asyncio.sleep(delay)
                        continue
                    # self.logger.error(f'Timeout na requisição assíncrona')  # Temporariamente comentado
                    raise SicoobError(f'Timeout na requisição para {url}') from e

                except SicoobError:
                    # Relança SicoobError sem wrapping
                    raise

                except Exception as e:
                    last_error = e
                    # self.logger.error(f'Erro na requisição assíncrona: {e!s}')  # Temporariamente comentado
                    raise SicoobError(f'Erro na requisição assíncrona: {e!s}') from e

        # Se chegou aqui, esgotou todas as tentativas
        if last_error:
            raise SicoobError(
                f'Todas as {max_tentativas} tentativas falharam para {url}'
            ) from last_error
        raise SicoobError(f'Falha inesperada após {max_tentativas} tentativas')


class AsyncSicoob:
    """Cliente principal assíncrono para API do Sicoob."""

    def __init__(
        self,
        client_id: str | None = None,
        certificado: str | None = None,
        chave_privada: str | None = None,
        certificado_pfx: str | bytes | None = None,
        senha_pfx: str | None = None,
        environment: str | Environment | None = None,
        max_concurrent_requests: int = 10,
        request_timeout: int = 30,
        retry_config: dict[str, Any] | None = None,
    ) -> None:
        """Inicializa o cliente assíncrono.

        Args:
            client_id: Client ID para autenticação OAuth2
            certificado: Path para o certificado PEM (opcional)
            chave_privada: Path para a chave privada PEM (opcional)
            certificado_pfx: Path ou bytes do certificado PFX (opcional)
            senha_pfx: Senha do certificado PFX (opcional)
            environment: Ambiente (development, test, staging, production, sandbox)
            max_concurrent_requests: Limite de requisições concorrentes
            request_timeout: Timeout padrão para requisições
            retry_config: Configuração de retry automático (opcional)
                {
                    'max_tentativas': 3,
                    'delay_inicial': 1.0,
                    'backoff_exponencial': True,
                    'codigos_retry': [500, 502, 503, 504, 429],
                }
        """
        import os

        from dotenv import load_dotenv

        load_dotenv()

        self.client_id = client_id or os.getenv('SICOOB_CLIENT_ID')
        self.certificado = certificado or os.getenv('SICOOB_CERTIFICADO')
        self.chave_privada = chave_privada or os.getenv('SICOOB_CHAVE_PRIVADA')
        self.certificado_pfx = certificado_pfx or os.getenv('SICOOB_CERTIFICADO_PFX')
        self.senha_pfx = senha_pfx or os.getenv('SICOOB_SENHA_PFX')
        # Configura ambiente se fornecido
        if environment is not None:
            if isinstance(environment, str):
                env_mapping = {
                    'dev': Environment.DEVELOPMENT,
                    'development': Environment.DEVELOPMENT,
                    'test': Environment.TEST,
                    'sandbox': Environment.SANDBOX,
                    'staging': Environment.STAGING,
                    'prod': Environment.PRODUCTION,
                    'production': Environment.PRODUCTION,
                }
                env = env_mapping.get(environment.lower(), Environment.PRODUCTION)
            else:
                env = environment
            SicoobConfig.set_environment(env)

        # Valida credenciais mínimas
        if not self.client_id:
            raise ValueError('client_id é obrigatório')

        # Inicializa cliente OAuth2 (síncrono para compatibilidade)
        self.oauth_client = OAuth2Client(
            client_id=self.client_id,
            certificado=self.certificado,
            chave_privada=self.chave_privada,
            certificado_pfx=self.certificado_pfx,
            senha_pfx=self.senha_pfx,
        )

        # Inicializa cliente assíncrono
        self._api_client = AsyncAPIClient(
            oauth_client=self.oauth_client,
            max_concurrent_requests=max_concurrent_requests,
            request_timeout=request_timeout,
            retry_config=retry_config,
        )

        # self.logger = get_logger(__name__)  # Temporariamente comentado

    async def __aenter__(self) -> 'AsyncAPIClient':
        """Entrada do context manager."""
        await self._api_client.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Saída do context manager."""
        await self._api_client.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def conta_corrente(self) -> 'AsyncContaCorrenteAPI':
        """Retorna instância da API de conta corrente assíncrona."""
        return AsyncContaCorrenteAPI(self._api_client)

    @property
    def cobranca(self) -> 'AsyncCobrancaAPI':
        """Retorna instância da API de cobrança assíncrona."""
        return AsyncCobrancaAPI(self._api_client)


class AsyncContaCorrenteAPI:
    """API assíncrona para operações de conta corrente."""

    def __init__(self, api_client: AsyncAPIClient) -> None:
        self.api_client = api_client

    async def get_extrato(
        self, data_inicio: str, data_fim: str, numero_conta: str | None = None
    ) -> dict[str, Any]:
        """Consulta extrato de conta corrente de forma assíncrona.

        Args:
            data_inicio: Data de início (YYYY-MM-DD)
            data_fim: Data de fim (YYYY-MM-DD)
            numero_conta: Número da conta (opcional)

        Returns:
            Dados do extrato
        """
        base_url = self.api_client._get_base_url()
        url = f'{base_url}/conta-corrente/extrato'

        params = {
            'dataInicio': data_inicio,
            'dataFim': data_fim,
        }

        if numero_conta:
            params['numeroConta'] = numero_conta

        return await self.api_client._make_request(
            'GET', url, scope='cco_extrato cco_consulta', params=params
        )

    async def get_saldo(self, numero_conta: str | None = None) -> dict[str, Any]:
        """Consulta saldo de conta corrente de forma assíncrona.

        Args:
            numero_conta: Número da conta (opcional)

        Returns:
            Dados do saldo
        """
        base_url = self.api_client._get_base_url()
        url = f'{base_url}/conta-corrente/saldo'

        params = {}
        if numero_conta:
            params['numeroConta'] = numero_conta

        return await self.api_client._make_request(
            'GET', url, scope='cco_consulta', params=params
        )


class AsyncCobrancaAPI:
    """API assíncrona para operações de cobrança."""

    def __init__(self, api_client: AsyncAPIClient) -> None:
        self.api_client = api_client

    async def criar_cobranca_pix(
        self, txid: str, dados: dict[str, Any]
    ) -> dict[str, Any]:
        """Cria cobrança PIX de forma assíncrona.

        Args:
            txid: Identificador da transação
            dados: Dados da cobrança

        Returns:
            Dados da cobrança criada
        """
        base_url = self.api_client._get_base_url()
        url = f'{base_url}/pix/cob/{txid}'

        return await self.api_client._make_request(
            'PUT', url, scope='cob.write', json=dados
        )

    async def consultar_cobranca_pix(self, txid: str) -> dict[str, Any]:
        """Consulta cobrança PIX de forma assíncrona.

        Args:
            txid: Identificador da transação

        Returns:
            Dados da cobrança
        """
        base_url = self.api_client._get_base_url()
        url = f'{base_url}/pix/cob/{txid}'

        return await self.api_client._make_request('GET', url, scope='cob.read')

    async def listar_cobrancas_pix(
        self, inicio: str, fim: str, **filtros: Any
    ) -> dict[str, Any]:
        """Lista cobranças PIX de forma assíncrona.

        Args:
            inicio: Data/hora inicial (ISO 8601)
            fim: Data/hora final (ISO 8601)
            **filtros: Filtros adicionais

        Returns:
            Lista de cobranças
        """
        base_url = self.api_client._get_base_url()
        url = f'{base_url}/pix/cob'

        params = {'inicio': inicio, 'fim': fim, **filtros}

        return await self.api_client._make_request(
            'GET', url, scope='cob.read', params=params
        )


# Utilitários assíncronos
async def gather_with_concurrency(tasks: list, max_concurrency: int = 10) -> list:
    """Executa tarefas com limite de concorrência.

    Args:
        tasks: Lista de corrotinas
        max_concurrency: Número máximo de tarefas concorrentes

    Returns:
        Lista de resultados
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def bounded_task(task: Any) -> Any:
        async with semaphore:
            return await task

    bounded_tasks = [bounded_task(task) for task in tasks]
    return await asyncio.gather(*bounded_tasks)


async def gather_with_rate_limit(
    tasks: list,
    max_concurrency: int = 10,
    requests_per_second: float = 5.0,
    stagger_delay: float = 0.0,
) -> list:
    """Executa tarefas com limite de concorrência E rate limiting integrado.

    Esta função combina controle de concorrência (semáforo) com rate limiting
    (intervalo mínimo entre requisições) para evitar throttling em APIs que
    limitam a taxa de requisições.

    Args:
        tasks: Lista de corrotinas a executar
        max_concurrency: Número máximo de tarefas concorrentes (default: 10)
        requests_per_second: Taxa máxima de requisições por segundo (default: 5.0)
        stagger_delay: Delay inicial escalonado para evitar rajada inicial
            em segundos. Se > 0, cada task aguarda (stagger_delay * índice)
            antes de começar. (default: 0.0 = desabilitado)

    Returns:
        Lista com resultados de todas as tasks na mesma ordem

    Example:
        >>> # Emitir 12 boletos com rate limiting para evitar erro 500
        >>> tasks = [emitir_boleto(dados) for dados in lista_boletos]
        >>> resultados = await gather_with_rate_limit(
        ...     tasks,
        ...     max_concurrency=3,
        ...     requests_per_second=3.0,  # Margem de segurança (API permite 5)
        ...     stagger_delay=0.2  # 200ms entre início de cada task
        ... )

    Note:
        - O rate limiting é aplicado DENTRO do semáforo, garantindo que mesmo
          com várias tasks aguardando, elas respeitem o intervalo mínimo.
        - O stagger_delay é calculado como: delay * (index % max_concurrency),
          distribuindo as tasks em "ondas" para evitar rajada inicial.
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    min_interval = 1.0 / requests_per_second
    last_request_lock = asyncio.Lock()
    last_request_time: list[float] = [0.0]

    async def rate_limited_task(task: Any, index: int) -> Any:
        # Stagger delay para evitar rajada inicial
        if index > 0 and stagger_delay > 0:
            await asyncio.sleep(stagger_delay * (index % max_concurrency))

        async with semaphore:
            # Rate limiting - garante intervalo mínimo entre requisições
            async with last_request_lock:
                loop = asyncio.get_event_loop()
                now = loop.time()
                elapsed = now - last_request_time[0]
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
                last_request_time[0] = loop.time()

            return await task

    bounded_tasks = [rate_limited_task(task, i) for i, task in enumerate(tasks)]
    return await asyncio.gather(*bounded_tasks)


@asynccontextmanager
async def async_batch_processor(
    items: list, process_func: Any, batch_size: int = 10, max_concurrency: int = 5
) -> AsyncGenerator[list, None]:
    """Context manager para processamento assíncrono em lotes.

    Args:
        items: Lista de itens para processar
        process_func: Função assíncrona para processar cada item
        batch_size: Tamanho do lote
        max_concurrency: Número máximo de lotes concorrentes

    Yields:
        Lista de resultados processados

    Example:
        >>> async with async_batch_processor(
        ...     txids,
        ...     client.cobranca.consultar_cobranca_pix,
        ...     batch_size=5
        ... ) as results:
        ...     for result in results:
        ...         print(result)
    """
    # Divide items em lotes
    batches = [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

    # Processa lotes com concorrência limitada
    tasks = []
    for batch in batches:
        batch_tasks = [process_func(item) for item in batch]
        tasks.append(gather_with_concurrency(batch_tasks, max_concurrency))

    # Executa todos os lotes
    batch_results = await asyncio.gather(*tasks)

    # Flattening dos resultados
    results = []
    for batch_result in batch_results:
        results.extend(batch_result)

    yield results
