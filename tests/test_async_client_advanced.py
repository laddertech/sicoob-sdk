"""Testes avançados para o módulo async_client.py"""

import asyncio
import json
import ssl
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio
from aiohttp import ClientSession

from sicoob.async_client import (
    AsyncAPIClient,
    AsyncCobrancaAPI,
    AsyncContaCorrenteAPI,
    AsyncSicoob,
    async_batch_processor,
    gather_with_concurrency,
)
from sicoob.auth import OAuth2Client
from sicoob.config import SicoobConfig
from sicoob.exceptions import SicoobError


@pytest_asyncio.fixture
async def mock_oauth_client():
    """Mock do cliente OAuth2"""
    mock_client = Mock(spec=OAuth2Client)
    mock_client.get_access_token.return_value = 'fake_token'
    return mock_client


@pytest_asyncio.fixture
async def mock_session():
    """Mock da sessão aiohttp"""
    mock_session = AsyncMock(spec=ClientSession)
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value='{"success": true}')
    mock_response.json = AsyncMock(return_value={'success': True})
    mock_session.request.return_value.__aenter__.return_value = mock_response
    return mock_session


@pytest_asyncio.fixture
async def async_api_client(mock_oauth_client, mock_session):
    """Fixture para AsyncAPIClient"""
    client = AsyncAPIClient(
        oauth_client=mock_oauth_client,
        session=mock_session,
        max_concurrent_requests=5,
        request_timeout=10,
    )
    return client


