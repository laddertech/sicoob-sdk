"""Testes para módulo de paginação."""

from unittest.mock import patch

import pytest

from sicoob.exceptions import PaginationError
from sicoob.pagination import (
    CursorBasedStrategy,
    OffsetBasedStrategy,
    PagedResponse,
    PageInfo,
    PaginatedIterator,
    PaginationConfig,
    SicoobPaginationStrategy,
    paginated_response_from_data,
)


class TestPaginationConfig:
    """Testes para configuração de paginação"""

    def test_default_config(self):
        """Testa configuração padrão"""
        config = PaginationConfig()

        assert config.page_size == 100
        assert config.max_pages is None
        assert config.cursor_field == 'created_at'
        assert config.order_by == 'created_at'
        assert config.ascending is True
        assert config.auto_retry is True
        assert config.retry_delay == 1.0
        assert config.max_retries == 3

    def test_custom_config(self):
        """Testa configuração customizada"""
        config = PaginationConfig(
            page_size=50,
            max_pages=10,
            cursor_field='id',
            order_by='updated_at',
            ascending=False,
            auto_retry=False,
            retry_delay=2.0,
            max_retries=5,
        )

        assert config.page_size == 50
        assert config.max_pages == 10
        assert config.cursor_field == 'id'
        assert config.order_by == 'updated_at'
        assert config.ascending is False
        assert config.auto_retry is False
        assert config.retry_delay == 2.0
        assert config.max_retries == 5

    def test_invalid_page_size(self):
        """Testa erro com page_size inválido"""
        with pytest.raises(PaginationError, match='page_size deve ser maior que zero'):
            PaginationConfig(page_size=0)

        with pytest.raises(PaginationError, match='page_size deve ser maior que zero'):
            PaginationConfig(page_size=-10)

    def test_invalid_max_pages(self):
        """Testa erro com max_pages inválido"""
        with pytest.raises(PaginationError, match='max_pages deve ser maior que zero'):
            PaginationConfig(max_pages=0)

        with pytest.raises(PaginationError, match='max_pages deve ser maior que zero'):
            PaginationConfig(max_pages=-5)

    def test_invalid_retry_config(self):
        """Testa erro com configuração de retry inválida"""
        with pytest.raises(PaginationError, match='retry_delay deve ser >= 0'):
            PaginationConfig(retry_delay=-1.0)

        with pytest.raises(PaginationError, match='max_retries deve ser >= 0'):
            PaginationConfig(max_retries=-1)


class TestPageInfo:
    """Testes para informações de página"""

    def test_page_info_creation(self):
        """Testa criação de PageInfo"""
        info = PageInfo(
            current_page=2,
            page_size=50,
            total_items=200,
            total_pages=4,
            has_next=True,
            has_previous=True,
            next_cursor='cursor_123',
            previous_cursor='cursor_456',
        )

        assert info.current_page == 2
        assert info.page_size == 50
        assert info.total_items == 200
        assert info.total_pages == 4
        assert info.has_next is True
        assert info.has_previous is True
        assert info.next_cursor == 'cursor_123'
        assert info.previous_cursor == 'cursor_456'

    def test_is_first_page(self):
        """Testa verificação de primeira página"""
        first_page = PageInfo(current_page=1, page_size=100)
        second_page = PageInfo(current_page=2, page_size=100)

        assert first_page.is_first_page is True
        assert second_page.is_first_page is False

    def test_is_last_page_with_total(self):
        """Testa verificação de última página com total conhecido"""
        page_info = PageInfo(current_page=3, page_size=100, total_pages=3)

        assert page_info.is_last_page is True

    def test_is_last_page_without_total(self):
        """Testa verificação de última página sem total conhecido"""
        last_page = PageInfo(current_page=2, page_size=100, has_next=False)
        middle_page = PageInfo(current_page=2, page_size=100, has_next=True)

        assert last_page.is_last_page is True
        assert middle_page.is_last_page is False


