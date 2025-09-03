"""Testes para o sistema de autenticação OAuth2"""

import os
import time
from unittest.mock import Mock, patch, mock_open

import pytest
import requests

from sicoob.auth import OAuth2Client
from sicoob.config import SicoobConfig


class TestOAuth2Client:
    """Testes para OAuth2Client"""

    def setup_method(self):
        """Setup para cada teste"""
        # Reset configuração para estado padrão
        SicoobConfig.reset_to_defaults()

    @patch.dict(os.environ, {
        'SICOOB_CLIENT_ID': 'test_client_id',
        'SICOOB_CERTIFICADO': '/path/to/cert.pem',
        'SICOOB_CHAVE_PRIVADA': '/path/to/key.pem'
    })
    @patch('sicoob.auth.oauth.load_dotenv')
    def test_init_with_env_vars(self, mock_load_dotenv):
        """Testa inicialização usando variáveis de ambiente"""
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=False):
            client = OAuth2Client()
            
        assert client.client_id == 'test_client_id'
        assert client.certificado == '/path/to/cert.pem'
        assert client.chave_privada == '/path/to/key.pem'
        mock_load_dotenv.assert_called_once()

    @patch('sicoob.auth.oauth.load_dotenv')
    def test_init_with_params(self, mock_load_dotenv):
        """Testa inicialização com parâmetros diretos"""
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=False):
            client = OAuth2Client(
                client_id='param_client_id',
                certificado='/param/cert.pem',
                chave_privada='/param/key.pem'
            )
            
        assert client.client_id == 'param_client_id'
        assert client.certificado == '/param/cert.pem'
        assert client.chave_privada == '/param/key.pem'

    @patch('sicoob.auth.oauth.load_dotenv')
    @patch('sicoob.auth.oauth.requests_pkcs12.Pkcs12Adapter')
    def test_init_with_pfx_string(self, mock_adapter, mock_load_dotenv):
        """Testa inicialização com certificado PFX como string"""
        mock_adapter_instance = Mock()
        mock_adapter.return_value = mock_adapter_instance
        
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=True):
            client = OAuth2Client(
                client_id='test_id',
                certificado_pfx='/path/to/cert.pfx',
                senha_pfx='password123'
            )
            
        # Verifica se o adapter foi criado corretamente
        mock_adapter.assert_called_once_with(
            pkcs12_data=None,
            pkcs12_filename='/path/to/cert.pfx',
            pkcs12_password='password123'
        )
        client.session.mount.assert_called_with('https://', mock_adapter_instance)

    @patch('sicoob.auth.oauth.load_dotenv')
    @patch('sicoob.auth.oauth.requests_pkcs12.Pkcs12Adapter')
    def test_init_with_pfx_bytes(self, mock_adapter, mock_load_dotenv):
        """Testa inicialização com certificado PFX como bytes"""
        mock_adapter_instance = Mock()
        mock_adapter.return_value = mock_adapter_instance
        pfx_data = b'fake_pfx_data'
        
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=True):
            client = OAuth2Client(
                client_id='test_id',
                certificado_pfx=pfx_data,
                senha_pfx='password123'
            )
            
        # Verifica se o adapter foi criado corretamente
        mock_adapter.assert_called_once_with(
            pkcs12_data=pfx_data,
            pkcs12_filename=None,
            pkcs12_password='password123'
        )

    @patch('sicoob.auth.oauth.load_dotenv')
    def test_init_with_pem_certs(self, mock_load_dotenv):
        """Testa inicialização com certificados PEM"""
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=True):
            client = OAuth2Client(
                client_id='test_id',
                certificado='/path/to/cert.pem',
                chave_privada='/path/to/key.pem'
            )
            
        assert client.session.cert == ('/path/to/cert.pem', '/path/to/key.pem')

    @patch('sicoob.auth.oauth.load_dotenv')
    def test_init_missing_certificates(self, mock_load_dotenv):
        """Testa erro quando certificados são necessários mas não fornecidos"""
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=True):
            with pytest.raises(ValueError, match='É necessário fornecer certificado'):
                OAuth2Client(client_id='test_id')

    @patch('sicoob.auth.oauth.load_dotenv')
    def test_get_access_token_from_cache(self, mock_load_dotenv):
        """Testa obtenção de token do cache quando ainda válido"""
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=False):
            client = OAuth2Client(client_id='test_id')
            
        # Simula token em cache
        client.token_cache['test_scope'] = {
            'access_token': 'cached_token',
            'expires_at': time.time() + 3600  # Expira em 1 hora
        }
        
        token = client.get_access_token('test_scope')
        assert token == 'cached_token'

    @patch('sicoob.auth.oauth.load_dotenv')
    @patch('requests.Session.post')
    def test_get_access_token_new_request(self, mock_post, mock_load_dotenv):
        """Testa solicitação de novo token quando não há cache"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=False):
            client = OAuth2Client(client_id='test_id')
            
        token = client.get_access_token('new_scope')
        
        assert token == 'new_token'
        assert 'new_scope' in client.token_cache
        assert client.token_cache['new_scope']['access_token'] == 'new_token'
        
        # Verifica se a requisição foi feita corretamente
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['data']['grant_type'] == 'client_credentials'
        assert call_args[1]['data']['scope'] == 'new_scope'

    @patch('sicoob.auth.oauth.load_dotenv')
    @patch('requests.Session.post')
    def test_get_access_token_default_scope(self, mock_post, mock_load_dotenv):
        """Testa uso de escopo padrão quando não especificado"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'default_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=False):
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
        
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=False):
            client = OAuth2Client(client_id='test_id')
            
        with pytest.raises(requests.exceptions.RequestException):
            client.get_access_token('test_scope')

    @patch('sicoob.auth.oauth.load_dotenv')
    @patch('requests.Session.post')
    def test_get_access_token_http_error(self, mock_post, mock_load_dotenv):
        """Testa tratamento de erro HTTP na requisição de token"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError('401 Unauthorized')
        mock_post.return_value = mock_response
        
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=False):
            client = OAuth2Client(client_id='test_id')
            
        with pytest.raises(requests.exceptions.HTTPError):
            client.get_access_token('test_scope')

    @patch('sicoob.auth.oauth.load_dotenv')
    def test_is_token_expired(self, mock_load_dotenv):
        """Testa verificação de expiração de token"""
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=False):
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
    def test_clear_cache(self, mock_load_dotenv):
        """Testa limpeza do cache de tokens"""
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=False):
            client = OAuth2Client(client_id='test_id')
            
        # Adiciona tokens ao cache
        client.token_cache['scope1'] = {'access_token': 'token1'}
        client.token_cache['scope2'] = {'access_token': 'token2'}
        
        client.clear_cache()
        
        assert len(client.token_cache) == 0

    @patch('sicoob.auth.oauth.load_dotenv')
    def test_sandbox_mode(self, mock_load_dotenv):
        """Testa modo sandbox"""
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=False):
            client = OAuth2Client(client_id='test_id', sandbox_mode=True)
            
        assert client.sandbox_mode is True

    @patch('sicoob.auth.oauth.load_dotenv')
    @patch('requests.Session.post')
    def test_token_expiry_calculation(self, mock_post, mock_load_dotenv):
        """Testa cálculo correto da expiração do token"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 1800  # 30 minutos
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=False):
            client = OAuth2Client(client_id='test_id')
            
        start_time = time.time()
        client.get_access_token('test_scope')
        
        # Verifica se o tempo de expiração foi calculado corretamente
        expires_at = client.token_cache['test_scope']['expires_at']
        expected_expires = start_time + 1800 - 60  # Margem de segurança de 60 segundos
        
        # Permite margem de erro de alguns segundos
        assert abs(expires_at - expected_expires) < 5

    @patch('sicoob.auth.oauth.load_dotenv')
    @patch('requests.Session.post')
    def test_multiple_scopes(self, mock_post, mock_load_dotenv):
        """Testa gerenciamento de múltiplos escopos"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'scope_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=False):
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