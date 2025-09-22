"""Sistema de paginação para APIs de listagem do Sicoob SDK.

Este módulo fornece classes e utilitários para lidar com paginação de forma
consistente em todas as APIs do SDK, suportando grandes volumes de dados.

Características:
    - Paginação offset-based (tradicional)
    - Cursor-based pagination para alta performance
    - Lazy loading com iteradores
    - Configuração automática de tamanho de página
    - Retry automático em falhas temporárias
    - Métricas de performance

Example:
    >>> from sicoob.pagination import PagedResponse, PaginationConfig
    >>>
    >>> # Configuração de paginação
    >>> config = PaginationConfig(page_size=100, max_pages=10)
    >>>
    >>> # Usar com API existente
    >>> for page in cliente.pix.listar_cobrancas_paginado(
    ...     inicio="2024-01-01T00:00:00Z",
    ...     fim="2024-01-31T23:59:59Z",
    ...     pagination=config
    ... ):
    ...     for cobranca in page.items:
    ...         print(f"TXID: {cobranca['txid']}")
"""

import math
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import (
    Any,
    Generic,
    TypeVar,
)

from sicoob.exceptions import PaginationError
from sicoob.logging_config import get_logger

T = TypeVar('T')


@dataclass
class PaginationConfig:
    """Configuração para paginação

    Attributes:
        page_size: Tamanho de cada página (padrão: 100)
        max_pages: Número máximo de páginas a processar (None = ilimitado)
        cursor_field: Campo usado como cursor (para cursor-based pagination)
        order_by: Campo para ordenação (padrão: data de criação)
        ascending: Se ordenação é crescente (padrão: True)
        auto_retry: Se deve tentar novamente em caso de erro (padrão: True)
        retry_delay: Delay entre retries em segundos (padrão: 1.0)
        max_retries: Máximo de tentativas de retry (padrão: 3)
    """

    page_size: int = 100
    max_pages: int | None = None
    cursor_field: str = 'created_at'
    order_by: str = 'created_at'
    ascending: bool = True
    auto_retry: bool = True
    retry_delay: float = 1.0
    max_retries: int = 3

    def __post_init__(self):
        """Valida configuração após inicialização"""
        if self.page_size <= 0:
            raise PaginationError('page_size deve ser maior que zero')
        if self.max_pages is not None and self.max_pages <= 0:
            raise PaginationError('max_pages deve ser maior que zero')
        if self.retry_delay < 0:
            raise PaginationError('retry_delay deve ser >= 0')
        if self.max_retries < 0:
            raise PaginationError('max_retries deve ser >= 0')


@dataclass
class PageInfo:
    """Informações sobre paginação da página atual"""

    current_page: int
    page_size: int
    total_items: int | None = None
    total_pages: int | None = None
    has_next: bool = False
    has_previous: bool = False
    next_cursor: str | None = None
    previous_cursor: str | None = None

    @property
    def is_first_page(self) -> bool:
        """Verifica se é a primeira página"""
        return self.current_page == 1

    @property
    def is_last_page(self) -> bool:
        """Verifica se é a última página"""
        if self.total_pages is None:
            return not self.has_next
        return self.current_page >= self.total_pages


@dataclass
class PagedResponse(Generic[T]):
    """Resposta paginada contendo items e metadados de paginação

    Attributes:
        items: Lista de items da página atual
        page_info: Informações de paginação
        raw_response: Resposta original da API (opcional)
        request_duration: Duração da requisição em segundos
        pagination_config: Configuração de paginação usada
    """

    items: list[T]
    page_info: PageInfo
    raw_response: dict[str, Any] | None = None
    request_duration: float = 0.0
    pagination_config: PaginationConfig | None = None

    def __len__(self) -> int:
        """Retorna número de items na página atual"""
        return len(self.items)

    def __iter__(self) -> Iterator[T]:
        """Permite iteração sobre os items da página"""
        return iter(self.items)

    def __bool__(self) -> bool:
        """Retorna True se há items na página"""
        return len(self.items) > 0


