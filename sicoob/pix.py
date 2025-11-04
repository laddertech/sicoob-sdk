"""Módulo PIX do SDK Sicoob.

Este módulo atua como uma ponte (thin wrapper) entre o SDK Sicoob e a
biblioteca pypix-api, que implementa o padrão PIX do BACEN.

Arquitetura:
    - pypix-api: Implementação genérica do PIX (padrão BACEN)
    - sicoob-sdk: Funcionalidades específicas do Sicoob

A separação permite que a pypix-api seja reutilizada por outros bancos,
enquanto o sicoob-sdk foca nas particularidades do Banco Sicoob.

Classes:
    PixAPI: Interface principal para operações PIX
    SicoobPixAPICustom: Customização da pypix-api para Sicoob

Example:
    >>> from sicoob import Sicoob
    >>> cliente = Sicoob(client_id="123", environment="sandbox")
    >>> cobranca = cliente.pix.criar_cobranca_imediata(
    ...     txid="abcd1234567890123456789012345",
    ...     dados={
    ...         "calendario": {"expiracao": 3600},
    ...         "valor": {"original": "100.50"},
    ...         "chave": "usuario@exemplo.com"
    ...     }
    ... )
    >>> print(cobranca["qrcode"])
"""

from collections.abc import Generator
from typing import Any

import requests
from pypix_api.banks.sicoob import SicoobPixAPI

from sicoob.api_client import APIClientBase
from sicoob.config import SicoobConfig
from sicoob.exceptions import (
    CobrancaPixNaoEncontradaError,
    PixError,
    WebhookPixNaoEncontradoError,
)
from sicoob.pagination import (
    PaginatedIterator,
    PaginationConfig,
    SicoobPaginationStrategy,
    paginated_response_from_data,
)
from sicoob.validation import (
    MultipleValidationError,
    ValidationError,
    get_pix_cobranca_schema,
    validate_txid,
    validate_url,
)


