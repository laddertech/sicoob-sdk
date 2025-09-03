"""Constantes globais para o cliente Sicoob"""

from sicoob.config import SicoobConfig


# URLs dinâmicas baseadas na configuração do ambiente
def get_auth_url() -> str:
    """Retorna URL de autenticação baseada no ambiente"""
    return SicoobConfig.get_auth_url()


def get_base_url() -> str:
    """Retorna URL base baseada no ambiente"""
    return SicoobConfig.get_base_url()


# Mantém constantes legadas para compatibilidade
AUTH_URL = (
    'https://auth.sicoob.com.br/auth/realms/cooperado/protocol/openid-connect/token'
)
BASE_URL = 'https://api.sicoob.com.br'
SANDBOX_URL = 'https://sandbox.sicoob.com.br/sicoob/sandbox'
