"""Módulo principal do SDK Sicoob"""

from .client import Sicoob
from .conta_corrente import ContaCorrenteAPI
from .pix import PixAPI
from .boleto import BoletoAPI
from .exceptions import (
    SicoobError,
    BoletoError,
    BoletoEmissaoError,
    BoletoConsultaError,
    BoletoNaoEncontradoError,
    ContaCorrenteError,
    PixError,
    AutenticacaoError,
    ExtratoError,
    SaldoError,
    TransferenciaError,
    CobrancaPixError,
    CobrancaPixNaoEncontradaError,
    CobrancaPixVencimentoError,
    WebhookPixError,
    WebhookPixNaoEncontradoError,
    LoteCobrancaPixError,
    QrCodePixError
)

__version__ = "0.1.4"
__all__ = [
    "Sicoob",
    "ContaCorrenteAPI",
    "PixAPI",
    "BoletoAPI",
    "SicoobError",
    "BoletoError",
    "BoletoEmissaoError",
    "BoletoConsultaError",
    "BoletoNaoEncontradoError",
    "ContaCorrenteError",
    "PixError",
    "AutenticacaoError",
    "ExtratoError",
    "SaldoError",
    "TransferenciaError",
    "CobrancaPixError",
    "CobrancaPixNaoEncontradaError",
    "CobrancaPixVencimentoError",
    "WebhookPixError",
    "WebhookPixNaoEncontradoError",
    "LoteCobrancaPixError",
    "QrCodePixError"
]
