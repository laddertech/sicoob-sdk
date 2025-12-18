"""Testes para o sistema de autenticação OAuth2"""

import time
from unittest.mock import Mock, patch

import pytest
import requests

from sicoob.auth import OAuth2Client
from sicoob.config import SicoobConfig
from sicoob.exceptions import AutenticacaoError


class TestOAuth2Client:
    """Testes para OAuth2Client"""

    def setup_method(self):
        """Setup para cada teste"""
        # Reset configuração para estado padrão
        SicoobConfig.reset_to_defaults()

    @patch('sicoob.auth.oauth.load_dotenv')
    @patch('requests.Session.post')
    def test_get_access_token_default_scope(self, mock_post, mock_load_dotenv):
        """Testa uso de escopo padrão quando não especificado"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'default_token',
            'expires_in': 3600,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with patch(
            'sicoob.config.SicoobConfig.requires_certificate', return_value=False
        ):
            client = OAuth2Client(client_id='test_id')

        token = client.get_access_token()  # Sem escopo especificado

        # Verifica se usou escopo padrão
        call_args = mock_post.call_args
        assert call_args[1]['data']['scope'] == 'cco_extrato cco_consulta'

    @patch('sicoob.auth.oauth.load_dotenv')
    @patch('requests.Session.post')
    def test_get_access_token_request_error(self, mock_post, mock_load_dotenv):
        """Testa tratamento de erro na requisição de token"""
        mock_post.side_effect = requests.exceptions.RequestException('Erro de conexão')

        with patch(
            'sicoob.config.SicoobConfig.requires_certificate', return_value=False
        ):
            client = OAuth2Client(client_id='test_id')

        with pytest.raises(requests.exceptions.RequestException):
            client.get_access_token('test_scope')

    @patch('sicoob.auth.oauth.load_dotenv')
    @patch('requests.Session.post')
    def test_get_access_token_http_error(self, mock_post, mock_load_dotenv):
        """Testa tratamento de erro HTTP genérico (não 401) na requisição de token"""
        mock_response = Mock()
        mock_response.status_code = 500
        error = requests.exceptions.HTTPError('500 Internal Server Error')
        error.response = mock_response
        mock_response.raise_for_status.side_effect = error
        mock_post.return_value = mock_response

        with patch(
            'sicoob.config.SicoobConfig.requires_certificate', return_value=False
        ):
            client = OAuth2Client(client_id='test_id')

        with pytest.raises(requests.exceptions.HTTPError):
            client.get_access_token('test_scope')

    @patch('sicoob.auth.oauth.load_dotenv')
    @patch('requests.Session.post')
    def test_get_access_token_401_raises_autenticacao_error(
        self, mock_post, mock_load_dotenv
    ):
        """Testa que erro 401 na requisição de token lança AutenticacaoError"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = '{"error": "unauthorized"}'
        mock_response.headers = {'Content-Type': 'application/json'}
        error = requests.exceptions.HTTPError(
            '401 Client Error: Unauthorized for url: https://auth.sicoob.com.br/...'
        )
        error.response = mock_response
        mock_response.raise_for_status.side_effect = error
        mock_post.return_value = mock_response

        with patch(
            'sicoob.config.SicoobConfig.requires_certificate', return_value=False
        ):
            client = OAuth2Client(client_id='test_id')

        with pytest.raises(AutenticacaoError) as exc_info:
            client.get_access_token('test_scope')

        assert exc_info.value.code == 401
        assert 'credenciais inválidas' in exc_info.value.message
        assert exc_info.value.response_text == '{"error": "unauthorized"}'

    @patch('sicoob.auth.oauth.load_dotenv')
    def test_is_token_expired(self, mock_load_dotenv):
        """Testa verificação de expiração de token"""
        with patch(
            'sicoob.config.SicoobConfig.requires_certificate', return_value=False
        ):
            client = OAuth2Client(client_id='test_id')

        # Token expirado
        client.token_cache['expired_scope'] = {
            'expires_at': time.time() - 100  # Expirado há 100 segundos
        }

        # Token válido
        client.token_cache['valid_scope'] = {
            'expires_at': time.time() + 3600  # Expira em 1 hora
        }

        assert client._is_token_expired('expired_scope') is True
        assert client._is_token_expired('valid_scope') is False
        assert client._is_token_expired('nonexistent_scope') is True

    @patch('sicoob.auth.oauth.load_dotenv')
    def test_environment_configuration(self, mock_load_dotenv):
        """Testa configuração de ambiente"""
        with patch(
            'sicoob.config.SicoobConfig.requires_certificate', return_value=False
        ):
            client = OAuth2Client(client_id='test_id')

        assert client.client_id == 'test_id'

    @patch('sicoob.auth.oauth.load_dotenv')
    @patch('requests.Session.post')
    def test_multiple_scopes(self, mock_post, mock_load_dotenv):
        """Testa gerenciamento de múltiplos escopos"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'scope_token',
            'expires_in': 3600,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with patch(
            'sicoob.config.SicoobConfig.requires_certificate', return_value=False
        ):
            client = OAuth2Client(client_id='test_id')

        # Solicita tokens para diferentes escopos
        token1 = client.get_access_token('scope1')
        token2 = client.get_access_token('scope2')

        # Verifica se foram armazenados separadamente
        assert 'scope1' in client.token_cache
        assert 'scope2' in client.token_cache
        assert len(client.token_cache) == 2

        # Verifica se foram feitas duas requisições
        assert mock_post.call_count == 2
