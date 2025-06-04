from typing import Dict
import requests
from .auth import OAuth2Client

class APIClientBase:
    """Classe base para APIs do Sicoob"""
    
    BASE_URL = "https://api.sicoob.com.br"
    SANDBOX_URL = "https://sandbox.sicoob.com.br/sicoob/sandbox"
    
    def __init__(self, oauth_client: OAuth2Client, session: requests.Session, sandbox_mode: bool = False):
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
        return self.SANDBOX_URL if self.sandbox_mode else self.BASE_URL
        
    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers padrão com token de acesso"""
        token = self.oauth_client.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
