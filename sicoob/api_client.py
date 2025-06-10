import requests

from .auth import OAuth2Client
from .constants import BASE_URL, SANDBOX_URL


class APIClientBase:
    """Classe base para APIs do Sicoob"""

    def __init__(
        self,
        oauth_client: OAuth2Client,
        session: requests.Session,
        sandbox_mode: bool = False,
    ) -> None:
        """Inicializa com cliente OAuth e sessão HTTP existente

        Args:
            oauth_client: Cliente OAuth2 para autenticação
            session: Sessão HTTP existente
            sandbox_mode: Se True, usa URL de sandbox (default: False)
        """
        self.sandbox_mode = sandbox_mode
        self.oauth_client = oauth_client
        self.session = session

    def _get_base_url(self) -> str:
        """Retorna a URL base conforme modo de operação"""
        return SANDBOX_URL if self.sandbox_mode else BASE_URL

    def _get_headers(self, scope: str) -> dict[str, str]:
        """Retorna headers padrão com token de acesso"""
        token = self.oauth_client.get_access_token(scope)
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
