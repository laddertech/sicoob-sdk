import time
from typing import BinaryIO

import requests
import requests_pkcs12

from sicoob._credenciais import validar_client_id
from sicoob.config import Environment, EnvironmentConfig, SicoobConfig
from sicoob.exceptions import AutenticacaoError
from sicoob.logging_config import get_logger


class OAuth2Client:
    """Cliente OAuth2 para autenticação com a API Sicoob"""

    def __init__(
        self,
        client_id: str | None = None,
        certificado: str | None = None,
        chave_privada: str | None = None,
        certificado_pfx: str | bytes | BinaryIO | None = None,
        senha_pfx: str | None = None,
        config: EnvironmentConfig | None = None,
        sandbox_token: str | None = None,
    ) -> None:
        """Inicializa o cliente OAuth2

        Todas as credenciais são explícitas: o cliente não lê variáveis de
        ambiente nem arquivos ``.env``.

        Args:
            client_id: Client ID para autenticação OAuth2 (obrigatório)
            certificado: Path para o certificado PEM (opcional)
            chave_privada: Path para a chave privada PEM (opcional)
            certificado_pfx: Path ou dados do certificado PFX (opcional)
            senha_pfx: Senha do certificado PFX (opcional)
            config: Configuração do ambiente desta instância. Sem ela, usa
                uma configuração nova de produção (nunca a global).
            sandbox_token: Token fixo do sandbox do Sicoob (só no sandbox)

        Raises:
            ValueError: ``client_id`` ausente ou certificado exigido e não
                informado.
        """
        # Inicializa logger
        self.logger = get_logger(__name__)

        self.client_id = validar_client_id(client_id)
        self.certificado = certificado
        self.chave_privada = chave_privada
        self.certificado_pfx = certificado_pfx
        self.senha_pfx = senha_pfx
        self.sandbox_token = sandbox_token
        # Sem config explícita, produção nova — nunca a configuração global,
        # que outra parte do processo pode ter trocado para o sandbox.
        self.config = (
            config
            if config is not None
            else SicoobConfig.config_for(Environment.PRODUCTION)
        )

        self.token_url = self.config.auth_url  # URL de autenticação OAuth2
        self.token_cache = {}  # Cache de tokens por escopo
        self.session = requests.Session()

        if self.config.require_certificate:
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
            self.logger.debug(
                'Token válido encontrado no cache',
                extra={'operation': 'token_cache_hit', 'scope': scope},
            )
            return self.token_cache[scope]['access_token']

        self.logger.info(
            'Solicitando novo token de acesso',
            extra={
                'operation': 'token_request',
                'scope': scope,
                'cached_scopes': len(self.token_cache),
            },
        )

        token_data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'scope': scope,
        }

        try:
            response = self.session.post(self.token_url, data=token_data)
            response.raise_for_status()

            token_info = response.json()
            token_info['expires_at'] = time.time() + token_info['expires_in']

            # Armazena o token no cache por escopo
            self.token_cache[scope] = token_info

            self.logger.info(
                'Token de acesso obtido com sucesso',
                extra={
                    'operation': 'token_success',
                    'scope': scope,
                    'expires_in': token_info['expires_in'],
                    'token_type': token_info.get('token_type', 'Bearer'),
                },
            )

            return token_info['access_token']

        except requests.exceptions.RequestException as e:
            self.logger.error(
                f'Falha na requisição de token: {e!s}',
                extra={'operation': 'token_request_error', 'scope': scope},
                exc_info=True,
            )
            # Tratar erro 401 especificamente como erro de autenticação
            if e.response is not None and e.response.status_code == 401:
                raise AutenticacaoError(
                    'Falha na autenticação OAuth2: credenciais inválidas, '
                    'client_id incorreto ou certificado não autorizado',
                    code=401,
                    response=e.response,
                    response_text=e.response.text,
                    response_headers=dict(e.response.headers),
                ) from e
            raise
        except Exception as e:
            self.logger.error(
                f'Erro inesperado ao obter token: {e!s}',
                extra={'operation': 'token_error', 'scope': scope},
                exc_info=True,
            )
            raise

    def get_token(self, scope: str | None = None) -> str:
        """Alias de `get_access_token` no contrato esperado pela pypix-api

        A pypix-api obtém o token chamando ``oauth.get_token(escopos)``.

        Args:
            scope: Escopo(s) necessário(s) para a API

        Returns:
            str: Token de acesso válido para o escopo solicitado
        """
        return self.get_access_token(scope)

    def _is_token_expired(self, scope: str) -> bool:
        """Verifica se o token para o escopo especificado expirou"""
        if scope not in self.token_cache or 'expires_at' not in self.token_cache[scope]:
            return True
        return (
            time.time() >= self.token_cache[scope]['expires_at'] - 60
        )  # 60s de margem
