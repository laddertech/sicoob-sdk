"""Testes para o módulo async_pix.py"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from sicoob.async_client import AsyncAPIClient
from sicoob.async_pix import AsyncPixAPI
from sicoob.exceptions import (
    CobrancaPixNaoEncontradaError,
    PixError,
    WebhookPixNaoEncontradoError,
)


@pytest_asyncio.fixture
async def mock_api_client():
    """Mock do cliente API assíncrono"""
    mock_client = Mock(spec=AsyncAPIClient)
    mock_client._get_base_url.return_value = 'https://api.sicoob.com.br/prd'
    mock_client._make_request = AsyncMock()
    mock_client.logger = Mock()
    return mock_client


@pytest_asyncio.fixture
async def async_pix_api(mock_api_client):
    """Fixture para AsyncPixAPI"""
    return AsyncPixAPI(mock_api_client)


class TestAsyncPixAPI:
    """Testes para AsyncPixAPI"""

    @pytest.mark.asyncio
    async def test_init(self, mock_api_client):
        """Testa inicialização da API PIX"""
        api = AsyncPixAPI(mock_api_client)
        assert api.api_client is mock_api_client

    @pytest.mark.asyncio
    async def test_criar_cobranca_imediata_success(
        self, async_pix_api, mock_api_client
    ):
        """Testa criação de cobrança PIX imediata com sucesso"""
        txid = 'abcd1234567890123456789012'
        dados = {'valor': {'original': '100.00'}}
        expected_response = {'txid': txid, 'status': 'ATIVA'}

        mock_api_client._make_request.return_value = expected_response

        with patch('sicoob.async_pix.validate_txid', return_value=txid):
            result = await async_pix_api.criar_cobranca_imediata(txid, dados)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'PUT',
            f'https://api.sicoob.com.br/prd/pix/cob/{txid}',
            scope='cob.write',
            json=dados,
        )

    @pytest.mark.asyncio
    async def test_criar_cobranca_imediata_error(self, async_pix_api, mock_api_client):
        """Testa erro na criação de cobrança PIX"""
        txid = 'abcd1234567890123456789012'
        dados = {'valor': {'original': '100.00'}}

        mock_api_client._make_request.side_effect = Exception('API Error')

        with patch('sicoob.async_pix.validate_txid', return_value=txid):
            with pytest.raises(PixError, match='Erro ao criar cobrança PIX'):
                await async_pix_api.criar_cobranca_imediata(txid, dados)

    @pytest.mark.asyncio
    async def test_consultar_cobranca_imediata_success(
        self, async_pix_api, mock_api_client
    ):
        """Testa consulta de cobrança PIX com sucesso"""
        txid = 'abcd1234567890123456789012'
        expected_response = {'txid': txid, 'status': 'ATIVA'}

        mock_api_client._make_request.return_value = expected_response

        with patch('sicoob.async_pix.validate_txid', return_value=txid):
            result = await async_pix_api.consultar_cobranca_imediata(txid)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET', f'https://api.sicoob.com.br/prd/pix/cob/{txid}', scope='cob.read'
        )

    @pytest.mark.asyncio
    async def test_consultar_cobranca_imediata_not_found(
        self, async_pix_api, mock_api_client
    ):
        """Testa cobrança PIX não encontrada"""
        txid = 'abcd1234567890123456789012'

        mock_api_client._make_request.side_effect = Exception('404 - não encontrada')

        with patch('sicoob.async_pix.validate_txid', return_value=txid):
            with pytest.raises(CobrancaPixNaoEncontradaError):
                await async_pix_api.consultar_cobranca_imediata(txid)

    @pytest.mark.asyncio
    async def test_listar_cobrancas(self, async_pix_api, mock_api_client):
        """Testa listagem de cobranças PIX"""
        inicio = '2023-01-01T00:00:00Z'
        fim = '2023-01-31T23:59:59Z'
        expected_response = {'cobs': []}

        mock_api_client._make_request.return_value = expected_response

        result = await async_pix_api.listar_cobrancas(inicio, fim, status='ATIVA')

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/prd/pix/cob',
            scope='cob.read',
            params={'inicio': inicio, 'fim': fim, 'status': 'ATIVA'},
        )

    @pytest.mark.asyncio
    async def test_criar_cobranca_com_vencimento(self, async_pix_api, mock_api_client):
        """Testa criação de cobrança PIX com vencimento"""
        txid = 'abcd1234567890123456789012'
        dados = {'valor': {'original': '100.00'}, 'vencimento': '2023-12-31'}
        expected_response = {'txid': txid, 'status': 'ATIVA'}

        mock_api_client._make_request.return_value = expected_response

        with patch('sicoob.async_pix.validate_txid', return_value=txid):
            result = await async_pix_api.criar_cobranca_com_vencimento(txid, dados)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'PUT',
            f'https://api.sicoob.com.br/prd/pix/cobv/{txid}',
            scope='cobv.write',
            json=dados,
        )

    @pytest.mark.asyncio
    async def test_consultar_cobranca_com_vencimento(
        self, async_pix_api, mock_api_client
    ):
        """Testa consulta de cobrança PIX com vencimento"""
        txid = 'abcd1234567890123456789012'
        expected_response = {'txid': txid, 'status': 'ATIVA'}

        mock_api_client._make_request.return_value = expected_response

        with patch('sicoob.async_pix.validate_txid', return_value=txid):
            result = await async_pix_api.consultar_cobranca_com_vencimento(
                txid, revisao=1
            )

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET',
            f'https://api.sicoob.com.br/prd/pix/cobv/{txid}',
            scope='cobv.read',
            params={'revisao': 1},
        )

    @pytest.mark.asyncio
    async def test_cadastrar_webhook(self, async_pix_api, mock_api_client):
        """Testa cadastro de webhook PIX"""
        chave = 'chave@exemplo.com'
        url_webhook = 'https://exemplo.com/webhook'
        expected_response = {'webhookUrl': url_webhook}

        mock_api_client._make_request.return_value = expected_response

        with patch('sicoob.async_pix.validate_url', return_value=url_webhook):
            result = await async_pix_api.cadastrar_webhook(chave, url_webhook)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'PUT',
            f'https://api.sicoob.com.br/prd/pix/webhook/{chave}',
            scope='webhook.write',
            json={'webhookUrl': url_webhook},
        )

    @pytest.mark.asyncio
    async def test_consultar_webhook(self, async_pix_api, mock_api_client):
        """Testa consulta de webhook PIX"""
        chave = 'chave@exemplo.com'
        expected_response = {'webhookUrl': 'https://exemplo.com/webhook'}

        mock_api_client._make_request.return_value = expected_response

        result = await async_pix_api.consultar_webhook(chave)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET',
            f'https://api.sicoob.com.br/prd/pix/webhook/{chave}',
            scope='webhook.read',
        )

    @pytest.mark.asyncio
    async def test_consultar_webhook_not_found(self, async_pix_api, mock_api_client):
        """Testa webhook PIX não encontrado"""
        chave = 'chave@exemplo.com'

        mock_api_client._make_request.side_effect = Exception('404')

        with pytest.raises(WebhookPixNaoEncontradoError):
            await async_pix_api.consultar_webhook(chave)

    @pytest.mark.asyncio
    async def test_excluir_webhook(self, async_pix_api, mock_api_client):
        """Testa exclusão de webhook PIX"""
        chave = 'chave@exemplo.com'
        expected_response = {'message': 'Webhook excluído'}

        mock_api_client._make_request.return_value = expected_response

        result = await async_pix_api.excluir_webhook(chave)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'DELETE',
            f'https://api.sicoob.com.br/prd/pix/webhook/{chave}',
            scope='webhook.write',
        )

    @pytest.mark.asyncio
    async def test_criar_lote_cobranca(self, async_pix_api, mock_api_client):
        """Testa criação de lote de cobranças PIX"""
        id_lote = 123
        dados = {'descricao': 'Lote de teste'}
        expected_response = {'id': id_lote, 'status': 'PROCESSANDO'}

        mock_api_client._make_request.return_value = expected_response

        result = await async_pix_api.criar_lote_cobranca(id_lote, dados)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'PUT',
            f'https://api.sicoob.com.br/prd/pix/lotecobv/{id_lote}',
            scope='lotecobv.write',
            json=dados,
        )

    @pytest.mark.asyncio
    async def test_consultar_lote_cobranca(self, async_pix_api, mock_api_client):
        """Testa consulta de lote de cobranças PIX"""
        id_lote = 123
        expected_response = {'id': id_lote, 'status': 'PROCESSADO'}

        mock_api_client._make_request.return_value = expected_response

        result = await async_pix_api.consultar_lote_cobranca(id_lote)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET',
            f'https://api.sicoob.com.br/prd/pix/lotecobv/{id_lote}',
            scope='lotecobv.read',
        )

    @pytest.mark.asyncio
    async def test_criar_cobrancas_lote(self, async_pix_api, mock_api_client):
        """Testa criação de múltiplas cobranças PIX"""
        cobrancas = [
            ('txid1', {'valor': {'original': '100.00'}}),
            ('txid2', {'valor': {'original': '200.00'}}),
        ]
        expected_responses = [
            {'txid': 'txid1', 'status': 'ATIVA'},
            {'txid': 'txid2', 'status': 'ATIVA'},
        ]

        with patch(
            'sicoob.async_pix.gather_with_concurrency', return_value=expected_responses
        ) as mock_gather:
            with patch.object(async_pix_api, 'criar_cobranca_imediata') as mock_criar:
                result = await async_pix_api.criar_cobrancas_lote(
                    cobrancas, max_concorrencia=5
                )

                assert result == expected_responses
                assert mock_criar.call_count == 2
                mock_gather.assert_called_once()

    @pytest.mark.asyncio
    async def test_consultar_cobrancas_lote(self, async_pix_api, mock_api_client):
        """Testa consulta de múltiplas cobranças PIX"""
        txids = ['txid1', 'txid2']
        expected_responses = [
            {'txid': 'txid1', 'status': 'ATIVA'},
            {'txid': 'txid2', 'status': 'PAGA'},
        ]

        with patch(
            'sicoob.async_pix.gather_with_concurrency', return_value=expected_responses
        ) as mock_gather:
            with patch.object(
                async_pix_api, 'consultar_cobranca_imediata'
            ) as mock_consultar:
                result = await async_pix_api.consultar_cobrancas_lote(
                    txids, max_concorrencia=5
                )

                assert result == expected_responses
                assert mock_consultar.call_count == 2
                mock_gather.assert_called_once()

    @pytest.mark.asyncio
    async def test_processar_cobrancas_periodo(self, async_pix_api, mock_api_client):
        """Testa processamento de cobranças por período"""
        inicio = datetime.now() - timedelta(days=7)
        fim = datetime.now()
        mock_response = {
            'cobs': [
                {'txid': 'txid1', 'valor': {'original': '100.50'}, 'status': 'ATIVA'},
                {'txid': 'txid2', 'valor': {'original': '200.75'}, 'status': 'PAGA'},
            ]
        }

        with patch.object(
            async_pix_api, 'listar_cobrancas', return_value=mock_response
        ):
            result = await async_pix_api.processar_cobrancas_periodo(inicio, fim)

            assert result['total_cobrancas'] == 2
            assert result['estatisticas']['valor_total'] == 301.25
            assert result['estatisticas']['valor_medio'] == 150.625
            assert result['estatisticas']['distribuicao_status'] == {
                'ATIVA': 1,
                'PAGA': 1,
            }

    @pytest.mark.asyncio
    async def test_gerar_relatorio_performance(self, async_pix_api, mock_api_client):
        """Testa geração de relatório de performance"""
        txids = ['txid1', 'txid2']
        mock_cobrancas = [
            {'txid': 'txid1', 'valor': {'original': '100.50'}, 'status': 'ATIVA'},
            {'txid': 'txid2', 'valor': {'original': '200.75'}, 'status': 'PAGA'},
        ]

        with patch.object(
            async_pix_api, 'consultar_cobrancas_lote', return_value=mock_cobrancas
        ):
            result = await async_pix_api.gerar_relatorio_performance(
                txids, max_concorrencia=5
            )

            metrics = result['metricas_performance']
            assert metrics['total_txids'] == 2
            assert metrics['cobrancas_encontradas'] == 2
            assert metrics['taxa_sucesso'] == 100.0
            assert 'throughput_txids_por_segundo' in metrics

            assert result['distribuicao_status'] == {'ATIVA': 1, 'PAGA': 1}
            assert result['analise_valores']['total'] == 301.25
