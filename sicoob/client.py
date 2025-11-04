import os
from typing import BinaryIO

from dotenv import load_dotenv

from sicoob.auth import OAuth2Client
from sicoob.cobranca import CobrancaAPI
from sicoob.config import Environment, SicoobConfig
from sicoob.conta_corrente import ContaCorrenteAPI
from sicoob.logging_config import SicoobLogger, get_logger


class Sicoob:
    """Cliente para API do Sicoob"""

    def __init__(
        self,
        client_id: str | None = None,
        certificado: str | None = None,
        chave_privada: str | None = None,
        certificado_pfx: str | bytes | BinaryIO | None = None,
        senha_pfx: str | None = None,
        environment: str | Environment | None = None,
    ) -> None:
        """Inicializa o cliente com credenciais

        Args:
            client_id: Client ID para autenticação OAuth2
            certificado: Path para o certificado PEM (opcional)
            chave_privada: Path para a chave privada PEM (opcional)
            certificado_pfx: Path (str), bytes ou arquivo aberto (BinaryIO) do certificado PFX (opcional)
            senha_pfx: Senha do certificado PFX (opcional)
            environment: Ambiente (development, test, staging, production, sandbox)
        """
        load_dotenv()

        # Configura ambiente se fornecido
        if environment is not None:
            if isinstance(environment, str):
                env_mapping = {
                    'dev': Environment.DEVELOPMENT,
                    'development': Environment.DEVELOPMENT,
                    'test': Environment.TEST,
                    'staging': Environment.STAGING,
                    'prod': Environment.PRODUCTION,
                    'production': Environment.PRODUCTION,
                    'sandbox': Environment.SANDBOX,
                }
                env = env_mapping.get(environment.lower(), Environment.PRODUCTION)
            else:
                env = environment
            SicoobConfig.set_environment(env)

        # Configuração automática de logging baseada no ambiente
        config = SicoobConfig.get_current_config()
        SicoobLogger.configure(
            level=config.log_level,
            format_type=config.log_format,
            log_requests=config.log_requests,
            log_responses=config.log_responses,
            force_reconfigure=True,
        )

        # Inicializa logger
        self.logger = get_logger(__name__)

        self.client_id = client_id or os.getenv('SICOOB_CLIENT_ID')
        self.certificado = certificado or os.getenv('SICOOB_CERTIFICADO')
        self.chave_privada = chave_privada or os.getenv('SICOOB_CHAVE_PRIVADA')
        self.certificado_pfx = certificado_pfx or os.getenv('SICOOB_CERTIFICADO_PFX')
        self.senha_pfx = senha_pfx or os.getenv('SICOOB_SENHA_PFX')

        self.environment = config.environment

        # Valida credenciais mínimas
        if not self.client_id:
            self.logger.error(
                'Client ID não fornecido', extra={'operation': 'client_init'}
            )
            raise ValueError('client_id é obrigatório')

        # Log de inicialização
        self.logger.info(
            'Inicializando cliente Sicoob',
            extra={
                'operation': 'client_init',
                'environment': config.environment.value,
                'has_certificate': bool(certificado or certificado_pfx),
                'auth_method': 'pfx'
                if certificado_pfx
                else 'pem'
                if certificado
                else 'env_vars',
                'requires_certificate': config.require_certificate,
            },
        )

        # Validação de certificado baseada na configuração do ambiente
        if config.require_certificate:
            # Verifica se pelo menos um conjunto de credenciais foi fornecido explicitamente
            has_pem = bool(certificado and chave_privada)
            has_pfx = bool(certificado_pfx and senha_pfx)

            if not (has_pem or has_pfx):
                self.logger.error(
                    'Credenciais de certificado insuficientes para produção',
                    extra={
                        'operation': 'client_init',
                        'has_pem': has_pem,
                        'has_pfx': has_pfx,
                    },
                )
                raise ValueError(
                    'É necessário fornecer certificado e chave privada (PEM) '
                    'ou certificado PFX e senha explicitamente'
                )

        self.oauth_client = OAuth2Client(
            client_id=self.client_id,
            certificado=self.certificado,
            chave_privada=self.chave_privada,
            certificado_pfx=self.certificado_pfx,
            senha_pfx=self.senha_pfx,
        )

        # Armazena a sessão do OAuth2Client
        # para reutilização nas APIs
        self.session = self.oauth_client.session

        self.logger.info(
            'Cliente Sicoob inicializado com sucesso',
            extra={'operation': 'client_init_complete'},
        )

    def _get_token(self) -> dict[str, str]:
        """Obtém token de acesso usando OAuth2Client"""
        self.logger.debug('Obtendo token de acesso', extra={'operation': 'get_token'})

        try:
            access_token = self.oauth_client.get_access_token()
            self.logger.info(
                'Token de acesso obtido com sucesso', extra={'operation': 'get_token'}
            )
            return {'access_token': access_token}
        except Exception as e:
            self.logger.error(
                f'Falha ao obter token de acesso: {e!s}',
                extra={'operation': 'get_token_error'},
                exc_info=True,
            )
            raise Exception(f'Falha ao obter token de acesso: {e!s}') from e

    @property
    def cobranca(self) -> CobrancaAPI:
        """Acesso às APIs de Cobrança (Boleto e PIX)

        Retorna um objeto com duas propriedades:
        - boleto: API para operações de boleto bancário
        - pix: API para operações de PIX

        Exemplo:
            >>> sicoob = Sicoob(client_id, certificado, chave)
            >>> boleto = sicoob.cobranca.boleto.emitir_boleto(dados)
            >>> pix = sicoob.cobranca.pix.criar_cobranca_pix(txid, dados)
        """

        return CobrancaAPI(self.oauth_client, self.session)

    @property
    def conta_corrente(self) -> ContaCorrenteAPI:
        """Acesso à API de Conta Corrente

        Retorna um objeto com métodos para:
        - extrato: Consulta de extrato bancário
        - saldo: Consulta de saldo
        - transferencia: Realização de transferências

        Exemplo:
            >>> sicoob = Sicoob(client_id, certificado, chave)
            >>> extrato = sicoob.conta_corrente.extrato(data_inicio, data_fim)
            >>> saldo = sicoob.conta_corrente.saldo()
            >>> transferencia = sicoob.conta_corrente.transferencia(valor, conta_destino)
        """

        return ContaCorrenteAPI(self.oauth_client, self.session)
