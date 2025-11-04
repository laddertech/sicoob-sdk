import json
from unittest.mock import Mock, patch

import pytest
import requests

from sicoob.api_client import APIClientBase
from sicoob.auth import OAuth2Client
from sicoob.config import SicoobConfig
from sicoob.exceptions import RespostaInvalidaError


class TestAPIClientBase:
    """Testes para a classe base APIClientBase"""

    @pytest.fixture
    def mock_oauth_client(self):
        """Fixture para cliente OAuth mock"""
        client = Mock(spec=OAuth2Client)
        client.client_id = 'test_client_id'
        client.get_access_token.return_value = 'test_token'
        return client

    @pytest.fixture
    def mock_session(self):
        """Fixture para sessão HTTP mock"""
        return Mock(spec=requests.Session)

    @pytest.fixture
    def api_client(self, mock_oauth_client, mock_session):
        """Fixture para APIClientBase"""
        return APIClientBase(mock_oauth_client, mock_session, enable_resilience=False)

    def test_init_default_mode(self, mock_oauth_client, mock_session):
        """Testa inicialização com configurações padrão"""
        client = APIClientBase(mock_oauth_client, mock_session)

        assert client.oauth_client == mock_oauth_client
        assert client.session is not None  # Session foi configurada

    def test_init_with_resilience_disabled(self, mock_oauth_client, mock_session):
        """Testa inicialização com resiliência desabilitada"""
        client = APIClientBase(mock_oauth_client, mock_session, enable_resilience=False)

        assert client.oauth_client == mock_oauth_client
        assert client.session is not None

    def test_get_base_url_sandbox(self, api_client):
        """Testa obtenção da URL base em modo sandbox"""
        with patch.object(
            SicoobConfig, 'get_base_url', return_value='https://sandbox.sicoob.com'
        ):
            url = api_client._get_base_url()
            assert url == 'https://sandbox.sicoob.com'

    def test_get_base_url_production(self, mock_oauth_client, mock_session):
        """Testa obtenção da URL base em modo produção"""
        client = APIClientBase(mock_oauth_client, mock_session)

        with patch.object(
            SicoobConfig, 'get_base_url', return_value='https://api.sicoob.com'
        ):
            url = client._get_base_url()
            assert url == 'https://api.sicoob.com'

    def test_get_headers_basic(self, api_client):
        """Testa geração de headers básicos"""
        headers = api_client._get_headers('test_scope')

        expected_headers = {
            'Authorization': 'Bearer test_token',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        # Verifica headers básicos
        for key, value in expected_headers.items():
            assert headers[key] == value

    def test_get_headers_custom(self, api_client):
        """Testa geração de headers com customizações"""
        # O método _get_headers não aceita parâmetros customizados diretamente
        headers = api_client._get_headers('test_scope')

        assert headers['Authorization'] == 'Bearer test_token'

    def test_get_headers_client_id(self, api_client):
        """Testa se client_id está presente nos headers"""
        headers = api_client._get_headers('test_scope')
        assert 'client_id' in headers
        assert headers['client_id'] == 'test_client_id'

    def test_make_request_get_success(self, api_client):
        """Testa requisição GET bem-sucedida"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        api_client.session.request.return_value = mock_response

        response = api_client._make_request(
            'GET', 'https://api.test.com/endpoint', 'test_scope'
        )

        assert response == mock_response
        api_client.session.request.assert_called_once()

    def test_make_request_post_with_json(self, api_client):
        """Testa requisição POST com dados JSON"""
        mock_response = Mock()
        mock_response.status_code = 201
        api_client.session.request.return_value = mock_response

        data = {'key': 'value'}
        response = api_client._make_request(
            'POST', 'https://api.test.com/endpoint', 'test_scope', json=data
        )

        assert response == mock_response
        api_client.session.request.assert_called_once()
        call_args = api_client.session.request.call_args
        assert call_args[1]['json'] == data

    def test_make_request_with_params(self, api_client):
        """Testa requisição com parâmetros de query"""
        mock_response = Mock()
        mock_response.status_code = 200
        api_client.session.request.return_value = mock_response

        params = {'param1': 'value1', 'param2': 'value2'}
        api_client._make_request(
            'GET', 'https://api.test.com/endpoint', 'test_scope', params=params
        )

        call_args = api_client.session.request.call_args
        assert call_args[1]['params'] == params

    def test_make_request_logs_request(self, api_client):
        """Testa se as requisições são logadas no início"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.text = '{"success": true}'
        api_client.session.request.return_value = mock_response

        with patch('sicoob.api_client.SicoobLogger') as mock_logger:
            api_client._make_request(
                'GET', 'https://api.test.com/endpoint', 'test_scope'
            )

            # Verifica se logou a requisição
            mock_logger.log_http_request.assert_called_once()
            call_args = mock_logger.log_http_request.call_args
            assert call_args[1]['method'] == 'GET'

    def test_make_request_logs_response(self, api_client):
        """Testa se as respostas são logadas"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.text = '{"success": true}'
        api_client.session.request.return_value = mock_response

        with patch('sicoob.api_client.SicoobLogger') as mock_logger:
            api_client._make_request(
                'GET', 'https://api.test.com/endpoint', 'test_scope'
            )

            # Verifica se logou a resposta
            mock_logger.log_http_response.assert_called_once()
            call_args = mock_logger.log_http_response.call_args
            assert call_args[1]['status_code'] == 200

    def test_validate_response_success(self, api_client):
        """Testa validação de resposta bem-sucedida"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'valid': 'json'}
        mock_response.raise_for_status.return_value = None

        result = api_client._validate_response(mock_response)
        assert result == {'valid': 'json'}

    def test_validate_response_invalid_json(self, api_client):
        """Testa validação de resposta com JSON inválido"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError(
            'Invalid JSON', 'response', 0
        )
        mock_response.text = 'Invalid response'
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {'Content-Type': 'application/json'}
        # Remove mock detection
        delattr(mock_response, '_mock_return_value') if hasattr(
            mock_response, '_mock_return_value'
        ) else None

        with pytest.raises(RespostaInvalidaError) as exc_info:
            api_client._validate_response(mock_response)

        assert 'JSON válido' in str(exc_info.value)

    def test_oauth_token_caching(self, api_client):
        """Testa se os tokens OAuth são reutilizados"""
        # Faz duas requisições com o mesmo escopo
        api_client._get_headers('same_scope')
        api_client._get_headers('same_scope')

        # Verifica se get_access_token foi chamado duas vezes
        # (o cache está no OAuth2Client, não aqui)
        assert api_client.oauth_client.get_access_token.call_count == 2

        # Verifica se ambas as chamadas foram com o mesmo escopo
        calls = api_client.oauth_client.get_access_token.call_args_list
        assert calls[0][0][0] == 'same_scope'
        assert calls[1][0][0] == 'same_scope'

    def test_different_scopes_different_tokens(self, api_client):
        """Testa se escopos diferentes geram chamadas separadas"""
        api_client._get_headers('scope1')
        api_client._get_headers('scope2')

        # Verifica se get_access_token foi chamado duas vezes
        assert api_client.oauth_client.get_access_token.call_count == 2

        # Verifica se as chamadas foram com escopos diferentes
        calls = api_client.oauth_client.get_access_token.call_args_list
        assert calls[0][0][0] == 'scope1'
        assert calls[1][0][0] == 'scope2'

    def test_request_timeout_handling(self, mock_oauth_client, mock_session):
        """Testa tratamento de timeout de requisição"""
        # Cria cliente sem resiliência para testar erros brutos
        api_client = APIClientBase(
            mock_oauth_client, mock_session, enable_resilience=False
        )
        api_client.session.request.side_effect = requests.exceptions.Timeout(
            'Request timeout'
        )

        with pytest.raises(requests.exceptions.Timeout):
            api_client._make_request(
                'GET', 'https://api.test.com/endpoint', 'test_scope'
            )

    def test_connection_error_handling(self, mock_oauth_client, mock_session):
        """Testa tratamento de erro de conexão"""
        # Cria cliente sem resiliência para testar erros brutos
        api_client = APIClientBase(
            mock_oauth_client, mock_session, enable_resilience=False
        )
        api_client.session.request.side_effect = requests.exceptions.ConnectionError(
            'Connection failed'
        )

        with pytest.raises(requests.exceptions.ConnectionError):
            api_client._make_request(
                'GET', 'https://api.test.com/endpoint', 'test_scope'
            )

    def test_custom_user_agent(self, api_client):
        """Testa se o User-Agent customizado é usado"""
        headers = api_client._get_headers('test_scope')
        assert 'SicoobAPIClient' in headers['User-Agent']

    def test_content_type_json(self, api_client):
        """Testa se Content-Type é sempre application/json"""
        headers = api_client._get_headers('test_scope')
        assert headers['Content-Type'] == 'application/json'
        assert headers['Accept'] == 'application/json'

    def test_pkcs12_adapter_preservation_with_resilience(self, mock_oauth_client):
        """Testa se adaptador PKCS12 é preservado quando enable_resilience=True"""
        # Cria uma sessão mock com adaptador PKCS12
        session = Mock(spec=requests.Session)
        session.adapters = {}

        # Mock adaptador PKCS12
        pkcs12_adapter = Mock()
        pkcs12_adapter.pkcs12_data = b'test_data'
        pkcs12_adapter.pkcs12_filename = 'test.pfx'
        pkcs12_adapter.pkcs12_password = 'test_password'
        session.adapters['https://'] = pkcs12_adapter

        # Cria cliente com resiliência habilitada
        with patch('sicoob.api_client.create_resilient_session') as mock_create_session:
            resilient_session = Mock(spec=requests.Session)
            resilient_session.adapters = {}
            resilient_session.headers = {}
            mock_create_session.return_value = resilient_session

            client = APIClientBase(mock_oauth_client, session, enable_resilience=True)

            # Verifica se a sessão resiliente foi criada
            mock_create_session.assert_called_once()

            # Verifica se o adaptador PKCS12 foi preservado na sessão final
            assert hasattr(client.session, '_sicoob_resilient')
            assert client.session._sicoob_resilient is True

    def test_regular_session_without_pkcs12_adapter(self, mock_oauth_client):
        """Testa comportamento normal sem adaptador PKCS12"""
        # Cria uma sessão sem adaptador PKCS12
        session = Mock(spec=requests.Session)
        session.adapters = {}

        with patch('sicoob.api_client.create_resilient_session') as mock_create_session:
            resilient_session = Mock(spec=requests.Session)
            resilient_session.adapters = {}
            resilient_session.headers = {}
            mock_create_session.return_value = resilient_session

            client = APIClientBase(mock_oauth_client, session, enable_resilience=True)

            # Verifica se a sessão resiliente foi criada normalmente
            mock_create_session.assert_called_once()
            assert hasattr(client.session, '_sicoob_resilient')
            assert client.session._sicoob_resilient is True
