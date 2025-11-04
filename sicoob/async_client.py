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
import ssl
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from aiohttp import ClientSession, ClientTimeout, TCPConnector

from sicoob.auth import OAuth2Client
from sicoob.config import Environment, SicoobConfig
from sicoob.exceptions import SicoobError


class AsyncAPIClient:
    """Cliente base para requisições HTTP assíncronas."""

    def __init__(
        self,
        oauth_client: OAuth2Client,
        session: ClientSession | None = None,
        max_concurrent_requests: int = 10,
        request_timeout: int = 30,
    ) -> None:
        """Inicializa cliente assíncrono.

        Args:
            oauth_client: Cliente OAuth2 para autenticação
            session: Sessão aiohttp existente (opcional)
            max_concurrent_requests: Limite de requisições concorrentes
            request_timeout: Timeout padrão para requisições em segundos
        """
        self.oauth_client = oauth_client
        self.max_concurrent_requests = max_concurrent_requests
        self.request_timeout = request_timeout
        # self.logger = get_logger(__name__)  # Temporariamente comentado

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

    async def _make_request(
        self, method: str, url: str, scope: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Faz uma requisição HTTP assíncrona com logging integrado.

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

        # Controle de concorrência
        async with self._semaphore:
            try:
                async with self._session.request(method, url, **kwargs) as response:
                    # Lê o corpo da resposta
                    response_text = await response.text()

                    # Log da resposta (simplificado)
                    # TODO: Implementar logging apropriado quando SicoobLogger estiver disponível

                    # Verifica se houve erro HTTP
                    if response.status >= 400:
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get(
                                'message', f'HTTP {response.status}'
                            )
                        except Exception:
                            error_msg = f'HTTP {response.status}: {response_text}'

                        raise SicoobError(error_msg, code=response.status)

                    # Parse JSON
                    try:
                        data = await response.json()
                        return self._validate_response_data(data, response.status)
                    except json.JSONDecodeError as e:
                        raise SicoobError(f'Resposta não é JSON válido: {e!s}') from e

            except asyncio.TimeoutError as e:
                # self.logger.error(f'Timeout na requisição assíncrona')  # Temporariamente comentado
                raise SicoobError(f'Timeout na requisição para {url}') from e

            except Exception as e:
                # self.logger.error(f'Erro na requisição assíncrona: {e!s}')  # Temporariamente comentado
                pass
                raise SicoobError(f'Erro na requisição assíncrona: {e!s}') from e


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
