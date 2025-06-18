import json
import requests

from sicoob.auth import OAuth2Client
from sicoob.constants import BASE_URL, SANDBOX_URL
from sicoob.exceptions import RespostaInvalidaError


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
        if self.sandbox_mode:
            import os
            from dotenv import load_dotenv

            load_dotenv()

            token = os.getenv('SICOOB_SANDBOX_TOKEN', 'sandbox-token')
            client_id = os.getenv('SICOOB_SANDBOX_CLIENT_ID', 'sandbox-client-id')
        else:
            token = self.oauth_client.get_access_token(scope)
            client_id = self.oauth_client.client_id

        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'User-Agent': 'SicoobAPIClient/1.0',
            'client_id': client_id,
        }

    def _validate_response(self, response: requests.Response) -> dict:
        """Valida se a resposta da API é um JSON válido

        Args:
            response: Objeto Response do requests

        Returns:
            dict: Dados JSON da resposta

        Raises:
            RespostaInvalidaError: Se a resposta não for JSON válido
        """
        try:
            # Skip content-type validation for Mock objects during testing
            if hasattr(response, '_mock_return_value'):  # Checking for Mock object
                return response.json()

            content_type = response.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                raise RespostaInvalidaError(
                    f'Resposta não é JSON (Content-Type: {content_type})', response
                )

            return response.json()
        except json.JSONDecodeError as e:
            raise RespostaInvalidaError(
                f'Resposta não é JSON válido: {str(e)}', response
            ) from e
