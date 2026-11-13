from typing import BinaryIO

from sicoob._credenciais import ler_env, validar_client_id
from sicoob.auth import OAuth2Client
from sicoob.cobranca import CobrancaAPI
from sicoob.config import Environment, SicoobConfig
from sicoob.conta_corrente import ContaCorrenteAPI
from sicoob.logging_config import SicoobLogger, get_logger


class Sicoob:
    """Cliente para API do Sicoob

    Todas as credenciais e o ambiente são explícitos e próprios da instância:
    o cliente não lê variáveis de ambiente nem altera configuração global.
    Para ler de variáveis de ambiente, use :meth:`Sicoob.from_env`.
    """

    def __init__(
        self,
        client_id: str | None = None,
        certificado: str | None = None,
        chave_privada: str | None = None,
        certificado_pfx: str | bytes | BinaryIO | None = None,
        senha_pfx: str | None = None,
        environment: str | Environment = Environment.PRODUCTION,
        sandbox_token: str | None = None,
    ) -> None:
        """Inicializa o cliente com credenciais

        Args:
            client_id: Client ID para autenticação OAuth2 (obrigatório)
            certificado: Path para o certificado PEM (opcional)
            chave_privada: Path para a chave privada PEM (opcional)
            certificado_pfx: Path (str), bytes ou arquivo aberto (BinaryIO) do certificado PFX (opcional)
            senha_pfx: Senha do certificado PFX (opcional)
            environment: Ambiente (development, test, staging, production,
                sandbox). Padrão: production. Valor desconhecido é erro.
            sandbox_token: Token fixo do sandbox do Sicoob (só no sandbox)

        Raises:
            ValueError: ``client_id`` ausente, ambiente desconhecido ou
                certificado exigido e não informado.
        """
        config = SicoobConfig.config_for(environment)
        self.config = config

        # Logging global do SDK: configura uma vez, sem que cada nova
        # instância reconfigure o processo inteiro. O que pode expor dados
        # (requisições/respostas HTTP) é decidido pela config de cada
        # instância no momento do log, não pelo nível global.
        SicoobLogger.configure(
            level=config.log_level,
            format_type=config.log_format,
            log_requests=config.log_requests,
            log_responses=config.log_responses,
        )

        # Inicializa logger
        self.logger = get_logger(__name__)

        self.client_id = client_id
        self.certificado = certificado
        self.chave_privada = chave_privada
        self.certificado_pfx = certificado_pfx
        self.senha_pfx = senha_pfx
        self.sandbox_token = sandbox_token

        self.environment = config.environment

        # Valida credenciais mínimas
        try:
            self.client_id = validar_client_id(self.client_id)
        except ValueError:
            self.logger.error(
                'Client ID não fornecido', extra={'operation': 'client_init'}
            )
            raise

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
                else 'none',
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
            config=config,
            sandbox_token=self.sandbox_token,
        )

        # Armazena a sessão do OAuth2Client
        # para reutilização nas APIs
        self.session = self.oauth_client.session

        self.logger.info(
            'Cliente Sicoob inicializado com sucesso',
            extra={'operation': 'client_init_complete'},
        )

    @classmethod
    def from_env(cls, dotenv: bool = True, **overrides) -> 'Sicoob':
        """Cria o cliente a partir das variáveis de ambiente ``SICOOB_*``.

        É a única forma de o SDK ler credenciais do ambiente — e só quando
        chamada explicitamente. Use em scripts e testes de integração; em
        aplicações com várias contas, passe as credenciais ao construtor.

        Variáveis: ``SICOOB_CLIENT_ID``, ``SICOOB_CERTIFICADO``,
        ``SICOOB_CHAVE_PRIVADA``, ``SICOOB_CERTIFICADO_PFX``,
        ``SICOOB_SENHA_PFX``, ``SICOOB_ENVIRONMENT`` (padrão production) e
        ``SICOOB_SANDBOX_TOKEN``.

        Args:
            dotenv: carrega o arquivo ``.env`` antes de ler o ambiente.
            **overrides: argumentos do construtor que prevalecem sobre o
                ambiente.
        """
        return cls(**{**ler_env(dotenv), **overrides})

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
