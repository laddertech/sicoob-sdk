"""Sistema de configuração flexível por ambiente para o Sicoob SDK"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from dotenv import load_dotenv


class Environment(Enum):
    """Enum para ambientes suportados"""

    DEVELOPMENT = 'development'
    TEST = 'test'
    STAGING = 'staging'
    PRODUCTION = 'production'
    SANDBOX = 'sandbox'


@dataclass
class EnvironmentConfig:
    """Configuração completa por ambiente"""

    # Identificação do ambiente
    environment: Environment = Environment.PRODUCTION

    # URLs dos serviços
    base_url: str = 'https://api.sicoob.com.br'
    auth_url: str = (
        'https://auth.sicoob.com.br/auth/realms/cooperado/protocol/openid-connect/token'
    )

    # Configurações de rede
    timeout: int = 30  # Timeout padrão
    connect_timeout: int = 10  # Timeout para conexão
    read_timeout: int = 30  # Timeout para leitura
    max_retries: int = 3
    retry_backoff_factor: float = 1.0

    # Timeouts específicos por operação
    pix_timeout: int = 45  # PIX pode ser mais lento
    boleto_timeout: int = 60  # Emissão de boleto pode demorar
    extrato_timeout: int = 120  # Consultas de extrato podem ser lentas

    # Configurações de logging por ambiente
    log_level: str = 'INFO'
    log_format: str = 'custom'
    log_requests: bool = False
    log_responses: bool = False

    # Configurações de certificado
    require_certificate: bool = True

    # Configurações específicas por ambiente
    debug_mode: bool = False
    verify_ssl: bool = True

    # Headers customizados por ambiente
    custom_headers: dict[str, str] = field(default_factory=dict)


class SicoobConfig:
    """Gerenciador de configuração do SDK Sicoob"""

    _instance: Optional['SicoobConfig'] = None
    _current_config: EnvironmentConfig

    # Configurações predefinidas por ambiente
    _DEFAULT_CONFIGS = {
        Environment.DEVELOPMENT: EnvironmentConfig(
            environment=Environment.DEVELOPMENT,
            base_url='https://sandbox.sicoob.com.br/sicoob/sandbox',
            timeout=60,
            log_level='DEBUG',
            log_format='custom',
            log_requests=True,
            log_responses=True,
            require_certificate=False,
            debug_mode=True,
            verify_ssl=True,
        ),
        Environment.TEST: EnvironmentConfig(
            environment=Environment.TEST,
            base_url='https://sandbox.sicoob.com.br/sicoob/sandbox',
            timeout=30,
            log_level='WARNING',
            log_format='simple',
            log_requests=False,
            log_responses=False,
            require_certificate=False,
            debug_mode=False,
            verify_ssl=True,
        ),
        Environment.STAGING: EnvironmentConfig(
            environment=Environment.STAGING,
            base_url='https://api.sicoob.com.br',
            timeout=30,
            log_level='INFO',
            log_format='json',
            log_requests=True,
            log_responses=True,
            require_certificate=True,
            debug_mode=False,
            verify_ssl=True,
        ),
        Environment.PRODUCTION: EnvironmentConfig(
            environment=Environment.PRODUCTION,
            base_url='https://api.sicoob.com.br',
            timeout=30,
            max_retries=5,
            log_level='INFO',
            log_format='json',
            log_requests=False,
            log_responses=False,
            require_certificate=True,
            debug_mode=False,
            verify_ssl=True,
        ),
        Environment.SANDBOX: EnvironmentConfig(
            environment=Environment.SANDBOX,
            base_url='https://sandbox.sicoob.com.br/sicoob/sandbox',
            timeout=45,
            log_level='DEBUG',
            log_format='custom',
            log_requests=True,
            log_responses=True,
            require_certificate=False,
            debug_mode=True,
            verify_ssl=True,
        ),
    }

    def __new__(cls) -> 'SicoobConfig':
        """Implementa padrão Singleton"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Inicializa a configuração"""
        if hasattr(self, '_initialized'):
            return

        load_dotenv()
        self._initialized = True

        # Detecta ambiente atual
        env_name = os.getenv('SICOOB_ENVIRONMENT', 'production').lower()

        # Mapeia nomes comuns para environments
        env_mapping = {
            'dev': Environment.DEVELOPMENT,
            'development': Environment.DEVELOPMENT,
            'test': Environment.TEST,
            'testing': Environment.TEST,
            'stage': Environment.STAGING,
            'staging': Environment.STAGING,
            'prod': Environment.PRODUCTION,
            'production': Environment.PRODUCTION,
            'sandbox': Environment.SANDBOX,
        }

        try:
            current_env = env_mapping[env_name]
        except KeyError:
            current_env = Environment.PRODUCTION

        # Carrega configuração padrão para o ambiente
        self._current_config = self._load_config_for_environment(current_env)

    def _load_config_for_environment(
        self, environment: Environment
    ) -> EnvironmentConfig:
        """Carrega configuração para um ambiente específico"""
        base_config = self._DEFAULT_CONFIGS[environment]

        # Sobrescreve com variáveis de ambiente se disponíveis
        overrides = {}

        if os.getenv('SICOOB_BASE_URL'):
            overrides['base_url'] = os.getenv('SICOOB_BASE_URL')

        if os.getenv('SICOOB_AUTH_URL'):
            overrides['auth_url'] = os.getenv('SICOOB_AUTH_URL')

        if os.getenv('SICOOB_TIMEOUT'):
            try:
                overrides['timeout'] = int(os.getenv('SICOOB_TIMEOUT'))
            except ValueError:
                pass

        if os.getenv('SICOOB_MAX_RETRIES'):
            try:
                overrides['max_retries'] = int(os.getenv('SICOOB_MAX_RETRIES'))
            except ValueError:
                pass

        if os.getenv('SICOOB_LOG_LEVEL'):
            overrides['log_level'] = os.getenv('SICOOB_LOG_LEVEL')

        if os.getenv('SICOOB_LOG_FORMAT'):
            overrides['log_format'] = os.getenv('SICOOB_LOG_FORMAT')

        if os.getenv('SICOOB_LOG_REQUESTS'):
            overrides['log_requests'] = (
                os.getenv('SICOOB_LOG_REQUESTS').lower() == 'true'
            )

        if os.getenv('SICOOB_LOG_RESPONSES'):
            overrides['log_responses'] = (
                os.getenv('SICOOB_LOG_RESPONSES').lower() == 'true'
            )

        if os.getenv('SICOOB_DEBUG_MODE'):
            overrides['debug_mode'] = os.getenv('SICOOB_DEBUG_MODE').lower() == 'true'

        if os.getenv('SICOOB_VERIFY_SSL'):
            overrides['verify_ssl'] = os.getenv('SICOOB_VERIFY_SSL').lower() == 'true'

        # Cria nova instância com overrides
        if overrides:
            from dataclasses import replace

            return replace(base_config, **overrides)

        return base_config

    @classmethod
    def get_current_config(cls) -> EnvironmentConfig:
        """Retorna a configuração atual"""
        instance = cls()
        return instance._current_config

    @classmethod
    def set_environment(cls, environment: Environment) -> None:
        """Define o ambiente atual"""
        instance = cls()
        instance._current_config = instance._load_config_for_environment(environment)

    @classmethod
    def is_production(cls) -> bool:
        """Verifica se está em produção"""
        return cls.get_current_config().environment == Environment.PRODUCTION

    @classmethod
    def is_sandbox(cls) -> bool:
        """Verifica se está em modo sandbox"""
        config = cls.get_current_config()
        return config.environment in [
            Environment.DEVELOPMENT,
            Environment.TEST,
            Environment.SANDBOX,
        ]

    @classmethod
    def requires_certificate(cls) -> bool:
        """Verifica se o ambiente atual requer certificado"""
        return cls.get_current_config().require_certificate

    @classmethod
    def get_base_url(cls) -> str:
        """Retorna a URL base para o ambiente atual"""
        return cls.get_current_config().base_url

    @classmethod
    def get_auth_url(cls) -> str:
        """Retorna a URL de autenticação para o ambiente atual"""
        return cls.get_current_config().auth_url

    @classmethod
    def get_timeout(cls) -> int:
        """Retorna o timeout para requisições"""
        return cls.get_current_config().timeout

    @classmethod
    def get_max_retries(cls) -> int:
        """Retorna o número máximo de tentativas"""
        return cls.get_current_config().max_retries

    @classmethod
    def should_log_requests(cls) -> bool:
        """Verifica se deve logar requisições"""
        return cls.get_current_config().log_requests

    @classmethod
    def should_log_responses(cls) -> bool:
        """Verifica se deve logar respostas"""
        return cls.get_current_config().log_responses

    @classmethod
    def get_log_level(cls) -> str:
        """Retorna o nível de log"""
        return cls.get_current_config().log_level

    @classmethod
    def get_log_format(cls) -> str:
        """Retorna o formato de log"""
        return cls.get_current_config().log_format

    @classmethod
    def is_debug_mode(cls) -> bool:
        """Verifica se está em modo debug"""
        return cls.get_current_config().debug_mode

    @classmethod
    def should_verify_ssl(cls) -> bool:
        """Verifica se deve verificar SSL"""
        return cls.get_current_config().verify_ssl

    @classmethod
    def get_custom_headers(cls) -> dict[str, str]:
        """Retorna headers customizados"""
        return cls.get_current_config().custom_headers.copy()

    @classmethod
    def update_config(cls, **kwargs) -> None:
        """Atualiza configuração atual com valores fornecidos"""
        instance = cls()
        from dataclasses import replace

        instance._current_config = replace(instance._current_config, **kwargs)

    @classmethod
    def reset_to_defaults(cls) -> None:
        """Reseta para configuração padrão do ambiente"""
        instance = cls()
        current_env = instance._current_config.environment
        from dataclasses import replace

        instance._current_config = replace(instance._DEFAULT_CONFIGS[current_env])


# Instância global para fácil acesso
config = SicoobConfig()