class TestPagedResponse:
    """Testes para resposta paginada"""

    def test_paged_response_creation(self):
        """Testa criação de PagedResponse"""
        items = [{'id': 1}, {'id': 2}, {'id': 3}]
        page_info = PageInfo(current_page=1, page_size=10)

        response = PagedResponse(
            items=items,
            page_info=page_info,
            raw_response={'data': items},
            request_duration=0.5,
        )

        assert response.items == items
        assert response.page_info == page_info
        assert response.raw_response == {'data': items}
        assert response.request_duration == 0.5

    def test_paged_response_len(self):
        """Testa método __len__"""
        items = [{'id': 1}, {'id': 2}]
        page_info = PageInfo(current_page=1, page_size=10)
        response = PagedResponse(items=items, page_info=page_info)

        assert len(response) == 2

    def test_paged_response_iter(self):
        """Testa iteração sobre PagedResponse"""
        items = [{'id': 1}, {'id': 2}, {'id': 3}]
        page_info = PageInfo(current_page=1, page_size=10)
        response = PagedResponse(items=items, page_info=page_info)

        result = list(response)
        assert result == items

    def test_paged_response_bool(self):
        """Testa método __bool__"""
        empty_response = PagedResponse(
            items=[], page_info=PageInfo(current_page=1, page_size=10)
        )
        non_empty_response = PagedResponse(
            items=[{'id': 1}], page_info=PageInfo(current_page=1, page_size=10)
        )

        assert bool(empty_response) is False
        assert bool(non_empty_response) is True


class TestOffsetBasedStrategy:
    """Testes para estratégia offset-based"""

    def test_get_next_params_with_next_page(self):
        """Testa cálculo de parâmetros para próxima página"""
        strategy = OffsetBasedStrategy()
        current_params = {'offset': 0, 'limit': 10}

        page_info = PageInfo(current_page=1, page_size=10, has_next=True)
        response = PagedResponse(items=[{}] * 10, page_info=page_info)

        next_params = strategy.get_next_params(current_params, response)

        assert next_params == {'offset': 10, 'limit': 10}

    def test_get_next_params_no_next_page(self):
        """Testa quando não há próxima página"""
        strategy = OffsetBasedStrategy()
        current_params = {'offset': 20, 'limit': 10}

        page_info = PageInfo(current_page=3, page_size=10, has_next=False)
        response = PagedResponse(items=[{}] * 5, page_info=page_info)

        next_params = strategy.get_next_params(current_params, response)

        assert next_params is None

    def test_extract_page_info_with_total(self):
        """Testa extração de informações com total conhecido"""
        strategy = OffsetBasedStrategy()
        response_data = {'items': [{}] * 10, 'total': 35}

        page_info = strategy.extract_page_info(response_data, 2, 10)

        assert page_info.current_page == 2
        assert page_info.page_size == 10
        assert page_info.total_items == 35
        assert page_info.total_pages == 4
        assert page_info.has_next is True
        assert page_info.has_previous is True

    def test_extract_page_info_without_total(self):
        """Testa extração de informações sem total"""
        strategy = OffsetBasedStrategy()
        response_data = {'data': [{}] * 10}

        page_info = strategy.extract_page_info(response_data, 1, 10)

        assert page_info.current_page == 1
        assert page_info.page_size == 10
        assert page_info.total_items is None
        assert page_info.total_pages is None
        assert page_info.has_next is True  # Página cheia indica possível próxima
        assert page_info.has_previous is False

    def test_extract_page_info_alternative_keys(self):
        """Testa extração com chaves alternativas."""
        strategy = OffsetBasedStrategy()

        response_data = {'data': ['item'] * 10, 'totalElements': 25}

        page_info = strategy.extract_page_info(response_data, 1, 10)

        assert page_info.total_items == 25
        assert len(response_data['data']) == 10  # Verifica que 'data' foi encontrado

    def test_custom_param_names(self):
        """Testa nomes customizados de parâmetros"""
        strategy = OffsetBasedStrategy(offset_param='start', limit_param='count')
        current_params = {'start': 5, 'count': 3}

        page_info = PageInfo(current_page=1, page_size=3, has_next=True)
        response = PagedResponse(items=[{}] * 3, page_info=page_info)

        next_params = strategy.get_next_params(current_params, response)

        assert next_params == {'start': 8, 'count': 3}


