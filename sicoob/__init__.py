"""Módulo principal do SDK Sicoob"""
from pypix_api.banks.sicoob import SicoobPixAPI

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

__version__ = '0.1.16'
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
    'PixError',
    'QrCodePixError',
    'SaldoError',
    'Sicoob',
    'SicoobError',
    'SicoobPixAPI',
    'TransferenciaError',
    'WebhookPixError',
    'WebhookPixNaoEncontradoError',
]
