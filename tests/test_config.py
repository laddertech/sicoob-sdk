"""Testes para o sistema de configuração por ambiente"""

import os
from unittest.mock import patch

from sicoob.config import Environment, EnvironmentConfig, SicoobConfig


def test_environment_enum():
    """Testa o enum Environment"""
    assert Environment.DEVELOPMENT.value == 'development'
    assert Environment.TEST.value == 'test'
    assert Environment.STAGING.value == 'staging'
    assert Environment.PRODUCTION.value == 'production'
    assert Environment.SANDBOX.value == 'sandbox'


def test_environment_config_defaults():
    """Testa valores padrão do EnvironmentConfig"""
    config = EnvironmentConfig()

    assert config.environment == Environment.PRODUCTION
    assert config.base_url == 'https://api.sicoob.com.br'
    assert config.timeout == 30
    assert config.log_level == 'INFO'
    assert config.require_certificate is True
    assert config.debug_mode is False


def test_sicoob_config_singleton():
    """Testa padrão Singleton do SicoobConfig"""
    config1 = SicoobConfig()
    config2 = SicoobConfig()
    assert config1 is config2


@patch.dict(os.environ, {'SICOOB_ENVIRONMENT': 'development'})
def test_sicoob_config_development_environment():
    """Testa configuração para ambiente development"""
    # Força nova instância
    SicoobConfig._instance = None

    config = SicoobConfig()
    current_config = config.get_current_config()

    assert current_config.environment == Environment.DEVELOPMENT
    assert current_config.base_url == 'https://sandbox.sicoob.com.br/sicoob/sandbox'
    assert current_config.log_level == 'DEBUG'
    assert current_config.log_requests is True
    assert current_config.require_certificate is False
    assert current_config.debug_mode is True


@patch.dict(os.environ, {'SICOOB_ENVIRONMENT': 'test'})
def test_sicoob_config_test_environment():
    """Testa configuração para ambiente test"""
    # Força nova instância
    SicoobConfig._instance = None

    config = SicoobConfig()
    current_config = config.get_current_config()

    assert current_config.environment == Environment.TEST
    assert current_config.log_level == 'WARNING'
    assert current_config.log_format == 'simple'
    assert current_config.log_requests is False
    assert current_config.require_certificate is False


@patch.dict(os.environ, {'SICOOB_ENVIRONMENT': 'staging'})
def test_sicoob_config_staging_environment():
    """Testa configuração para ambiente staging"""
    # Força nova instância
    SicoobConfig._instance = None

    config = SicoobConfig()
    current_config = config.get_current_config()

    assert current_config.environment == Environment.STAGING
    assert current_config.base_url == 'https://api.sicoob.com.br'
    assert current_config.log_format == 'json'
    assert current_config.require_certificate is True


@patch.dict(os.environ, {'SICOOB_ENVIRONMENT': 'production'})
def test_sicoob_config_production_environment():
    """Testa configuração para ambiente production"""
    # Força nova instância
    SicoobConfig._instance = None

    config = SicoobConfig()
    current_config = config.get_current_config()

    assert current_config.environment == Environment.PRODUCTION
    assert current_config.base_url == 'https://api.sicoob.com.br'
    assert current_config.max_retries == 5
    assert current_config.log_requests is False
    assert current_config.require_certificate is True


@patch.dict(os.environ, {'SICOOB_ENVIRONMENT': 'sandbox'})
def test_sicoob_config_sandbox_environment():
    """Testa configuração para ambiente sandbox"""
    # Força nova instância
    SicoobConfig._instance = None

    config = SicoobConfig()
    current_config = config.get_current_config()

    assert current_config.environment == Environment.SANDBOX
    assert current_config.base_url == 'https://sandbox.sicoob.com.br/sicoob/sandbox'
    assert current_config.log_level == 'DEBUG'
    assert current_config.require_certificate is False
    assert current_config.debug_mode is True


def test_sicoob_config_invalid_environment():
    """Testa comportamento com ambiente inválido"""
    with patch.dict(os.environ, {'SICOOB_ENVIRONMENT': 'invalid'}):
        # Força nova instância
        SicoobConfig._instance = None

        config = SicoobConfig()
        current_config = config.get_current_config()

        # Deve usar production como padrão
        assert current_config.environment == Environment.PRODUCTION


