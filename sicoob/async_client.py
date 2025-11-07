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
import ssl
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from aiohttp import ClientSession, ClientTimeout, TCPConnector

from sicoob.auth import OAuth2Client
from sicoob.config import Environment, SicoobConfig
from sicoob.exceptions import SicoobError

# Logger para debugging
logger = logging.getLogger(__name__)


class AsyncAPIClient:
    """Cliente base para requisições HTTP assíncronas."""

    def __init__(
        self,
        oauth_client: OAuth2Client,
        session: ClientSession | None = None,
        max_concurrent_requests: int = 10,
        request_timeout: int = 30,
        retry_config: dict[str, Any] | None = None,
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
                    'delay_inicial': 1.0,
                    'backoff_exponencial': True,
                    'codigos_retry': [500, 502, 503, 504, 429],
                }
        """
        self.oauth_client = oauth_client
        self.max_concurrent_requests = max_concurrent_requests
        self.request_timeout = request_timeout
        # self.logger = get_logger(__name__)  # Temporariamente comentado

        # Configuração de retry
        self.retry_config = retry_config or {
            'max_tentativas': 1,  # Sem retry por padrão
            'delay_inicial': 1.0,
            'backoff_exponencial': True,
            'codigos_retry': [500, 502, 503, 504, 429],
        }

        # Semáforo para limitar requisições concorrentes
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._session = session
        self._owned_session = session is None

    async def __aenter__(self) -> 'AsyncAPIClient':
        """Entrada do context manager."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Saída do context manager."""
        if self._owned_session and self._session:
            await self._session.close()

    async def _ensure_session(self) -> None:
        """Garante que a sessão está inicializada."""
        if self._session is None:
            # Configuração SSL
            ssl_context = ssl.create_default_context()
            config = SicoobConfig.get_current_config()

            if not config.verify_ssl:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

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

        delay_inicial = self.retry_config.get('delay_inicial', 1.0)
        backoff_exponencial = self.retry_config.get('backoff_exponencial', True)

        if backoff_exponencial:
            # Exponential backoff: delay_inicial * (2 ** tentativa)
            delay = delay_inicial * (2**tentativa)
        else:
            # Delay fixo
            delay = delay_inicial

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
        """
        await self._ensure_session()

        # Headers padrão + headers customizados
        headers = self._get_headers(scope)
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers

        # Log da requisição (simplificado)
        # TODO: Implementar logging apropriado quando SicoobLogger estiver disponível

        # Implementa retry com exponential backoff
        max_tentativas = self.retry_config.get('max_tentativas', 1)
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
                                logger.info(
                                    f'Retry {tentativa + 1}/{max_tentativas} após {delay:.2f}s (HTTP {response.status})',
                                    extra={
                                        'operation': 'http_retry',
                                        'tentativa': tentativa + 1,
                                        'max_tentativas': max_tentativas,
                                        'delay': delay,
                                        'status': response.status,
                                        'url': url,
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