class PaginationStrategy(ABC):
    """Estratégia abstrata para diferentes tipos de paginação"""

    @abstractmethod
    def get_next_params(
        self, current_params: dict[str, Any], response: PagedResponse
    ) -> dict[str, Any] | None:
        """Calcula parâmetros para próxima página

        Args:
            current_params: Parâmetros da requisição atual
            response: Resposta da página atual

        Returns:
            Parâmetros para próxima página ou None se não há mais páginas
        """
        pass

    @abstractmethod
    def extract_page_info(
        self, response_data: dict[str, Any], current_page: int, page_size: int
    ) -> PageInfo:
        """Extrai informações de paginação da resposta

        Args:
            response_data: Dados da resposta da API
            current_page: Página atual
            page_size: Tamanho da página

        Returns:
            Informações de paginação extraídas
        """
        pass


class OffsetBasedStrategy(PaginationStrategy):
    """Estratégia de paginação baseada em offset/limit"""

    def __init__(self, offset_param: str = 'offset', limit_param: str = 'limit'):
        """Inicializa estratégia offset-based

        Args:
            offset_param: Nome do parâmetro de offset na API
            limit_param: Nome do parâmetro de limit na API
        """
        self.offset_param = offset_param
        self.limit_param = limit_param

    def get_next_params(
        self, current_params: dict[str, Any], response: PagedResponse
    ) -> dict[str, Any] | None:
        """Calcula offset para próxima página"""
        if not response.page_info.has_next:
            return None

        current_offset = current_params.get(self.offset_param, 0)
        next_offset = current_offset + response.page_info.page_size

        next_params = current_params.copy()
        next_params[self.offset_param] = next_offset

        return next_params

    def extract_page_info(
        self, response_data: dict[str, Any], current_page: int, page_size: int
    ) -> PageInfo:
        """Extrai informações de paginação para offset-based"""
        items_count = len(response_data.get('items', response_data.get('data', [])))
        total_items = response_data.get('total', response_data.get('totalElements'))

        total_pages = None
        if total_items is not None:
            total_pages = math.ceil(total_items / page_size)

        has_next = items_count == page_size
        if total_pages is not None:
            has_next = current_page < total_pages

        return PageInfo(
            current_page=current_page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=current_page > 1,
        )


class CursorBasedStrategy(PaginationStrategy):
    """Estratégia de paginação baseada em cursor"""

    def __init__(
        self,
        cursor_param: str = 'cursor',
        cursor_field: str = 'id',
        size_param: str = 'size',
    ):
        """Inicializa estratégia cursor-based

        Args:
            cursor_param: Nome do parâmetro de cursor na API
            cursor_field: Campo usado como cursor nos items
            size_param: Nome do parâmetro de tamanho da página
        """
        self.cursor_param = cursor_param
        self.cursor_field = cursor_field
        self.size_param = size_param

    def get_next_params(
        self, current_params: dict[str, Any], response: PagedResponse
    ) -> dict[str, Any] | None:
        """Calcula cursor para próxima página"""
        if not response.page_info.has_next or not response.page_info.next_cursor:
            return None

        next_params = current_params.copy()
        next_params[self.cursor_param] = response.page_info.next_cursor

        return next_params

    def extract_page_info(
        self, response_data: dict[str, Any], current_page: int, page_size: int
    ) -> PageInfo:
        """Extrai informações de paginação para cursor-based"""
        items = response_data.get('items', response_data.get('data', []))

        # Próximo cursor é o valor do campo cursor do último item
        next_cursor = None
        if items and len(items) == page_size:
            last_item = items[-1]
            next_cursor = last_item.get(self.cursor_field)

        # Para cursor-based, geralmente não sabemos total de items
        has_next = len(items) == page_size and next_cursor is not None

        return PageInfo(
            current_page=current_page,
            page_size=page_size,
            has_next=has_next,
            has_previous=current_page > 1,
            next_cursor=str(next_cursor) if next_cursor else None,
        )