@patch.dict(
    os.environ,
    {
        'SICOOB_ENVIRONMENT': 'development',
        'SICOOB_BASE_URL': 'https://custom.api.com',
        'SICOOB_TIMEOUT': '60',
        'SICOOB_LOG_LEVEL': 'ERROR',
        'SICOOB_DEBUG_MODE': 'true',
    },
)
def test_environment_variable_overrides():
    """Testa sobrescrição com variáveis de ambiente"""
    # Força nova instância
    SicoobConfig._instance = None

    config = SicoobConfig()
    current_config = config.get_current_config()

    assert current_config.base_url == 'https://custom.api.com'
    assert current_config.timeout == 60
    assert current_config.log_level == 'ERROR'
    assert current_config.debug_mode is True


def test_set_environment():
    """Testa mudança de ambiente programática"""
    # Força nova instância com production
    SicoobConfig._instance = None
    with patch.dict(os.environ, {'SICOOB_ENVIRONMENT': 'production'}):
        config = SicoobConfig()

    # Muda para development
    SicoobConfig.set_environment(Environment.DEVELOPMENT)
    current_config = SicoobConfig.get_current_config()

    assert current_config.environment == Environment.DEVELOPMENT
    assert current_config.log_level == 'DEBUG'
    assert current_config.require_certificate is False


def test_utility_methods():
    """Testa métodos utilitários da configuração"""
    # Força ambiente production
    SicoobConfig.set_environment(Environment.PRODUCTION)

    assert SicoobConfig.is_production() is True
    assert SicoobConfig.is_sandbox() is False
    assert SicoobConfig.requires_certificate() is True
    assert SicoobConfig.get_base_url() == 'https://api.sicoob.com.br'

    # Muda para sandbox
    SicoobConfig.set_environment(Environment.SANDBOX)

    assert SicoobConfig.is_production() is False
    assert SicoobConfig.is_sandbox() is True
    assert SicoobConfig.requires_certificate() is False


def test_config_update():
    """Testa atualização de configuração"""
    SicoobConfig.set_environment(Environment.DEVELOPMENT)

    original_timeout = SicoobConfig.get_timeout()

    # Atualiza configuração
    SicoobConfig.update_config(timeout=120, log_level='ERROR')

    assert SicoobConfig.get_timeout() == 120
    assert SicoobConfig.get_log_level() == 'ERROR'

    # Reseta para padrões
    SicoobConfig.reset_to_defaults()
    assert SicoobConfig.get_timeout() == original_timeout


def test_custom_headers():
    """Testa headers customizados"""
    config = SicoobConfig.get_current_config()

    # Por padrão não deve ter headers customizados
    assert SicoobConfig.get_custom_headers() == {}

    # Atualiza com headers customizados
    custom_headers = {'X-Custom-Header': 'test-value'}
    SicoobConfig.update_config(custom_headers=custom_headers)

    assert SicoobConfig.get_custom_headers() == custom_headers


def test_logging_configuration_methods():
    """Testa métodos específicos de configuração de logging"""
    SicoobConfig.set_environment(Environment.DEVELOPMENT)

    assert SicoobConfig.should_log_requests() is True
    assert SicoobConfig.should_log_responses() is True
    assert SicoobConfig.get_log_format() == 'custom'

    SicoobConfig.set_environment(Environment.PRODUCTION)

    assert SicoobConfig.should_log_requests() is False
    assert SicoobConfig.should_log_responses() is False
    assert SicoobConfig.get_log_format() == 'json'


def test_ssl_and_security_config():
    """Testa configurações de SSL e segurança"""
    SicoobConfig.set_environment(Environment.DEVELOPMENT)

    assert SicoobConfig.should_verify_ssl() is True
    assert SicoobConfig.is_debug_mode() is True

    SicoobConfig.set_environment(Environment.PRODUCTION)

    assert SicoobConfig.should_verify_ssl() is True
    assert SicoobConfig.is_debug_mode() is False


@patch.dict(os.environ, {'SICOOB_VERIFY_SSL': 'false', 'SICOOB_MAX_RETRIES': '10'})
def test_boolean_and_numeric_overrides():
    """Testa conversão correta de valores booleanos e numéricos"""
    # Força nova instância
    SicoobConfig._instance = None

    config = SicoobConfig()
    current_config = config.get_current_config()

    assert current_config.verify_ssl is False
    assert current_config.max_retries == 10


@patch.dict(os.environ, {'SICOOB_TIMEOUT': 'invalid'})
def test_invalid_numeric_override():
    """Testa comportamento com valor numérico inválido"""
    # Força nova instância
    SicoobConfig._instance = None

    config = SicoobConfig()
    current_config = config.get_current_config()

    # Deve manter valor padrão se conversão falhar
    assert current_config.timeout == 30  # Valor padrão
