"""Módulo de cobrança que agrega APIs de Boleto e PIX"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import requests

    from sicoob.auth import OAuth2Client

from sicoob.boleto import BoletoAPI
from sicoob.pix import PixAPI


class CobrancaAPI:
    """API agregadora de serviços de cobrança (Boleto e PIX)

    Esta classe fornece acesso unificado aos serviços de cobrança do Sicoob,
    incluindo boletos bancários e PIX.
    """

    def __init__(
        self,
        oauth_client: 'OAuth2Client',
        session: 'requests.Session',
        sandbox_mode: bool = False,
    ):
        """Inicializa a API de cobrança

        Args:
            oauth_client: Cliente OAuth2 para autenticação
            session: Sessão de requests configurada
            sandbox_mode: Modo sandbox (default: False)
        """
        self.boleto = BoletoAPI(oauth_client, session, sandbox_mode=sandbox_mode)
        self.pix = PixAPI(oauth_client, session, sandbox_mode=sandbox_mode)

    def __repr__(self):
        return f'<CobrancaAPI sandbox={self.boleto.sandbox_mode}>'


__all__ = ['BoletoAPI', 'CobrancaAPI', 'PixAPI']
