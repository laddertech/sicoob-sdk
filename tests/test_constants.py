"""Testes para o módulo constants.py"""

from unittest.mock import patch

from sicoob import constants
from sicoob.config import SicoobConfig


class TestConstants:
    """Testes para funções de constantes"""

    def test_get_auth_url_default(self):
        """Testa get_auth_url com configuração padrão"""
        with patch.object(
            SicoobConfig,
            'get_auth_url',
            return_value='https://auth.sicoob.com.br/token',
        ):
            result = constants.get_auth_url()
            assert result == 'https://auth.sicoob.com.br/token'
            SicoobConfig.get_auth_url.assert_called_once()

    def test_get_base_url_default(self):
        """Testa get_base_url com configuração padrão"""
        with patch.object(
            SicoobConfig, 'get_base_url', return_value='https://api.sicoob.com.br'
        ):
            result = constants.get_base_url()
            assert result == 'https://api.sicoob.com.br'
            SicoobConfig.get_base_url.assert_called_once()

    def test_get_auth_url_sandbox(self):
        """Testa get_auth_url em modo sandbox"""
        with patch.object(
            SicoobConfig,
            'get_auth_url',
            return_value='https://auth.sandbox.sicoob.com.br/token',
        ):
            result = constants.get_auth_url()
            assert result == 'https://auth.sandbox.sicoob.com.br/token'

    def test_get_base_url_sandbox(self):
        """Testa get_base_url em modo sandbox"""
        with patch.object(
            SicoobConfig, 'get_base_url', return_value='https://sandbox.sicoob.com.br'
        ):
            result = constants.get_base_url()
            assert result == 'https://sandbox.sicoob.com.br'

    def test_legacy_constants_exist(self):
        """Testa se constantes legadas ainda existem"""
        assert hasattr(constants, 'AUTH_URL')
        assert hasattr(constants, 'BASE_URL')
        assert hasattr(constants, 'SANDBOX_URL')

        assert (
            constants.AUTH_URL
            == 'https://auth.sicoob.com.br/auth/realms/cooperado/protocol/openid-connect/token'
        )
        assert constants.BASE_URL == 'https://api.sicoob.com.br'
        assert constants.SANDBOX_URL == 'https://sandbox.sicoob.com.br/sicoob/sandbox'

    def test_legacy_constants_are_strings(self):
        """Testa se constantes legadas são strings"""
        assert isinstance(constants.AUTH_URL, str)
        assert isinstance(constants.BASE_URL, str)
        assert isinstance(constants.SANDBOX_URL, str)

    def test_legacy_constants_not_empty(self):
        """Testa se constantes legadas não são vazias"""
        assert len(constants.AUTH_URL) > 0
        assert len(constants.BASE_URL) > 0
        assert len(constants.SANDBOX_URL) > 0

    def test_legacy_constants_are_urls(self):
        """Testa se constantes legadas são URLs válidas"""
        assert constants.AUTH_URL.startswith('https://')
        assert constants.BASE_URL.startswith('https://')
        assert constants.SANDBOX_URL.startswith('https://')

    def test_get_auth_url_function_exists(self):
        """Testa se função get_auth_url existe e é chamável"""
        assert hasattr(constants, 'get_auth_url')
        assert callable(constants.get_auth_url)

    def test_get_base_url_function_exists(self):
        """Testa se função get_base_url existe e é chamável"""
        assert hasattr(constants, 'get_base_url')
        assert callable(constants.get_base_url)