class TestCursorBasedStrategy:
    """Testes para estratégia cursor-based"""

    def test_get_next_params_with_cursor(self):
        """Testa cálculo de parâmetros com cursor"""
        strategy = CursorBasedStrategy()
        current_params = {'size': 10}

        page_info = PageInfo(
            current_page=1, page_size=10, has_next=True, next_cursor='cursor_abc123'
        )
        response = PagedResponse(items=[{}] * 10, page_info=page_info)

        next_params = strategy.get_next_params(current_params, response)

        assert next_params == {'size': 10, 'cursor': 'cursor_abc123'}

    def test_get_next_params_no_cursor(self):
        """Testa quando não há cursor para próxima página"""
        strategy = CursorBasedStrategy()
        current_params = {'size': 10}

        page_info = PageInfo(
            current_page=1, page_size=10, has_next=False, next_cursor=None
        )
        response = PagedResponse(items=[{}] * 5, page_info=page_info)

        next_params = strategy.get_next_params(current_params, response)

        assert next_params is None

    def test_extract_page_info_with_cursor(self):
        """Testa extração de informações com cursor"""
        strategy = CursorBasedStrategy(cursor_field='timestamp')
        response_data = {
            'items': [
                {'id': 1, 'timestamp': '2024-01-01T10:00:00Z'},
                {'id': 2, 'timestamp': '2024-01-01T11:00:00Z'},
                {'id': 3, 'timestamp': '2024-01-01T12:00:00Z'},
            ]
        }

        page_info = strategy.extract_page_info(response_data, 1, 3)

        assert page_info.current_page == 1
        assert page_info.page_size == 3
        assert page_info.has_next is True
        assert page_info.next_cursor == '2024-01-01T12:00:00Z'

    def test_extract_page_info_partial_page(self):
        """Testa extração com página incompleta (última página)"""
        strategy = CursorBasedStrategy()
        response_data = {
            'data': [
                {'id': 'item1'},
                {'id': 'item2'},  # Apenas 2 items de uma página de 5
            ]
        }

        page_info = strategy.extract_page_info(response_data, 3, 5)

        assert page_info.current_page == 3
        assert page_info.page_size == 5
        assert page_info.has_next is False  # Página não está cheia
        assert page_info.next_cursor is None

    def test_cursor_strategy_get_next_params_no_cursor(self):
        """Testa quando não há cursor para próxima página."""
        strategy = CursorBasedStrategy()

        current_params = {'size': 10}
        page_info = PageInfo(
            current_page=1, page_size=10, has_next=True, next_cursor=None
        )
        response = PagedResponse(items=['item'] * 10, page_info=page_info)

        next_params = strategy.get_next_params(current_params, response)
        assert next_params is None

    def test_cursor_strategy_extract_page_info_no_cursor_field(self):
        """Testa extração quando item não tem campo cursor."""
        strategy = CursorBasedStrategy()

        response_data = {
            'items': [
                {'name': 'item1'},  # Sem campo 'id'
                {'name': 'item2'},
                {'name': 'item3'},
            ]
        }

        page_info = strategy.extract_page_info(response_data, 1, 3)

        assert page_info.has_next is False
        assert page_info.next_cursor is None


