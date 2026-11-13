"""Testes para o sistema de autenticação OAuth2"""

import time
from dataclasses import replace
from unittest.mock import Mock, patch

import pytest
import requests

from sicoob.auth import OAuth2Client
from sicoob.config import SicoobConfig
from sicoob.exceptions import AutenticacaoError

SEM_CERTIFICADO = replace(
    SicoobConfig.config_for('production'), require_certificate=False
)


class TestOAuth2Client:
    """Testes para OAuth2Client"""

    def setup_method(self):
        """Setup para cada teste"""
        # Reset configuração para estado padrão
        SicoobConfig.reset_to_defaults()

    @patch('requests.Session.post')
    def test_get_access_token_default_scope(self, mock_post):
        """Testa uso de escopo padrão quando não especificado"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'default_token',
            'expires_in': 3600,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = OAuth2Client(client_id='test_id', config=SEM_CERTIFICADO)

        token = client.get_access_token()  # Sem escopo especificado

        # Verifica se usou escopo padrão
        call_args = mock_post.call_args
        assert call_args[1]['data']['scope'] == 'cco_extrato cco_consulta'

    @patch('requests.Session.post')
    def test_get_access_token_request_error(self, mock_post):
        """Testa tratamento de erro na requisição de token"""
        mock_post.side_effect = requests.exceptions.RequestException('Erro de conexão')

        client = OAuth2Client(client_id='test_id', config=SEM_CERTIFICADO)

        with pytest.raises(requests.exceptions.RequestException):
            client.get_access_token('test_scope')

    @patch('requests.Session.post')
    def test_get_access_token_http_error(self, mock_post):
        """Testa tratamento de erro HTTP genérico (não 401) na requisição de token"""
        mock_response = Mock()
        mock_response.status_code = 500
        error = requests.exceptions.HTTPError('500 Internal Server Error')
        error.response = mock_response
        mock_response.raise_for_status.side_effect = error
        mock_post.return_value = mock_response

        client = OAuth2Client(client_id='test_id', config=SEM_CERTIFICADO)

        with pytest.raises(requests.exceptions.HTTPError):
            client.get_access_token('test_scope')

    @patch('requests.Session.post')
    def test_get_access_token_401_raises_autenticacao_error(self, mock_post):
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

        client = OAuth2Client(client_id='test_id', config=SEM_CERTIFICADO)

        with pytest.raises(AutenticacaoError) as exc_info:
            client.get_access_token('test_scope')

        assert exc_info.value.code == 401
        assert 'credenciais inválidas' in exc_info.value.message
        assert exc_info.value.response_text == '{"error": "unauthorized"}'

    def test_is_token_expired(self):
        """Testa verificação de expiração de token"""
        client = OAuth2Client(client_id='test_id', config=SEM_CERTIFICADO)

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

    def test_environment_configuration(self):
        """Testa configuração de ambiente"""
        client = OAuth2Client(client_id='test_id', config=SEM_CERTIFICADO)

        assert client.client_id == 'test_id'

    @patch('requests.Session.post')
    def test_multiple_scopes(self, mock_post):
        """Testa gerenciamento de múltiplos escopos"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'scope_token',
            'expires_in': 3600,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = OAuth2Client(client_id='test_id', config=SEM_CERTIFICADO)

        # Solicita tokens para diferentes escopos
        token1 = client.get_access_token('scope1')
        token2 = client.get_access_token('scope2')

        # Verifica se foram armazenados separadamente
        assert 'scope1' in client.token_cache
        assert 'scope2' in client.token_cache
        assert len(client.token_cache) == 2

        # Verifica se foram feitas duas requisições
        assert mock_post.call_count == 2


def test_sem_config_usa_producao_mesmo_com_global_em_sandbox():
    """OAuth2Client sem config não herda o ambiente global alterado"""
    from sicoob.config import Environment

    SicoobConfig.set_environment(Environment.SANDBOX)
    try:
        with pytest.raises(ValueError, match='certificado'):
            OAuth2Client(client_id='id')  # produção exige certificado
    finally:
        SicoobConfig.set_environment(Environment.PRODUCTION)


def test_client_id_vazio_e_erro():
    with pytest.raises(ValueError, match='client_id'):
        OAuth2Client(client_id='', config=SEM_CERTIFICADO)