class PixAPI(APIClientBase):
    """Interface PIX para o SDK Sicoob

    Esta classe atua como um wrapper fino sobre a pypix-api,
    delegando todas as operações PIX para a implementação genérica
    enquanto mantém consistência com a interface do SDK Sicoob.

    Responsabilidades:
        - Proxy para métodos da pypix-api
        - Tratamento de erros consistente com o SDK
        - Logging e métricas (se necessário)
        - Validações específicas do Sicoob (se necessário)
    """

    def __init__(self, oauth_client, session):
        """Inicializa a API PIX.

        Args:
            oauth_client: Cliente OAuth2 para autenticação
            session: Sessão HTTP (mantida por compatibilidade)

        Note:
            O ambiente é controlado via SicoobConfig.
        """
        super().__init__(oauth_client, session)

        # Inicializa a implementação PIX customizada do Sicoob
        self._pix_api = SicoobPixAPICustom(
            oauth=oauth_client, sandbox_mode=SicoobConfig.is_sandbox()
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy transparente para pypix-api.

        Delega automaticamente qualquer método não definido
        explicitamente para a instância da pypix-api.

        Args:
            name: Nome do método/atributo a ser acessado

        Returns:
            Método ou atributo da pypix-api, encapsulado com
            tratamento de erro se for um método

        Raises:
            AttributeError: Se o método/atributo não existe na pypix-api

        Note:
            Métodos são automaticamente encapsulados com tratamento
            de erro que converte exceções genéricas em PixError.
        """
        # Delega para a implementação da pypix-api
        attr = getattr(self._pix_api, name)

        # Se for um método, encapsula com tratamento de erro
        if callable(attr):

            def wrapped_method(*args, **kwargs):
                try:
                    return attr(*args, **kwargs)
                except (CobrancaPixNaoEncontradaError, WebhookPixNaoEncontradoError):
                    # Re-lança exceções do domínio
                    raise
                except Exception as e:
                    # Converte outras exceções em PixError
                    raise PixError(f'Erro na operação PIX: {e!s}') from e

            return wrapped_method

        return attr

    # Métodos explícitos para melhor documentação e IDE support

    def criar_cobranca_imediata(self, txid: str, dados: dict) -> dict:
        """Cria cobrança PIX imediata (COB)

        Args:
            txid: Identificador da transação (26-35 caracteres alfanuméricos)
            dados: Dados da cobrança

        Returns:
            Dados da cobrança criada

        Raises:
            ValidationError: Em caso de dados inválidos
            MultipleValidationError: Em caso de múltiplos erros de validação
        """
        # Valida TXID
        try:
            txid = validate_txid(txid)
        except ValueError as e:
            raise ValidationError(str(e), 'txid', txid) from e

        # Valida dados da cobrança
        try:
            schema = get_pix_cobranca_schema()
            dados = schema.validate(dados, strict=False)
        except (ValidationError, MultipleValidationError) as e:
            raise e

        return self.criar_cob(txid, dados)

    def consultar_cobranca_imediata(self, txid: str) -> dict:
        """Consulta cobrança PIX imediata

        Args:
            txid: Identificador da transação (26-35 caracteres alfanuméricos)

        Returns:
            Dados da cobrança

        Raises:
            ValidationError: Em caso de TXID inválido
        """
        # Valida TXID
        try:
            txid = validate_txid(txid)
        except ValueError as e:
            raise ValidationError(str(e), 'txid', txid) from e

        return self.consultar_cob(txid)

    def criar_cobranca_com_vencimento(self, txid: str, dados: dict) -> dict:
        """Cria cobrança PIX com vencimento (COBV)

        Args:
            txid: Identificador da transação
            dados: Dados da cobrança com vencimento

        Returns:
            Dados da cobrança criada
        """
        return self.criar_cobv(txid, dados)

    def consultar_cobranca_com_vencimento(self, txid: str) -> dict:
        """Consulta cobrança PIX com vencimento

        Args:
            txid: Identificador da transação

        Returns:
            Dados da cobrança
        """
        return self.consultar_cobv(txid, 0)

    def cadastrar_webhook(self, chave: str, url: str) -> dict:
        """Cadastra webhook para notificações PIX

        Args:
            chave: Chave PIX (não pode ser vazia)
            url: URL do webhook (deve ser uma URL válida)

        Returns:
            Dados do webhook cadastrado

        Raises:
            ValidationError: Em caso de dados inválidos
        """
        # Valida chave PIX
        if not chave or not isinstance(chave, str) or not chave.strip():
            raise ValidationError(
                'Chave PIX é obrigatória e não pode estar vazia', 'chave', chave
            )
        chave = chave.strip()

        # Valida URL
        try:
            url = validate_url(url)
        except ValueError as e:
            raise ValidationError(str(e), 'url', url) from e

        return self.configurar_webhook(chave, url)

    def consultar_webhook(self, chave: str) -> dict:
        """Consulta webhook cadastrado

        Args:
            chave: Chave PIX

        Returns:
            Dados do webhook
        """
        return self._pix_api.consultar_webhook(chave)

    def excluir_webhook(self, chave: str) -> None:
        """Exclui webhook cadastrado

        Args:
            chave: Chave PIX
        """
        return self._pix_api.excluir_webhook(chave)

    def listar_cobrancas(self, inicio: str, fim: str, **filtros: Any) -> dict:
        """Lista cobranças em um período

        Args:
            inicio: Data/hora inicial (ISO 8601)
            fim: Data/hora final (ISO 8601)
            **filtros: Filtros adicionais

        Returns:
            Lista de cobranças
        """
        return self.listar_cob(inicio, fim, **filtros)

    def criar_lote_cobranca(self, id_lote: int, dados: dict) -> dict:
        """Cria lote de cobranças com vencimento

        Args:
            id_lote: ID do lote
            dados: Dados do lote

        Returns:
            Dados do lote criado
        """
        return self.criar_lotecobv(id_lote, dados)

    def consultar_lote_cobranca(self, id_lote: int) -> dict:
        """Consulta lote de cobranças

        Args:
            id_lote: ID do lote

        Returns:
            Dados do lote
        """
        return self.consultar_lotecobv(id_lote)

    # Métodos paginados para grandes volumes

    def listar_cobrancas_paginado(
        self,
        inicio: str,
        fim: str,
        pagination: PaginationConfig | None = None,
        **filtros: Any,
    ) -> Generator[dict, None, None]:
        """Lista cobranças PIX com paginação automática

        Este método retorna um iterator que busca páginas sob demanda,
        permitindo processar grandes volumes de cobranças sem carregar
        tudo na memória de uma vez.

        Args:
            inicio: Data/hora inicial (ISO 8601)
            fim: Data/hora final (ISO 8601)
            pagination: Configuração de paginação (opcional)
            **filtros: Filtros adicionais

        Yields:
            Cada cobrança PIX individualmente

        Example:
            >>> config = PaginationConfig(page_size=50, max_pages=10)
            >>> for cobranca in cliente.pix.listar_cobrancas_paginado(
            ...     inicio="2024-01-01T00:00:00Z",
            ...     fim="2024-01-31T23:59:59Z",
            ...     pagination=config
            ... ):
            ...     print(f"TXID: {cobranca['txid']}")

        Note:
            Use este método para grandes volumes de dados. Para consultas
            simples, use listar_cobrancas() que retorna uma página única.
        """
        if pagination is None:
            pagination = PaginationConfig(page_size=100)

        def fetch_page(params: dict) -> dict:
            # Usa o método existente para buscar dados
            return self.listar_cobrancas(
                params.get('inicio', inicio),
                params.get('fim', fim),
                **{k: v for k, v in params.items() if k not in ['inicio', 'fim']},
            )

        strategy = SicoobPaginationStrategy()
        initial_params = {'inicio': inicio, 'fim': fim, **filtros}

        iterator = PaginatedIterator(
            fetch_function=fetch_page,
            initial_params=initial_params,
            config=pagination,
            strategy=strategy,
        )

        yield from iterator

    def listar_cobrancas_por_paginas(
        self,
        inicio: str,
        fim: str,
        pagination: PaginationConfig | None = None,
        **filtros: Any,
    ) -> Generator[Any, None, None]:
        """Lista cobranças PIX retornando páginas completas

        Similar ao listar_cobrancas_paginado(), mas retorna PagedResponse
        com metadados de paginação para cada página.

        Args:
            inicio: Data/hora inicial (ISO 8601)
            fim: Data/hora final (ISO 8601)
            pagination: Configuração de paginação (opcional)
            **filtros: Filtros adicionais

        Yields:
            PagedResponse com cobranças e metadados de cada página

        Example:
            >>> for page in cliente.pix.listar_cobrancas_por_paginas(
            ...     inicio="2024-01-01T00:00:00Z",
            ...     fim="2024-01-31T23:59:59Z"
            ... ):
            ...     print(f"Página {page.page_info.current_page}: {len(page)} cobranças")
            ...     for cobranca in page.items:
            ...         print(f"  TXID: {cobranca['txid']}")
        """
        if pagination is None:
            pagination = PaginationConfig(page_size=100)

        def fetch_page(params: dict) -> dict:
            raw_response = self.listar_cobrancas(
                params.get('inicio', inicio),
                params.get('fim', fim),
                **{k: v for k, v in params.items() if k not in ['inicio', 'fim']},
            )

            # Converte resposta em PagedResponse
            return paginated_response_from_data(
                raw_response, page=params.get('page', 1), page_size=pagination.page_size
            )

        initial_params = {'inicio': inicio, 'fim': fim, 'page': 1, **filtros}

        current_params = initial_params.copy()
        page_num = 1

        while True:
            try:
                page_response = fetch_page(current_params)

                if not page_response.items:
                    break

                yield page_response

                if not page_response.page_info.has_next:
                    break

                if pagination.max_pages and page_num >= pagination.max_pages:
                    break

                # Próxima página
                page_num += 1
                current_params['page'] = page_num

            except Exception as e:
                self.logger.error(
                    f'Erro ao buscar página {page_num}: {e}',
                    extra={'operation': 'pix_pagination_error', 'page': page_num},
                    exc_info=True,
                )
                break


class SicoobPixAPICustom(SicoobPixAPI):
    """Customização da pypix-api para Sicoob

    Adiciona tratamento de erros específicos do domínio Sicoob.
    """

    def _handle_error_response(
        self, response: requests.Response, **kwargs: Any
    ) -> None:
        """Trata erros com exceções específicas do domínio

        Args:
            response: Resposta HTTP
            **kwargs: Argumentos adicionais (não utilizado)
        """
        # Respostas de sucesso não são erros
        status_code = getattr(response, 'status_code', None)
        if status_code and 200 <= status_code < 300:
            return

        try:
            error_data = response.json()
        except (ValueError, AttributeError):
            error_data = {}

        detail = error_data.get('detail', '')
        title = error_data.get('title', '')
        status = error_data.get('status', status_code)
        type_ = error_data.get('type', '')

        # Mapeia para exceções específicas do domínio
        if status == 404:
            if 'cobrança' in (detail + title).lower():
                raise CobrancaPixNaoEncontradaError(detail or title)
            elif 'webhook' in (detail + title).lower():
                raise WebhookPixNaoEncontradoError(detail or title)

        # Erro genérico
        error_msg = detail or title or f'Erro {status}: {type_}'
        raise PixError(error_msg)