class TestSicoobPaginationStrategy:
    """Testes para estratégia específica do Sicoob"""

    def test_extract_page_info_array_response(self):
        """Testa extração de array direto"""
        strategy = SicoobPaginationStrategy()
        response_data = [{'txid': 'abc123'}, {'txid': 'def456'}, {'txid': 'ghi789'}]

        page_info = strategy.extract_page_info(response_data, 1, 3)

        assert page_info.current_page == 1
        assert page_info.page_size == 3
        assert page_info.has_next is True  # Página cheia

    def test_extract_page_info_cobs_response(self):
        """Testa extração de resposta PIX com 'cobs'"""
        strategy = SicoobPaginationStrategy()
        response_data = {'cobs': [{'txid': 'abc123'}, {'txid': 'def456'}]}

        page_info = strategy.extract_page_info(response_data, 1, 5)

        assert page_info.current_page == 1
        assert page_info.page_size == 5
        assert page_info.has_next is False  # Página não está cheia

    def test_extract_page_info_lancamentos_response(self):
        """Testa extração de resposta de extrato com 'lancamentos'"""
        strategy = SicoobPaginationStrategy()
        response_data = {
            'lancamentos': [
                {'data': '2024-01-01', 'valor': '100.00'},
                {'data': '2024-01-02', 'valor': '200.00'},
            ]
        }

        page_info = strategy.extract_page_info(response_data, 1, 2)

        assert page_info.current_page == 1
        assert page_info.page_size == 2
        assert page_info.has_next is True  # Página cheia

    def test_get_next_params_simple_pagination(self):
        """Testa cálculo de próxima página simples"""
        strategy = SicoobPaginationStrategy()
        current_params = {'inicio': '2024-01-01', 'fim': '2024-01-31'}

        page_info = PageInfo(current_page=1, page_size=100, has_next=True)
        response = PagedResponse(items=[{}] * 100, page_info=page_info)

        next_params = strategy.get_next_params(current_params, response)

        expected = {'inicio': '2024-01-01', 'fim': '2024-01-31', 'page': 2}
        assert next_params == expected

    def test_sicoob_strategy_get_next_params_partial_page(self):
        """Testa quando página parcial indica fim dos dados."""
        strategy = SicoobPaginationStrategy()

        current_params = {'limit': 10}
        page_info = PageInfo(current_page=2, page_size=10, has_next=True)
        response = PagedResponse(
            items=['item'] * 5, page_info=page_info
        )  # Menos que page_size

        next_params = strategy.get_next_params(current_params, response)
        assert next_params is None

    def test_sicoob_strategy_get_next_params_no_next(self):
        """Testa quando não há próxima página."""
        strategy = SicoobPaginationStrategy()

        current_params = {'limit': 10}
        page_info = PageInfo(current_page=2, page_size=10, has_next=False)
        response = PagedResponse(items=['item'] * 5, page_info=page_info)

        next_params = strategy.get_next_params(current_params, response)
        assert next_params is None

    def test_sicoob_strategy_extract_page_info_no_matching_key(self):
        """Testa extração quando não encontra chave conhecida."""
        strategy = SicoobPaginationStrategy()

        response_data = {'unknown_key': ['item1', 'item2']}

        page_info = strategy.extract_page_info(response_data, 1, 10)

        assert page_info.has_next is False  # items vazio