class SicoobPaginationStrategy(PaginationStrategy):
    """Estratégia específica para APIs do Sicoob baseada em análise das respostas"""

    def get_next_params(
        self, current_params: dict[str, Any], response: PagedResponse
    ) -> dict[str, Any] | None:
        """Sicoob geralmente usa paginação baseada em datas/períodos"""
        if not response.page_info.has_next:
            return None

        # Para APIs do Sicoob, pode ser necessário ajustar período
        # Por exemplo, se obtivemos 100 items, buscar próximo período
        if len(response.items) < response.page_info.page_size:
            return None  # Não há mais dados

        # Implementação específica dependeria da API
        # Por ora, usar estratégia offset simples
        next_params = current_params.copy()
        next_params['page'] = response.page_info.current_page + 1

        return next_params

    def extract_page_info(
        self, response_data: dict[str, Any], current_page: int, page_size: int
    ) -> PageInfo:
        """Extrai informações baseadas na estrutura de resposta do Sicoob"""
        # Sicoob pode retornar diferentes estruturas:
        # - Array direto de items
        # - Object com propriedade 'cobs', 'boletos', etc
        # - Object com metadados de paginação

        items = []
        if isinstance(response_data, list):
            items = response_data
        else:
            # Busca por arrays comuns nas APIs do Sicoob
            for key in ['cobs', 'boletos', 'lancamentos', 'items', 'data']:
                if key in response_data and isinstance(response_data[key], list):
                    items = response_data[key]
                    break

        items_count = len(items)
        has_next = items_count == page_size

        return PageInfo(
            current_page=current_page,
            page_size=page_size,
            total_items=None,  # Sicoob geralmente não fornece total
            total_pages=None,
            has_next=has_next,
            has_previous=current_page > 1,
        )


