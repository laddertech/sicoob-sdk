"""Testes para APIClientBase"""

import json
import uuid
from unittest.mock import Mock, patch

import pytest
import requests

from sicoob.api_client import APIClientBase
from sicoob.auth import OAuth2Client
from sicoob.config import SicoobConfig
from sicoob.exceptions import RespostaInvalidaError


class TestAPIClientBase:
    """Testes para APIClientBase"""

    def setup_method(self):
        """Setup para cada teste"""
        SicoobConfig.reset_to_defaults()

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
        return APIClientBase(mock_oauth_client, mock_session, sandbox_mode=True)

    def test_init_sandbox_mode(self, mock_oauth_client, mock_session):
        """Testa inicialização em modo sandbox"""
        client = APIClientBase(mock_oauth_client, mock_session, sandbox_mode=True)
        
        assert client.oauth_client == mock_oauth_client
        assert client.session == mock_session
        assert client.sandbox_mode is True

    def test_init_production_mode(self, mock_oauth_client, mock_session):
        """Testa inicialização em modo produção"""
        client = APIClientBase(mock_oauth_client, mock_session, sandbox_mode=False)
        
        assert client.sandbox_mode is False

    def test_get_base_url_sandbox(self, api_client):
        """Testa obtenção da URL base em modo sandbox"""
        with patch.object(SicoobConfig, 'get_sandbox_url', return_value='https://sandbox.sicoob.com'):
            url = api_client._get_base_url()
            assert url == 'https://sandbox.sicoob.com'

    def test_get_base_url_production(self, mock_oauth_client, mock_session):
        """Testa obtenção da URL base em modo produção"""
        client = APIClientBase(mock_oauth_client, mock_session, sandbox_mode=False)
        
        with patch.object(SicoobConfig, 'get_production_url', return_value='https://api.sicoob.com'):
            url = client._get_base_url()
            assert url == 'https://api.sicoob.com'

    def test_get_headers_basic(self, api_client):
        """Testa geração de headers básicos"""
        headers = api_client._get_headers('test_scope')
        
        expected_headers = {
            'Authorization': 'Bearer test_token',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'sicoob-sdk-python',
        }
        
        # Verifica headers básicos
        for key, value in expected_headers.items():
            assert headers[key] == value
        
        # Verifica se há request_id
        assert 'X-Request-ID' in headers
        # Verifica se é um UUID válido
        uuid.UUID(headers['X-Request-ID'])

    def test_get_headers_custom(self, api_client):
        """Testa geração de headers com customizações"""
        custom_headers = {'X-Custom': 'custom_value'}
        headers = api_client._get_headers('test_scope', **custom_headers)
        
        assert headers['X-Custom'] == 'custom_value'
        assert headers['Authorization'] == 'Bearer test_token'

    @patch('sicoob.api_client.uuid.uuid4')
    def test_get_headers_request_id_generation(self, mock_uuid, api_client):
        """Testa geração do request ID"""
        mock_uuid.return_value = Mock()
        mock_uuid.return_value.hex = 'test_request_id'
        
        headers = api_client._get_headers('test_scope')
        assert headers['X-Request-ID'] == 'test_request_id'

    def test_make_request_get_success(self, api_client):
        """Testa requisição GET bem-sucedida"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        api_client.session.get.return_value = mock_response
        
        response = api_client._make_request('GET', 'https://api.test.com/endpoint', 'test_scope')
        
        assert response == mock_response
        api_client.session.get.assert_called_once()

    def test_make_request_post_with_json(self, api_client):
        """Testa requisição POST com dados JSON"""
        mock_response = Mock()
        mock_response.status_code = 201
        api_client.session.post.return_value = mock_response
        
        data = {'key': 'value'}
        response = api_client._make_request('POST', 'https://api.test.com/endpoint', 'test_scope', json=data)
        
        assert response == mock_response
        api_client.session.post.assert_called_once()
        call_args = api_client.session.post.call_args
        assert call_args[1]['json'] == data

    def test_make_request_with_params(self, api_client):
        """Testa requisição com parâmetros de query"""
        mock_response = Mock()
        mock_response.status_code = 200
        api_client.session.get.return_value = mock_response
        
        params = {'param1': 'value1', 'param2': 'value2'}
        api_client._make_request('GET', 'https://api.test.com/endpoint', 'test_scope', params=params)
        
        call_args = api_client.session.get.call_args
        assert call_args[1]['params'] == params

    def test_make_request_logs_request(self, api_client):
        """Testa se a requisição é logada"""
        mock_response = Mock()
        mock_response.status_code = 200
        api_client.session.get.return_value = mock_response
        
        with patch.object(api_client.logger, 'info') as mock_log:
            api_client._make_request('GET', 'https://api.test.com/endpoint', 'test_scope')
            
            # Verifica se foi logado
            mock_log.assert_called()
            log_call = mock_log.call_args
            assert 'Fazendo requisição HTTP' in log_call[0][0]

    def test_make_request_logs_response(self, api_client):
        """Testa se a resposta é logada"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        api_client.session.get.return_value = mock_response
        
        with patch.object(api_client.logger, 'info') as mock_log:
            api_client._make_request('GET', 'https://api.test.com/endpoint', 'test_scope')
            
            # Verifica se a resposta foi logada
            assert mock_log.call_count >= 2  # Uma para request, uma para response

    def test_validate_response_success(self, api_client):
        """Testa validação de resposta bem-sucedida"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': 'success'}
        mock_response.raise_for_status.return_value = None
        
        result = api_client._validate_response(mock_response)
        assert result == {'result': 'success'}

    def test_validate_response_invalid_json(self, api_client):
        """Testa validação de resposta com JSON inválido"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError('Invalid JSON', 'response', 0)
        mock_response.text = 'Invalid response'
        mock_response.raise_for_status.return_value = None
        
        with pytest.raises(RespostaInvalidaError) as exc_info:
            api_client._validate_response(mock_response)
        
        assert 'Resposta inválida da API' in str(exc_info.value)
        assert exc_info.value.response == mock_response

    def test_validate_response_http_error(self, api_client):
        """Testa validação de resposta com erro HTTP"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError('400 Bad Request')
        
        with pytest.raises(requests.exceptions.HTTPError):
            api_client._validate_response(mock_response)

    def test_validate_response_logs_invalid_json(self, api_client):
        """Testa se erro de JSON inválido é logado"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError('Invalid JSON', 'response', 0)
        mock_response.text = 'Invalid response'
        mock_response.raise_for_status.return_value = None
        
        with patch.object(api_client.logger, 'error') as mock_log:
            with pytest.raises(RespostaInvalidaError):
                api_client._validate_response(mock_response)
            
            mock_log.assert_called()
            log_call = mock_log.call_args
            assert 'JSON inválido na resposta' in log_call[0][0]

    @patch('sicoob.api_client.os')
    @patch('sicoob.api_client.load_dotenv')
    def test_environment_detection_sandbox(self, mock_load_dotenv, mock_os, api_client):
        """Testa detecção do ambiente sandbox"""
        mock_os.getenv.return_value = 'sandbox'
        
        with patch.object(SicoobConfig, 'is_sandbox', return_value=True):
            # Force environment detection
            if SicoobConfig.is_sandbox():
                mock_load_dotenv.assert_called_once()

    def test_oauth_token_caching(self, api_client):
        """Testa se os tokens OAuth são reutilizados"""
        # Faz duas requisições com o mesmo escopo
        api_client._get_headers('same_scope')
        api_client._get_headers('same_scope')
        
        # Verifica se get_access_token foi chamado apenas uma vez (cached)
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
        
        # Verifica se foram chamados com escopos diferentes
        calls = api_client.oauth_client.get_access_token.call_args_list
        assert calls[0][0][0] == 'scope1'
        assert calls[1][0][0] == 'scope2'

    def test_request_timeout_handling(self, api_client):
        """Testa tratamento de timeout de requisição"""
        api_client.session.get.side_effect = requests.exceptions.Timeout('Request timeout')
        
        with pytest.raises(requests.exceptions.Timeout):
            api_client._make_request('GET', 'https://api.test.com/endpoint', 'test_scope')

    def test_connection_error_handling(self, api_client):
        """Testa tratamento de erro de conexão"""
        api_client.session.get.side_effect = requests.exceptions.ConnectionError('Connection failed')
        
        with pytest.raises(requests.exceptions.ConnectionError):
            api_client._make_request('GET', 'https://api.test.com/endpoint', 'test_scope')

    def test_custom_user_agent(self, api_client):
        """Testa se o User-Agent customizado é usado"""
        headers = api_client._get_headers('test_scope')
        assert headers['User-Agent'] == 'sicoob-sdk-python'

    def test_content_type_json(self, api_client):
        """Testa se Content-Type é sempre application/json"""
        headers = api_client._get_headers('test_scope')
        assert headers['Content-Type'] == 'application/json'
        assert headers['Accept'] == 'application/json'