class TestPaginatedIterator:
    """Testes para iterator paginado"""

    def test_iterator_single_page(self):
        """Testa iterator com uma única página"""

        def mock_fetch(params):
            return {'items': [{'id': 1}, {'id': 2}, {'id': 3}]}

        config = PaginationConfig(page_size=10)
        strategy = SicoobPaginationStrategy()

        iterator = PaginatedIterator(
            fetch_function=mock_fetch,
            initial_params={},
            config=config,
            strategy=strategy,
        )

        items = list(iterator)
        assert len(items) == 3
        assert items == [{'id': 1}, {'id': 2}, {'id': 3}]

    def test_iterator_multiple_pages(self):
        """Testa iterator com múltiplas páginas"""
        call_count = 0

        def mock_fetch(params):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                return {'items': [{'id': 1}, {'id': 2}]}
            elif call_count == 2:
                return {'items': [{'id': 3}, {'id': 4}]}
            else:
                return {'items': [{'id': 5}]}  # Última página parcial

        config = PaginationConfig(page_size=2)
        strategy = SicoobPaginationStrategy()

        iterator = PaginatedIterator(
            fetch_function=mock_fetch,
            initial_params={},
            config=config,
            strategy=strategy,
        )

        items = list(iterator)
        assert len(items) == 5
        assert items == [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}, {'id': 5}]

    def test_iterator_max_pages_limit(self):
        """Testa limite de páginas"""
        call_count = 0

        def mock_fetch(params):
            nonlocal call_count
            call_count += 1
            return {'items': [{'id': call_count}, {'id': call_count + 10}]}

        config = PaginationConfig(page_size=2, max_pages=2)
        strategy = SicoobPaginationStrategy()

        iterator = PaginatedIterator(
            fetch_function=mock_fetch,
            initial_params={},
            config=config,
            strategy=strategy,
        )

        items = list(iterator)
        assert len(items) == 4  # 2 páginas × 2 items
        assert call_count == 2

    def test_iterator_with_retry(self):
        """Testa retry automático em caso de erro"""
        call_count = 0

        def mock_fetch(params):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                raise Exception('Falha temporária')
            return {'items': [{'id': 1}]}

        config = PaginationConfig(page_size=10, max_retries=2, retry_delay=0.01)
        strategy = SicoobPaginationStrategy()

        iterator = PaginatedIterator(
            fetch_function=mock_fetch,
            initial_params={},
            config=config,
            strategy=strategy,
        )

        items = list(iterator)
        assert len(items) == 1
        assert call_count == 2

    def test_iterator_retry_exhausted(self):
        """Testa quando retries são esgotados"""

        def mock_fetch(params):
            raise Exception('Falha persistente')

        config = PaginationConfig(page_size=10, max_retries=1, retry_delay=0.01)
        strategy = SicoobPaginationStrategy()

        iterator = PaginatedIterator(
            fetch_function=mock_fetch,
            initial_params={},
            config=config,
            strategy=strategy,
        )

        with pytest.raises(PaginationError, match='Falha ao buscar página'):
            list(iterator)

    def test_iterator_custom_item_extractor(self):
        """Testa extrator customizado de items"""

        def mock_fetch(params):
            return {'payload': {'records': [{'name': 'João'}, {'name': 'Maria'}]}}

        def custom_extractor(data):
            return data['payload']['records']

        config = PaginationConfig(page_size=10)
        strategy = SicoobPaginationStrategy()

        iterator = PaginatedIterator(
            fetch_function=mock_fetch,
            initial_params={},
            config=config,
            strategy=strategy,
            item_extractor=custom_extractor,
        )

        items = list(iterator)
        assert len(items) == 2
        assert items == [{'name': 'João'}, {'name': 'Maria'}]

    def test_paginated_iterator_creation(self):
        """Testa criação do iterador."""

        def mock_fetch(params):
            return {'items': ['item1', 'item2']}

        config = PaginationConfig(page_size=10)
        strategy = OffsetBasedStrategy()

        iterator = PaginatedIterator(
            fetch_function=mock_fetch,
            initial_params={'limit': 10},
            config=config,
            strategy=strategy,
        )

        assert iterator.current_page == 1
        assert iterator.pages_fetched == 0
        assert iterator.total_items_fetched == 0
        assert iterator.finished is False

    def test_paginated_iterator_auto_sets_limit_param(self):
        """Testa que limit é configurado automaticamente."""
        captured_params = []

        def mock_fetch(params):
            captured_params.append(params.copy())
            return {'items': ['item1']}

        config = PaginationConfig(page_size=50)
        strategy = SicoobPaginationStrategy()

        iterator = PaginatedIterator(
            fetch_function=mock_fetch,
            initial_params={},
            config=config,
            strategy=strategy,
        )

        list(iterator)

        assert captured_params[0]['limit'] == 50

    def test_paginated_iterator_preserves_existing_limit(self):
        """Testa que não sobrescreve limit existente."""
        captured_params = []

        def mock_fetch(params):
            captured_params.append(params.copy())
            return {'items': ['item1']}

        config = PaginationConfig(page_size=50)
        strategy = SicoobPaginationStrategy()

        iterator = PaginatedIterator(
            fetch_function=mock_fetch,
            initial_params={'size': 100},  # Já tem size
            config=config,
            strategy=strategy,
        )

        list(iterator)

        # Não deve adicionar limit pois já tem size
        assert 'limit' not in captured_params[0]
        assert captured_params[0]['size'] == 100

    @patch('time.sleep')
    def test_paginated_iterator_no_auto_retry(self, mock_sleep):
        """Testa quando auto_retry está desabilitado."""

        def mock_fetch(params):
            raise Exception('Error without retry')

        config = PaginationConfig(page_size=10, auto_retry=False)
        strategy = SicoobPaginationStrategy()

        iterator = PaginatedIterator(
            fetch_function=mock_fetch,
            initial_params={},
            config=config,
            strategy=strategy,
        )

        with pytest.raises(PaginationError, match='Falha ao buscar página 1'):
            list(iterator)

        mock_sleep.assert_not_called()