class PaginatedIterator(Generic[T]):
    """Iterator que busca páginas sob demanda (lazy loading)"""

    def __init__(
        self,
        fetch_function: Callable[[dict[str, Any]], dict[str, Any]],
        initial_params: dict[str, Any],
        config: PaginationConfig,
        strategy: PaginationStrategy,
        item_extractor: Callable[[dict[str, Any]], list[T]] | None = None,
    ):
        """Inicializa iterator paginado

        Args:
            fetch_function: Função para buscar dados da API
            initial_params: Parâmetros iniciais da requisição
            config: Configuração de paginação
            strategy: Estratégia de paginação a usar
            item_extractor: Função para extrair items da resposta
        """
        self.fetch_function = fetch_function
        self.params = initial_params.copy()
        self.config = config
        self.strategy = strategy
        self.item_extractor = item_extractor or self._default_item_extractor

        self.current_page = 1
        self.pages_fetched = 0
        self.total_items_fetched = 0
        self.current_items: list[T] = []
        self.item_index = 0
        self.finished = False

        self.logger = get_logger(__name__)

    def _default_item_extractor(self, response_data: dict[str, Any]) -> list[T]:
        """Extrator padrão de items da resposta"""
        if isinstance(response_data, list):
            return response_data

        # Busca por arrays comuns
        for key in ['items', 'data', 'cobs', 'boletos', 'lancamentos']:
            if key in response_data and isinstance(response_data[key], list):
                return response_data[key]

        return []

    def _fetch_next_page(self) -> PagedResponse[T] | None:
        """Busca próxima página de dados"""
        if self.finished:
            return None

        if self.config.max_pages and self.pages_fetched >= self.config.max_pages:
            self.logger.info(f'Limite de páginas atingido: {self.config.max_pages}')
            self.finished = True
            return None

        # Configura tamanho da página
        if 'limit' not in self.params and 'size' not in self.params:
            self.params['limit'] = self.config.page_size

        attempts = 0
        while attempts <= self.config.max_retries:
            try:
                start_time = time.time()

                self.logger.debug(
                    f'Buscando página {self.current_page}',
                    extra={
                        'operation': 'pagination_fetch',
                        'page': self.current_page,
                        'params': self.params,
                    },
                )

                response_data = self.fetch_function(self.params)
                request_duration = time.time() - start_time

                # Extrai items e informações de paginação
                items = self.item_extractor(response_data)
                page_info = self.strategy.extract_page_info(
                    response_data, self.current_page, self.config.page_size
                )

                page_response = PagedResponse(
                    items=items,
                    page_info=page_info,
                    raw_response=response_data,
                    request_duration=request_duration,
                    pagination_config=self.config,
                )

                # Atualiza contadores
                self.pages_fetched += 1
                self.total_items_fetched += len(items)

                # Prepara próxima página
                if page_info.has_next:
                    next_params = self.strategy.get_next_params(
                        self.params, page_response
                    )
                    if next_params:
                        self.params = next_params
                        self.current_page += 1
                    else:
                        self.finished = True
                else:
                    self.finished = True

                self.logger.info(
                    f'Página {self.current_page - 1} buscada: {len(items)} items em {request_duration:.3f}s',
                    extra={
                        'operation': 'pagination_success',
                        'page': self.current_page - 1,
                        'items_count': len(items),
                        'duration': request_duration,
                        'total_fetched': self.total_items_fetched,
                    },
                )

                return page_response

            except Exception as e:
                attempts += 1

                if not self.config.auto_retry or attempts > self.config.max_retries:
                    self.logger.error(
                        f'Erro ao buscar página {self.current_page}: {e}',
                        extra={
                            'operation': 'pagination_error',
                            'page': self.current_page,
                        },
                        exc_info=True,
                    )
                    raise PaginationError(
                        f'Falha ao buscar página {self.current_page}: {e}'
                    ) from e

                self.logger.warning(
                    f'Tentativa {attempts} falhou, tentando novamente em {self.config.retry_delay}s: {e}',
                    extra={
                        'operation': 'pagination_retry',
                        'attempt': attempts,
                        'delay': self.config.retry_delay,
                    },
                )

                time.sleep(self.config.retry_delay)

        return None

    def __iter__(self) -> Iterator[T]:
        """Retorna o próprio iterator"""
        return self

    def __next__(self) -> T:
        """Retorna próximo item, buscando páginas conforme necessário"""
        # Se ainda há items na página atual
        if self.item_index < len(self.current_items):
            item = self.current_items[self.item_index]
            self.item_index += 1
            return item

        # Precisa buscar próxima página
        if self.finished:
            raise StopIteration

        page = self._fetch_next_page()
        if not page or not page.items:
            raise StopIteration

        # Atualiza items e reinicia índice
        self.current_items = page.items
        self.item_index = 0

        # Retorna primeiro item da nova página
        if self.current_items:
            item = self.current_items[self.item_index]
            self.item_index += 1
            return item

        raise StopIteration


def paginated_response_from_data(
    data: dict[str, Any],
    page: int = 1,
    page_size: int = 100,
    strategy: PaginationStrategy | None = None,
) -> PagedResponse:
    """Utilitário para criar PagedResponse a partir de dados de API

    Args:
        data: Dados da resposta da API
        page: Número da página atual
        page_size: Tamanho da página
        strategy: Estratégia de paginação (padrão: SicoobPaginationStrategy)

    Returns:
        PagedResponse com dados extraídos
    """
    if strategy is None:
        strategy = SicoobPaginationStrategy()

    # Extrai items
    items = []
    if isinstance(data, list):
        items = data
    else:
        for key in ['items', 'data', 'cobs', 'boletos', 'lancamentos']:
            if key in data and isinstance(data[key], list):
                items = data[key]
                break

    # Extrai informações de paginação
    page_info = strategy.extract_page_info(data, page, page_size)

    return PagedResponse(items=items, page_info=page_info, raw_response=data)
