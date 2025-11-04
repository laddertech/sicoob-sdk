"""Testes para o módulo async_boleto.py"""

from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from sicoob.async_boleto import AsyncBoletoAPI
from sicoob.async_client import AsyncAPIClient
from sicoob.exceptions import BoletoError, BoletoNaoEncontradoError


@pytest_asyncio.fixture
async def mock_api_client():
    """Mock do cliente API assíncrono"""
    mock_client = Mock(spec=AsyncAPIClient)
    mock_client._get_base_url.return_value = 'https://api.sicoob.com.br/prd'
    mock_client._make_request = AsyncMock()
    return mock_client


@pytest_asyncio.fixture
async def async_boleto_api(mock_api_client):
    """Fixture para AsyncBoletoAPI"""
    return AsyncBoletoAPI(mock_api_client)


class TestAsyncBoletoAPI:
    """Testes para AsyncBoletoAPI"""

    @pytest.mark.asyncio
    async def test_init(self, mock_api_client):
        """Testa inicialização da API de boleto"""
        api = AsyncBoletoAPI(mock_api_client)
        assert api.api_client is mock_api_client

    @pytest.mark.asyncio
    async def test_emitir_boleto_without_nosso_numero(
        self, async_boleto_api, mock_api_client
    ):
        """Testa emissão de boleto sem nosso número"""
        dados = {'valor': 100.00, 'pagador': {'nome': 'Teste'}}
        expected_response = {'nossoNumero': '12345678901'}

        mock_api_client._make_request.return_value = expected_response

        result = await async_boleto_api.emitir_boleto(dados)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'POST',
            'https://api.sicoob.com.br/prd/cobranca-bancaria/boleto',
            scope='boletos_inclusao',
            json=dados,
        )

    @pytest.mark.asyncio
    async def test_emitir_boleto_with_nosso_numero(
        self, async_boleto_api, mock_api_client
    ):
        """Testa emissão de boleto com nosso número"""
        dados = {'valor': 100.00, 'pagador': {'nome': 'Teste'}}
        nosso_numero = '12345678901'
        expected_response = {'nossoNumero': nosso_numero}

        mock_api_client._make_request.return_value = expected_response

        result = await async_boleto_api.emitir_boleto(dados, nosso_numero)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'PUT',
            f'https://api.sicoob.com.br/prd/cobranca-bancaria/boleto/{nosso_numero}',
            scope='boletos_inclusao',
            json=dados,
        )

    @pytest.mark.asyncio
    async def test_emitir_boleto_error(self, async_boleto_api, mock_api_client):
        """Testa erro na emissão de boleto"""
        dados = {'valor': 100.00}
        mock_api_client._make_request.side_effect = Exception('API Error')

        with pytest.raises(BoletoError, match='Erro ao emitir boleto'):
            await async_boleto_api.emitir_boleto(dados)

    @pytest.mark.asyncio
    async def test_consultar_boleto_success(self, async_boleto_api, mock_api_client):
        """Testa consulta de boleto com sucesso"""
        nosso_numero = '12345678901'
        expected_response = {'nossoNumero': nosso_numero, 'status': 'REGISTRADO'}

        mock_api_client._make_request.return_value = expected_response

        result = await async_boleto_api.consultar_boleto(nosso_numero)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET',
            f'https://api.sicoob.com.br/prd/cobranca-bancaria/boleto/{nosso_numero}',
            scope='boletos_consulta',
        )

    @pytest.mark.asyncio
    async def test_consultar_boleto_not_found(self, async_boleto_api, mock_api_client):
        """Testa boleto não encontrado"""
        nosso_numero = '12345678901'
        mock_api_client._make_request.side_effect = Exception('404 - não encontrado')

        with pytest.raises(BoletoNaoEncontradoError):
            await async_boleto_api.consultar_boleto(nosso_numero)

    @pytest.mark.asyncio
    async def test_consultar_boleto_other_error(
        self, async_boleto_api, mock_api_client
    ):
        """Testa outros erros na consulta de boleto"""
        nosso_numero = '12345678901'
        mock_api_client._make_request.side_effect = Exception('500 - Internal Error')

        with pytest.raises(BoletoError, match='Erro ao consultar boleto'):
            await async_boleto_api.consultar_boleto(nosso_numero)

    @pytest.mark.asyncio
    async def test_listar_boletos_with_filters(self, async_boleto_api, mock_api_client):
        """Testa listagem de boletos com filtros"""
        expected_response = {'content': []}
        mock_api_client._make_request.return_value = expected_response

        result = await async_boleto_api.listar_boletos(
            data_inicio='2023-01-01',
            data_fim='2023-01-31',
            situacao='REGISTRADO',
            nosso_numero='123',
        )

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/prd/cobranca-bancaria/boleto',
            scope='boletos_consulta',
            params={
                'dataInicio': '2023-01-01',
                'dataFim': '2023-01-31',
                'situacao': 'REGISTRADO',
                'nosso_numero': '123',
            },
        )

    @pytest.mark.asyncio
    async def test_listar_boletos_without_filters(
        self, async_boleto_api, mock_api_client
    ):
        """Testa listagem de boletos sem filtros"""
        expected_response = {'content': []}
        mock_api_client._make_request.return_value = expected_response

        result = await async_boleto_api.listar_boletos()

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/prd/cobranca-bancaria/boleto',
            scope='boletos_consulta',
            params={},
        )

    @pytest.mark.asyncio
    async def test_consultar_por_pagador(self, async_boleto_api, mock_api_client):
        """Testa consulta por pagador"""
        cpf_cnpj = '12345678901'
        expected_response = {'content': []}

        mock_api_client._make_request.return_value = expected_response

        with patch('sicoob.async_boleto.validate_cpf', return_value=cpf_cnpj):
            with patch('sicoob.async_boleto.validate_cnpj', return_value=cpf_cnpj):
                result = await async_boleto_api.consultar_por_pagador(
                    cpf_cnpj, data_inicio='2023-01-01', data_fim='2023-01-31'
                )

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/prd/cobranca-bancaria/boleto/pagador',
            scope='boletos_consulta',
            params={
                'cpfCnpj': cpf_cnpj,
                'dataInicio': '2023-01-01',
                'dataFim': '2023-01-31',
            },
        )

    @pytest.mark.asyncio
    async def test_consultar_por_pagador_without_dates(
        self, async_boleto_api, mock_api_client
    ):
        """Testa consulta por pagador sem datas"""
        cpf_cnpj = '12345678901'
        expected_response = {'content': []}

        mock_api_client._make_request.return_value = expected_response

        with patch('sicoob.async_boleto.validate_cpf', return_value=cpf_cnpj):
            with patch('sicoob.async_boleto.validate_cnpj', return_value=cpf_cnpj):
                result = await async_boleto_api.consultar_por_pagador(cpf_cnpj)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/prd/cobranca-bancaria/boleto/pagador',
            scope='boletos_consulta',
            params={'cpfCnpj': cpf_cnpj},
        )

    @pytest.mark.asyncio
    async def test_alterar_boleto(self, async_boleto_api, mock_api_client):
        """Testa alteração de boleto"""
        nosso_numero = '12345678901'
        dados_alteracao = {'dataVencimento': '2023-12-31'}
        expected_response = {'nossoNumero': nosso_numero, 'status': 'ALTERADO'}

        mock_api_client._make_request.return_value = expected_response

        result = await async_boleto_api.alterar_boleto(nosso_numero, dados_alteracao)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'PATCH',
            f'https://api.sicoob.com.br/prd/cobranca-bancaria/boleto/{nosso_numero}',
            scope='boletos_alteracao',
            json=dados_alteracao,
        )

    @pytest.mark.asyncio
    async def test_baixar_boleto(self, async_boleto_api, mock_api_client):
        """Testa baixa de boleto"""
        nosso_numero = '12345678901'
        dados_baixa = {'motivoBaixa': 1}
        expected_response = {'message': 'Boleto baixado'}

        mock_api_client._make_request.return_value = expected_response

        result = await async_boleto_api.baixar_boleto(nosso_numero, dados_baixa)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'POST',
            f'https://api.sicoob.com.br/prd/cobranca-bancaria/boleto/{nosso_numero}/baixa',
            scope='boletos_alteracao',
            json=dados_baixa,
        )

    @pytest.mark.asyncio
    async def test_emitir_boletos_lote(self, async_boleto_api, mock_api_client):
        """Testa emissão de múltiplos boletos"""
        lista_dados = [
            {'valor': 100.00, 'pagador': {'nome': 'Teste1'}},
            {'valor': 200.00, 'pagador': {'nome': 'Teste2'}},
        ]
        expected_responses = [
            {'nossoNumero': '12345678901'},
            {'nossoNumero': '12345678902'},
        ]

        with patch(
            'sicoob.async_client.gather_with_concurrency',
            return_value=expected_responses,
        ) as mock_gather:
            with patch.object(async_boleto_api, 'emitir_boleto') as mock_emitir:
                result = await async_boleto_api.emitir_boletos_lote(
                    lista_dados, max_concorrencia=5
                )

                assert result == expected_responses
                assert mock_emitir.call_count == 2
                mock_gather.assert_called_once()

    @pytest.mark.asyncio
    async def test_consultar_boletos_lote(self, async_boleto_api, mock_api_client):
        """Testa consulta de múltiplos boletos"""
        nossos_numeros = ['12345678901', '12345678902']
        expected_responses = [
            {'nossoNumero': '12345678901', 'status': 'REGISTRADO'},
            {'nossoNumero': '12345678902', 'status': 'PAGO'},
        ]

        with patch(
            'sicoob.async_client.gather_with_concurrency',
            return_value=expected_responses,
        ) as mock_gather:
            with patch.object(async_boleto_api, 'consultar_boleto') as mock_consultar:
                result = await async_boleto_api.consultar_boletos_lote(
                    nossos_numeros, max_concorrencia=5
                )

                assert result == expected_responses
                assert mock_consultar.call_count == 2
                mock_gather.assert_called_once()

    @pytest.mark.asyncio
    async def test_processar_vencimentos_hoje_with_vencidos(
        self, async_boleto_api, mock_api_client
    ):
        """Testa processamento de vencimentos incluindo vencidos"""
        hoje = date.today()
        data_hoje = hoje.strftime('%Y-%m-%d')

        mock_response = {
            'content': [
                {'nossoNumero': '123', 'valor': 100.50, 'dataVencimento': data_hoje},
                {'nossoNumero': '124', 'valor': 200.75, 'dataVencimento': data_hoje},
            ]
        }

        with patch.object(
            async_boleto_api, 'listar_boletos', return_value=mock_response
        ) as mock_listar:
            result = await async_boleto_api.processar_vencimentos_hoje(
                incluir_vencidos=True
            )

            assert result['total_boletos'] == 2
            assert result['valor_total'] == 301.25
            assert result['vencimento_hoje'] == 2
            assert result['data_processamento'] == data_hoje

            # Verifica se foi chamado com o range de 7 dias
            args = mock_listar.call_args[1]
            assert 'data_inicio' in args
            assert args['data_fim'] == data_hoje

    @pytest.mark.asyncio
    async def test_processar_vencimentos_hoje_without_vencidos(
        self, async_boleto_api, mock_api_client
    ):
        """Testa processamento de vencimentos sem incluir vencidos"""
        hoje = date.today()
        data_hoje = hoje.strftime('%Y-%m-%d')

        mock_response = {
            'content': [
                {'nossoNumero': '123', 'valor': 100.50, 'dataVencimento': data_hoje}
            ]
        }

        with patch.object(
            async_boleto_api, 'listar_boletos', return_value=mock_response
        ) as mock_listar:
            result = await async_boleto_api.processar_vencimentos_hoje(
                incluir_vencidos=False
            )

            assert result['total_boletos'] == 1
            assert result['valor_total'] == 100.50
            assert result['vencimento_hoje'] == 1

            # Verifica se foi chamado apenas com a data de hoje
            args = mock_listar.call_args[1]
            assert args['data_inicio'] == data_hoje
            assert args['data_fim'] == data_hoje

    @pytest.mark.asyncio
    async def test_processar_vencimentos_hoje_empty_response(
        self, async_boleto_api, mock_api_client
    ):
        """Testa processamento sem boletos"""
        mock_response = {'content': []}

        with patch.object(
            async_boleto_api, 'listar_boletos', return_value=mock_response
        ):
            result = await async_boleto_api.processar_vencimentos_hoje()

            assert result['total_boletos'] == 0
            assert result['valor_total'] == 0.0
            assert result['vencimento_hoje'] == 0
