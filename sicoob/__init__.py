"""Módulo principal do SDK Sicoob"""

from .boleto import BoletoAPI
from .client import Sicoob
from .cobranca import CobrancaAPI
from .conta_corrente import ContaCorrenteAPI
from .exceptions import (
    AutenticacaoError,
    BoletoConsultaError,
    BoletoEmissaoError,
    BoletoError,
    BoletoNaoEncontradoError,
    CobrancaPixError,
    CobrancaPixNaoEncontradaError,
    CobrancaPixVencimentoError,
    ContaCorrenteError,
    ExtratoError,
    LoteCobrancaPixError,
    PixError,
    QrCodePixError,
    SaldoError,
    SicoobError,
    TransferenciaError,
    WebhookPixError,
    WebhookPixNaoEncontradoError,
)
from .pix import PixAPI

# Funcionalidades assíncronas (importadas opcionalmente)
try:
    from .async_boleto import AsyncBoletoAPI  # noqa: F401
    from .async_cache import (  # noqa: F401
        AsyncCacheManager,
        async_cached,
        get_default_async_cache,
    )
    from .async_client import (  # noqa: F401
        AsyncAPIClient,
        AsyncCobrancaAPI,
        AsyncContaCorrenteAPI,
        AsyncSicoob,
        async_batch_processor,
        gather_with_concurrency,
    )
    from .async_pix import AsyncPixAPI  # noqa: F401

    _async_available = True

    __all_async__ = [
        'AsyncSicoob',
        'AsyncAPIClient',
        'AsyncContaCorrenteAPI',
        'AsyncCobrancaAPI',
        'AsyncBoletoAPI',
        'AsyncPixAPI',
        'AsyncCacheManager',
        'gather_with_concurrency',
        'async_batch_processor',
        'get_default_async_cache',
        'async_cached',
    ]

except ImportError:
    # Dependências assíncronas não instaladas
    _async_available = False
    __all_async__ = []

__version__ = '0.1.32'
__all__ = [
    'AutenticacaoError',
    'BoletoAPI',
    'BoletoConsultaError',
    'BoletoEmissaoError',
    'BoletoError',
    'BoletoNaoEncontradoError',
    'CobrancaAPI',
    'CobrancaPixError',
    'CobrancaPixNaoEncontradaError',
    'CobrancaPixVencimentoError',
    'ContaCorrenteAPI',
    'ContaCorrenteError',
    'ExtratoError',
    'LoteCobrancaPixError',
    'PixAPI',
    'PixError',
    'QrCodePixError',
    'SaldoError',
    'Sicoob',
    'SicoobError',
    'TransferenciaError',
    'WebhookPixError',
    'WebhookPixNaoEncontradoError',
    *__all_async__,
]


def is_async_available() -> bool:
    """Verifica se funcionalidades assíncronas estão disponíveis."""
    return _async_available


def get_async_info() -> dict:
    """Retorna informações sobre disponibilidade async."""
    return {
        'available': _async_available,
        'classes': __all_async__ if _async_available else [],
        'required_packages': ['aiohttp>=3.8.0', 'aiofiles>=24.0.0']
        if not _async_available
        else [],
    }
