import os
import time
import requests
import requests_pkcs12
from typing import Union, BinaryIO
from sicoob.constants import AUTH_URL
from dotenv import load_dotenv


class OAuth2Client:
    """Cliente OAuth2 para autenticação com a API Sicoob"""

    def __init__(
        self,
        client_id: str | None = None,
        certificado: str | None = None,
        chave_privada: str | None = None,
        certificado_pfx: Union[str, bytes, BinaryIO] | None = None,
        senha_pfx: str | None = None,
        sandbox_mode: bool = False,
    ) -> None:
        """Inicializa o cliente OAuth2

        Args:
            client_id: Client ID para autenticação OAuth2
            certificado: Path para o certificado PEM (opcional)
            chave_privada: Path para a chave privada PEM (opcional)
            certificado_pfx: Path ou dados do certificado PFX (opcional)
            senha_pfx: Senha do certificado PFX (opcional)
            sandbox_mode: Se True, não requer certificado (default: False)
        """
        load_dotenv()

        self.client_id = client_id or os.getenv('SICOOB_CLIENT_ID')
        self.certificado = certificado or os.getenv('SICOOB_CERTIFICADO')
        self.chave_privada = chave_privada or os.getenv('SICOOB_CHAVE_PRIVADA')
        self.certificado_pfx = certificado_pfx or os.getenv('SICOOB_CERTIFICADO_PFX')
        self.senha_pfx = senha_pfx or os.getenv('SICOOB_SENHA_PFX')

        self.token_url = AUTH_URL  # URL de autenticação OAuth2
        self.token_cache = {}  # Cache de tokens por escopo
        self.session = requests.Session()

        self.sandbox_mode = sandbox_mode

        if not self.sandbox_mode:
            if self.certificado_pfx and self.senha_pfx:
                # Configura autenticação com PFX
                pkcs12_adapter = requests_pkcs12.Pkcs12Adapter(
                    pkcs12_data=self.certificado_pfx
                    if isinstance(self.certificado_pfx, bytes)
                    else None,
                    pkcs12_filename=self.certificado_pfx
                    if isinstance(self.certificado_pfx, str)
                    else None,
                    pkcs12_password=self.senha_pfx,
                )
                self.session.mount('https://', pkcs12_adapter)
            elif self.certificado and self.chave_privada:
                # Configura autenticação com PEM (manter compatibilidade)
                self.session.cert = (self.certificado, self.chave_privada)
            else:
                raise ValueError(
                    'É necessário fornecer certificado e chave privada (PEM) '
                    'ou certificado PFX e senha'
                )

    def get_access_token(self, scope: str | None = None) -> str:
        """Obtém ou renova o token de acesso para o escopo especificado

        Args:
            scope: Escopo(s) necessário(s) para a API. Exemplos:
                - Cobrança por Boleto: "boletos_inclusao boletos_consulta boletos_alteracao webhooks_alteracao webhooks_consulta webhooks_inclusao"
                - Conta Corrente: "cco_consulta cco_transferencias openid"
                - Recebimento no PIX: "cob.write cob.read cobv.write cobv.read lotecobv.write lotecobv.read pix.write pix.read webhook.read webhook.write payloadlocation.write payloadlocation.read"

        Returns:
            str: Token de acesso válido para o escopo solicitado
        """
        # Usa escopo padrão se não especificado (para compatibilidade)
        if scope is None:
            scope = 'cco_extrato cco_consulta'

        # Verifica se já existe token válido para este escopo
        if scope in self.token_cache and not self._is_token_expired(scope):
            return self.token_cache[scope]['access_token']

        token_data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'scope': scope,
        }

        response = self.session.post(self.token_url, data=token_data)
        response.raise_for_status()

        token_info = response.json()
        token_info['expires_at'] = time.time() + token_info['expires_in']

        # Armazena o token no cache por escopo
        self.token_cache[scope] = token_info

        return token_info['access_token']

    def _is_token_expired(self, scope: str) -> bool:
        """Verifica se o token para o escopo especificado expirou"""
        if scope not in self.token_cache or 'expires_at' not in self.token_cache[scope]:
            return True
        return (
            time.time() >= self.token_cache[scope]['expires_at'] - 60
        )  # 60s de margem
