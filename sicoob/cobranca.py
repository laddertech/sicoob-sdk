"""Módulo de cobrança que agrega APIs de Boleto e PIX"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import requests

    from sicoob.auth import OAuth2Client

from sicoob.boleto import BoletoAPI
from sicoob.config import SicoobConfig
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
    ):
        """Inicializa a API de cobrança

        Args:
            oauth_client: Cliente OAuth2 para autenticação
            session: Sessão de requests configurada
        """
        self.boleto = BoletoAPI(oauth_client, session)
        self.pix = PixAPI(oauth_client, session)

    def __repr__(self):
        return f'<CobrancaAPI environment={SicoobConfig.get_current_config().environment.value}>'


__all__ = ['BoletoAPI', 'CobrancaAPI', 'PixAPI']