class TestAsyncAPIClient:
    """Testes para AsyncAPIClient"""

    @pytest.mark.asyncio
    async def test_init(self, mock_oauth_client):
        """Testa inicialização do cliente API"""
        client = AsyncAPIClient(
            oauth_client=mock_oauth_client,
            max_concurrent_requests=5,
            request_timeout=10,
        )

        assert client.oauth_client is mock_oauth_client
        assert client.max_concurrent_requests == 5
        assert client.request_timeout == 10
        assert client._session is None
        assert client._owned_session is True

    @pytest.mark.asyncio
    async def test_init_with_session(self, mock_oauth_client, mock_session):
        """Testa inicialização com sessão existente"""
        client = AsyncAPIClient(oauth_client=mock_oauth_client, session=mock_session)

        assert client._session is mock_session
        assert client._owned_session is False

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_oauth_client):
        """Testa context manager"""
        async with AsyncAPIClient(oauth_client=mock_oauth_client) as client:
            assert client._session is not None

    @pytest.mark.asyncio
    async def test_ensure_session_creates_session(self, mock_oauth_client):
        """Testa criação de sessão"""
        client = AsyncAPIClient(oauth_client=mock_oauth_client)

        with patch('sicoob.async_client.ClientSession') as mock_client_session:
            with patch('sicoob.async_client.TCPConnector') as mock_connector:
                with patch('sicoob.async_client.ClientTimeout') as mock_timeout:
                    with patch.object(
                        SicoobConfig, 'get_current_config'
                    ) as mock_config:
                        mock_config.return_value.verify_ssl = True

                        await client._ensure_session()

                        mock_connector.assert_called_once()
                        mock_timeout.assert_called_once_with(total=30)
                        mock_client_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_session_ssl_disabled(self, mock_oauth_client):
        """Testa configuração SSL desabilitada"""
        client = AsyncAPIClient(oauth_client=mock_oauth_client)

        with patch('sicoob.async_client.ClientSession'):
            with patch('sicoob.async_client.TCPConnector'):
                with patch('sicoob.async_client.ClientTimeout'):
                    with patch.object(
                        SicoobConfig, 'get_current_config'
                    ) as mock_config:
                        with patch('ssl.create_default_context') as mock_ssl:
                            mock_config.return_value.verify_ssl = False
                            mock_context = MagicMock()
                            mock_ssl.return_value = mock_context

                            await client._ensure_session()

                            assert mock_context.check_hostname is False
                            assert mock_context.verify_mode == ssl.CERT_NONE

    def test_get_base_url_sandbox(self, mock_oauth_client):
        """Testa URL base em modo sandbox"""
        with patch.object(
            SicoobConfig, 'get_base_url', return_value='https://sandbox.sicoob.com.br'
        ):
            client = AsyncAPIClient(oauth_client=mock_oauth_client)
            url = client._get_base_url()
            assert 'sandbox.sicoob.com.br' in url

    def test_get_base_url_production(self, mock_oauth_client):
        """Testa URL base em modo produção"""
        with patch.object(
            SicoobConfig, 'get_base_url', return_value='https://api.sicoob.com.br'
        ):
            client = AsyncAPIClient(oauth_client=mock_oauth_client)
            url = client._get_base_url()
            assert 'api.sicoob.com.br' in url

    def test_get_headers(self, mock_oauth_client):
        """Testa geração de headers"""
        client = AsyncAPIClient(oauth_client=mock_oauth_client)
        headers = client._get_headers('test_scope')

        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer fake_token'
        assert headers['Content-Type'] == 'application/json'
        assert headers['Accept'] == 'application/json'
        assert 'User-Agent' in headers

    def test_validate_response_data_valid(self, mock_oauth_client):
        """Testa validação de dados de resposta válidos"""
        client = AsyncAPIClient(oauth_client=mock_oauth_client)
        data = {'key': 'value'}
        result = client._validate_response_data(data, 200)
        assert result == data

    def test_validate_response_data_invalid(self, mock_oauth_client):
        """Testa validação de dados de resposta inválidos"""
        client = AsyncAPIClient(oauth_client=mock_oauth_client)
        with pytest.raises(SicoobError, match='Resposta não é JSON válido'):
            client._validate_response_data('invalid', 200)

    @pytest.mark.asyncio
    async def test_make_request_success(self, async_api_client, mock_session):
        """Testa requisição bem-sucedida"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"success": true}')
        mock_response.json = AsyncMock(return_value={'success': True})

        async_api_client._session = mock_session
        mock_session.request.return_value.__aenter__.return_value = mock_response

        result = await async_api_client._make_request(
            'GET', 'https://api.example.com/test', 'test_scope'
        )

        assert result == {'success': True}

    @pytest.mark.asyncio
    async def test_make_request_http_error(self, async_api_client, mock_session):
        """Testa erro HTTP"""
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value='Bad Request')
        mock_response.json = AsyncMock(return_value={'message': 'Bad Request'})

        async_api_client._session = mock_session
        mock_session.request.return_value.__aenter__.return_value = mock_response

        with pytest.raises(SicoobError, match='Bad Request'):
            await async_api_client._make_request(
                'GET', 'https://api.example.com/test', 'test_scope'
            )

    @pytest.mark.asyncio
    async def test_make_request_timeout_error(self, async_api_client, mock_session):
        """Testa erro de timeout"""
        async_api_client._session = mock_session
        mock_session.request.side_effect = asyncio.TimeoutError('Timeout')

        with pytest.raises(SicoobError, match='Timeout na requisição'):
            await async_api_client._make_request(
                'GET', 'https://api.example.com/test', 'test_scope'
            )

    @pytest.mark.asyncio
    async def test_make_request_json_decode_error(self, async_api_client, mock_session):
        """Testa erro de decodificação JSON"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='invalid json')
        mock_response.json = AsyncMock(
            side_effect=json.JSONDecodeError('Invalid', '', 0)
        )

        async_api_client._session = mock_session
        mock_session.request.return_value.__aenter__.return_value = mock_response

        with pytest.raises(SicoobError, match='Resposta não é JSON válido'):
            await async_api_client._make_request(
                'GET', 'https://api.example.com/test', 'test_scope'
            )


