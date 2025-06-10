"""Módulo principal do SDK Sicoob"""

from .boleto import BoletoAPI
from .client import Sicoob
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

__version__ = '0.1.5'
__all__ = [
    'AutenticacaoError',
    'BoletoAPI',
    'BoletoConsultaError',
    'BoletoEmissaoError',
    'BoletoError',
    'BoletoNaoEncontradoError',
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
]