class TestUtilityFunctions:
    """Testes para funções utilitárias"""

    def test_paginated_response_from_data_array(self):
        """Testa criação de PagedResponse a partir de array"""
        data = [{'id': 1}, {'id': 2}, {'id': 3}]

        response = paginated_response_from_data(data, page=1, page_size=10)

        assert response.items == data
        assert response.page_info.current_page == 1
        assert response.page_info.page_size == 10
        assert response.page_info.has_next is False  # Página não está cheia
        assert response.raw_response == data

    def test_paginated_response_from_data_object(self):
        """Testa criação de PagedResponse a partir de objeto"""
        data = {'cobs': [{'txid': 'abc123'}, {'txid': 'def456'}], 'total': 50}

        response = paginated_response_from_data(data, page=2, page_size=2)

        assert response.items == [{'txid': 'abc123'}, {'txid': 'def456'}]
        assert response.page_info.current_page == 2
        assert response.page_info.page_size == 2
        assert response.page_info.has_next is True  # Página cheia
        assert response.raw_response == data

    def test_paginated_response_custom_strategy(self):
        """Testa criação com estratégia customizada"""
        strategy = OffsetBasedStrategy()
        data = {'items': [{'id': 1}], 'total': 25}

        response = paginated_response_from_data(
            data, page=3, page_size=10, strategy=strategy
        )

        assert response.items == [{'id': 1}]
        assert response.page_info.total_items == 25
        assert response.page_info.total_pages == 3


@pytest.mark.integration
class TestPaginationIntegration:
    """Testes de integração para paginação"""

    def test_real_world_pix_pagination_simulation(self):
        """Simula paginação real de cobranças PIX"""
        # Simula resposta da API PIX do Sicoob
        pages_data = [
            {
                'cobs': [
                    {'txid': f'pix_{i:03d}', 'valor': {'original': f'{i * 10}.00'}}
                    for i in range(1, 101)  # 100 items na primeira página
                ]
            },
            {
                'cobs': [
                    {'txid': f'pix_{i:03d}', 'valor': {'original': f'{i * 10}.00'}}
                    for i in range(101, 151)  # 50 items na segunda página
                ]
            },
        ]

        call_count = 0

        def mock_fetch(params):
            nonlocal call_count
            if call_count < len(pages_data):
                result = pages_data[call_count]
                call_count += 1
                return result
            return {'cobs': []}

        config = PaginationConfig(page_size=100)
        strategy = SicoobPaginationStrategy()

        iterator = PaginatedIterator(
            fetch_function=mock_fetch,
            initial_params={'inicio': '2024-01-01', 'fim': '2024-01-31'},
            config=config,
            strategy=strategy,
        )

        # Coleta todas as cobranças
        all_items = list(iterator)

        assert len(all_items) == 150  # 100 + 50
        assert all_items[0]['txid'] == 'pix_001'
        assert all_items[99]['txid'] == 'pix_100'
        assert all_items[149]['txid'] == 'pix_150'

    def test_pagination_with_errors_and_retry(self):
        """Testa paginação com erros e retry"""
        call_count = 0

        def unreliable_fetch(params):
            nonlocal call_count
            call_count += 1

            # Falha na primeira tentativa de cada página
            if call_count in [1, 3]:
                raise Exception('Erro de rede temporário')
            elif call_count in [2]:
                return {'boletos': [{'id': 1}, {'id': 2}]}
            else:  # call_count == 4
                return {'boletos': [{'id': 3}]}  # Última página

        config = PaginationConfig(
            page_size=2, auto_retry=True, max_retries=1, retry_delay=0.01
        )
        strategy = SicoobPaginationStrategy()

        iterator = PaginatedIterator(
            fetch_function=unreliable_fetch,
            initial_params={},
            config=config,
            strategy=strategy,
        )

        items = list(iterator)

        assert len(items) == 3
        assert items == [{'id': 1}, {'id': 2}, {'id': 3}]
        assert call_count == 4  # 2 retries para 2 páginas