class TestAsyncSicoob:
    """Testes para AsyncSicoob"""

    @pytest.mark.asyncio
    async def test_init_with_client_id(self):
        """Testa inicialização com client_id"""
        with patch.dict('os.environ', {'SICOOB_CLIENT_ID': 'test_client'}):
            with patch('sicoob.async_client.OAuth2Client') as mock_oauth:
                client = AsyncSicoob()
                assert client.client_id == 'test_client'
                mock_oauth.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_without_client_id(self):
        """Testa erro quando client_id não é fornecido"""
        with patch.dict('os.environ', {}, clear=True):
            with patch('dotenv.load_dotenv'):
                with pytest.raises(ValueError, match='client_id é obrigatório'):
                    AsyncSicoob()

    @pytest.mark.asyncio
    async def test_init_with_all_params(self):
        """Testa inicialização com todos os parâmetros"""
        with patch('sicoob.async_client.OAuth2Client') as mock_oauth:
            client = AsyncSicoob(
                client_id='test',
                certificado='cert.pem',
                chave_privada='key.pem',
                certificado_pfx='cert.pfx',
                senha_pfx='password',
                environment='sandbox',
                max_concurrent_requests=20,
                request_timeout=60,
            )

            assert client.client_id == 'test'
            assert client.certificado == 'cert.pem'
            assert client.chave_privada == 'key.pem'
            assert client.certificado_pfx == 'cert.pfx'
            assert client.senha_pfx == 'password'

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Testa context manager do AsyncSicoob"""
        with patch('sicoob.async_client.OAuth2Client'):
            async with AsyncSicoob(client_id='test') as client:
                assert client is not None

    def test_conta_corrente_property(self):
        """Testa propriedade conta_corrente"""
        with patch('sicoob.async_client.OAuth2Client'):
            client = AsyncSicoob(client_id='test')
            cc_api = client.conta_corrente
            assert isinstance(cc_api, AsyncContaCorrenteAPI)

    def test_cobranca_property(self):
        """Testa propriedade cobranca"""
        with patch('sicoob.async_client.OAuth2Client'):
            client = AsyncSicoob(client_id='test')
            cobranca_api = client.cobranca
            assert isinstance(cobranca_api, AsyncCobrancaAPI)


class TestAsyncContaCorrenteAPI:
    """Testes para AsyncContaCorrenteAPI"""

    @pytest_asyncio.fixture
    async def mock_api_client(self):
        """Mock do cliente API"""
        mock_client = Mock(spec=AsyncAPIClient)
        mock_client._get_base_url.return_value = 'https://api.sicoob.com.br'
        mock_client._make_request = AsyncMock()
        return mock_client

    @pytest_asyncio.fixture
    async def conta_corrente_api(self, mock_api_client):
        """Fixture para AsyncContaCorrenteAPI"""
        return AsyncContaCorrenteAPI(mock_api_client)

    @pytest.mark.asyncio
    async def test_get_extrato_with_conta(self, conta_corrente_api, mock_api_client):
        """Testa consulta de extrato com número da conta"""
        expected_response = {'extratos': []}
        mock_api_client._make_request.return_value = expected_response

        result = await conta_corrente_api.get_extrato(
            '2023-01-01', '2023-01-31', '12345'
        )

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/conta-corrente/extrato',
            scope='cco_extrato cco_consulta',
            params={
                'dataInicio': '2023-01-01',
                'dataFim': '2023-01-31',
                'numeroConta': '12345',
            },
        )

    @pytest.mark.asyncio
    async def test_get_extrato_without_conta(self, conta_corrente_api, mock_api_client):
        """Testa consulta de extrato sem número da conta"""
        expected_response = {'extratos': []}
        mock_api_client._make_request.return_value = expected_response

        result = await conta_corrente_api.get_extrato('2023-01-01', '2023-01-31')

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/conta-corrente/extrato',
            scope='cco_extrato cco_consulta',
            params={'dataInicio': '2023-01-01', 'dataFim': '2023-01-31'},
        )

    @pytest.mark.asyncio
    async def test_get_saldo_with_conta(self, conta_corrente_api, mock_api_client):
        """Testa consulta de saldo com número da conta"""
        expected_response = {'saldo': 1000.00}
        mock_api_client._make_request.return_value = expected_response

        result = await conta_corrente_api.get_saldo('12345')

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/conta-corrente/saldo',
            scope='cco_consulta',
            params={'numeroConta': '12345'},
        )

    @pytest.mark.asyncio
    async def test_get_saldo_without_conta(self, conta_corrente_api, mock_api_client):
        """Testa consulta de saldo sem número da conta"""
        expected_response = {'saldo': 1000.00}
        mock_api_client._make_request.return_value = expected_response

        result = await conta_corrente_api.get_saldo()

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/conta-corrente/saldo',
            scope='cco_consulta',
            params={},
        )


class TestAsyncCobrancaAPI:
    """Testes para AsyncCobrancaAPI"""

    @pytest_asyncio.fixture
    async def mock_api_client(self):
        """Mock do cliente API"""
        mock_client = Mock(spec=AsyncAPIClient)
        mock_client._get_base_url.return_value = 'https://api.sicoob.com.br'
        mock_client._make_request = AsyncMock()
        return mock_client

    @pytest_asyncio.fixture
    async def cobranca_api(self, mock_api_client):
        """Fixture para AsyncCobrancaAPI"""
        return AsyncCobrancaAPI(mock_api_client)

    @pytest.mark.asyncio
    async def test_criar_cobranca_pix(self, cobranca_api, mock_api_client):
        """Testa criação de cobrança PIX"""
        txid = 'txid123'
        dados = {'valor': {'original': '100.00'}}
        expected_response = {'txid': txid, 'status': 'ATIVA'}

        mock_api_client._make_request.return_value = expected_response

        result = await cobranca_api.criar_cobranca_pix(txid, dados)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'PUT',
            f'https://api.sicoob.com.br/pix/cob/{txid}',
            scope='cob.write',
            json=dados,
        )

    @pytest.mark.asyncio
    async def test_consultar_cobranca_pix(self, cobranca_api, mock_api_client):
        """Testa consulta de cobrança PIX"""
        txid = 'txid123'
        expected_response = {'txid': txid, 'status': 'ATIVA'}

        mock_api_client._make_request.return_value = expected_response

        result = await cobranca_api.consultar_cobranca_pix(txid)

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET', f'https://api.sicoob.com.br/pix/cob/{txid}', scope='cob.read'
        )

    @pytest.mark.asyncio
    async def test_listar_cobrancas_pix(self, cobranca_api, mock_api_client):
        """Testa listagem de cobranças PIX"""
        inicio = '2023-01-01T00:00:00Z'
        fim = '2023-01-31T23:59:59Z'
        expected_response = {'cobs': []}

        mock_api_client._make_request.return_value = expected_response

        result = await cobranca_api.listar_cobrancas_pix(inicio, fim, status='ATIVA')

        assert result == expected_response
        mock_api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/pix/cob',
            scope='cob.read',
            params={'inicio': inicio, 'fim': fim, 'status': 'ATIVA'},
        )


class TestUtilityFunctions:
    """Testes para funções utilitárias"""

    @pytest.mark.asyncio
    async def test_gather_with_concurrency(self):
        """Testa execução com limite de concorrência"""

        async def mock_task(value):
            await asyncio.sleep(0.01)
            return value * 2

        tasks = [mock_task(i) for i in range(5)]
        results = await gather_with_concurrency(tasks, max_concurrency=2)

        assert results == [0, 2, 4, 6, 8]

    @pytest.mark.asyncio
    async def test_async_batch_processor(self):
        """Testa processador de lotes assíncrono"""

        async def process_item(item):
            return item * 2

        items = [1, 2, 3, 4, 5, 6]
        async with async_batch_processor(
            items, process_item, batch_size=2, max_concurrency=2
        ) as results:
            assert results == [2, 4, 6, 8, 10, 12]
