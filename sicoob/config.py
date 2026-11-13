"""Sistema de configuração por ambiente para o Sicoob SDK

A configuração **não lê variáveis de ambiente**: cada cliente recebe o seu
``EnvironmentConfig`` (``SicoobConfig.config_for``), sem estado compartilhado
entre instâncias. Para montar um cliente a partir de variáveis de ambiente,
use explicitamente ``Sicoob.from_env()``.
"""

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Optional


class Environment(Enum):
    """Enum para ambientes suportados"""

    DEVELOPMENT = 'development'
    TEST = 'test'
    STAGING = 'staging'
    PRODUCTION = 'production'
    SANDBOX = 'sandbox'

    @classmethod
    def parse(cls, value: 'Environment | str') -> 'Environment':
        """Converte um apelido textual no ambiente correspondente.

        Raises:
            ValueError: ambiente desconhecido. Não há fallback para produção:
                um erro de digitação não pode mudar o destino das chamadas.
        """
        if isinstance(value, Environment):
            return value
        aliases = {
            'dev': cls.DEVELOPMENT,
            'development': cls.DEVELOPMENT,
            'test': cls.TEST,
            'testing': cls.TEST,
            'stage': cls.STAGING,
            'staging': cls.STAGING,
            'prod': cls.PRODUCTION,
            'production': cls.PRODUCTION,
            'sandbox': cls.SANDBOX,
        }
        try:
            return aliases[str(value).strip().lower()]
        except KeyError:
            raise ValueError(
                f'Ambiente desconhecido: {value!r}. Use um de: '
                + ', '.join(sorted(aliases))
            ) from None


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

    @property
    def is_sandbox(self) -> bool:
        """Ambientes que falam com o sandbox do Sicoob."""
        return self.environment in (
            Environment.DEVELOPMENT,
            Environment.TEST,
            Environment.SANDBOX,
        )


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
        """Inicializa a configuração global (padrão: produção)."""
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._current_config = self._load_config_for_environment(Environment.PRODUCTION)

    def _load_config_for_environment(
        self, environment: Environment
    ) -> EnvironmentConfig:
        """Cópia da configuração padrão do ambiente (sem ler o ambiente do SO)."""
        return self.config_for(environment)

    @classmethod
    def config_for(cls, environment: 'Environment | str') -> EnvironmentConfig:
        """Configuração nova e independente para um ambiente.

        Usada pelos clientes para terem configuração própria: alterá-la não
        afeta outras instâncias nem a configuração global.
        """
        base = cls._DEFAULT_CONFIGS[Environment.parse(environment)]
        return replace(base, custom_headers=dict(base.custom_headers))

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
        return cls.get_current_config().is_sandbox

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
    def enable_debug(cls) -> None:
        """Ativa modo debug com logs verbosos

        Configura o ambiente para modo debug:
        - Ativa debug_mode
        - Define log_level para DEBUG
        - Ativa log_requests e log_responses
        - Configura logging do Python para DEBUG

        Example:
            >>> from sicoob import SicoobConfig
            >>> SicoobConfig.enable_debug()
            >>> # Agora todos os logs de DEBUG serão exibidos
        """
        import logging

        instance = cls()
        config = instance._current_config

        # Ativa flags de debug
        config.debug_mode = True
        config.log_level = 'DEBUG'
        config.log_requests = True
        config.log_responses = True

        # Configura logging do Python
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )

        # Ativa DEBUG para loggers do sicoob
        for logger_name in ['sicoob', 'sicoob.async_client', 'sicoob.async_boleto']:
            logging.getLogger(logger_name).setLevel(logging.DEBUG)

    @classmethod
    def disable_debug(cls) -> None:
        """Desativa modo debug

        Restaura configurações de logging para o nível INFO
        """
        import logging

        instance = cls()
        config = instance._current_config

        config.debug_mode = False
        config.log_level = 'INFO'
        config.log_requests = False
        config.log_responses = False

        # Restaura nível de log
        logging.basicConfig(level=logging.INFO)

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
