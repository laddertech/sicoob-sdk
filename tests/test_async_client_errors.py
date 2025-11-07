"""Testes para tratamento de erros HTTP no AsyncAPIClient

Testa as melhorias implementadas para debugging:
- Preservação de response_text em exceções
- Formatação de mensagens de validação
- get_error_details() em SicoobError
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from sicoob.async_boleto import AsyncBoletoAPI
from sicoob.async_client import AsyncAPIClient
from sicoob.exceptions import BoletoError, SicoobError


@pytest_asyncio.fixture
async def mock_api_client():
    """Mock do cliente API assíncrono"""
    mock_client = MagicMock(spec=AsyncAPIClient)
    mock_client._get_base_url = MagicMock(return_value='https://api.sicoob.com.br')
    mock_client._make_request = AsyncMock()
    return mock_client


@pytest_asyncio.fixture
async def async_boleto_api(mock_api_client):
    """Fixture para AsyncBoletoAPI"""
    return AsyncBoletoAPI(mock_api_client)


class TestSicoobErrorDetails:
    """Testes para SicoobError.get_error_details()"""

    def test_get_error_details_with_json_response(self):
        """Testa extração de detalhes de resposta JSON"""
        response_text = json.dumps(
            {
                'mensagens': [
                    {'campo': 'numeroCliente', 'mensagem': 'Campo obrigatório'},
                    {'campo': 'valor', 'mensagem': 'Valor inválido'},
                ],
                'status': 400,
            }
        )

        error = SicoobError('Erro de validação', code=400, response_text=response_text)

        details = error.get_error_details()
        assert 'mensagens' in details
        assert len(details['mensagens']) == 2
        assert details['mensagens'][0]['campo'] == 'numeroCliente'

    def test_get_error_details_with_invalid_json(self):
        """Testa extração quando response não é JSON"""
        response_text = 'Not a JSON response'

        error = SicoobError('Erro genérico', code=500, response_text=response_text)

        details = error.get_error_details()
        assert 'raw_response' in details
        assert details['raw_response'] == 'Not a JSON response'

    def test_get_error_details_without_response_text(self):
        """Testa extração quando não há response_text"""
        error = SicoobError('Erro sem resposta', code=500)

        details = error.get_error_details()
        assert details == {}


class TestBoletoValidationErrors:
    """Testa formatação de erros de validação em boletos"""

    @pytest.mark.asyncio
    async def test_emitir_boleto_validation_error_formatted(
        self, async_boleto_api, mock_api_client
    ):
        """Testa que erros de validação 400 são formatados corretamente"""
        validation_response = {
            'mensagens': [
                {'campo': 'numeroCliente', 'mensagem': 'Campo obrigatório'},
                {'campo': 'codigoModalidade', 'mensagem': 'Modalidade inválida'},
            ]
        }

        # Simula SicoobError com response_text
        sicoob_error = SicoobError(
            'HTTP 400', code=400, response_text=json.dumps(validation_response)
        )

        mock_api_client._make_request.side_effect = sicoob_error

        with pytest.raises(BoletoError) as exc_info:
            await async_boleto_api.emitir_boleto({'valor': 100})

        error_message = str(exc_info.value)
        assert 'Falha na validação do boleto' in error_message
        assert 'numeroCliente' in error_message
        assert 'Campo obrigatório' in error_message
        assert 'codigoModalidade' in error_message
        assert 'Modalidade inválida' in error_message

    @pytest.mark.asyncio
    async def test_emitir_boleto_preserves_response_text(
        self, async_boleto_api, mock_api_client
    ):
        """Testa que response_text é preservado na exceção BoletoError"""
        response_text = json.dumps({'erro': 'Detalhes completos do erro'})

        sicoob_error = SicoobError('HTTP 404', code=404, response_text=response_text)

        mock_api_client._make_request.side_effect = sicoob_error

        with pytest.raises(BoletoError) as exc_info:
            await async_boleto_api.emitir_boleto({'valor': 100})

        # Verifica que BoletoError tem response_text preservado
        assert exc_info.value.response_text == response_text
        assert exc_info.value.code == 404

    @pytest.mark.asyncio
    async def test_emitir_boleto_generic_error_preserves_details(
        self, async_boleto_api, mock_api_client
    ):
        """Testa que erros sem 'mensagens' preservam response_text"""
        response_text = 'Erro interno do servidor'

        sicoob_error = SicoobError('HTTP 500', code=500, response_text=response_text)

        mock_api_client._make_request.side_effect = sicoob_error

        with pytest.raises(BoletoError) as exc_info:
            await async_boleto_api.emitir_boleto({'valor': 100})

        assert exc_info.value.response_text == response_text
        assert 'Erro ao emitir boleto' in str(exc_info.value)


class TestHTTP404Handling:
    """Testa tratamento especial de erro 404"""

    @pytest.mark.asyncio
    async def test_404_with_validation_messages(
        self, async_boleto_api, mock_api_client
    ):
        """Testa 404 com mensagens de validação (caso específico Sicoob)"""
        response_data = {
            'mensagens': [{'campo': 'nossoNumero', 'mensagem': 'Boleto já existe'}]
        }

        sicoob_error = SicoobError(
            'HTTP 404', code=404, response_text=json.dumps(response_data)
        )

        mock_api_client._make_request.side_effect = sicoob_error

        with pytest.raises(BoletoError) as exc_info:
            await async_boleto_api.emitir_boleto({'nossoNumero': 123})

        # Verifica formatação
        error_msg = str(exc_info.value)
        assert '404' in error_msg or 'Falha na validação' in error_msg
        assert exc_info.value.response_text is not None

    @pytest.mark.asyncio
    async def test_404_without_json_body(self, async_boleto_api, mock_api_client):
        """Testa 404 sem corpo JSON (erro real)"""
        sicoob_error = SicoobError('HTTP 404', code=404, response_text='Not Found')

        mock_api_client._make_request.side_effect = sicoob_error

        with pytest.raises(BoletoError) as exc_info:
            await async_boleto_api.emitir_boleto({'valor': 100})

        assert exc_info.value.code == 404
        assert exc_info.value.response_text == 'Not Found'
