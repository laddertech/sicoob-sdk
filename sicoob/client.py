import os

import requests
from dotenv import load_dotenv

from sicoob.auth import OAuth2Client
from sicoob.cobranca import BoletoAPI, PixAPI
from sicoob.conta_corrente import ContaCorrenteAPI


class CobrancaServices:
    def __init__(
        self, oauth_client: OAuth2Client, session: requests.Session, sandbox_mode: bool
    ) -> None:
        self.boleto = BoletoAPI(oauth_client, session, sandbox_mode=sandbox_mode)
        self.pix = PixAPI(oauth_client, session, sandbox_mode=sandbox_mode)


class Sicoob:
    """Cliente para API do Sicoob"""

    def __init__(
        self,
        client_id: str | None = None,
        certificado: str | None = None,
        chave_privada: str | None = None,
        sandbox_mode: bool = False,
    ) -> None:
        """Inicializa o cliente com credenciais"""
        load_dotenv()

        self.client_id = client_id or os.getenv('SICOOB_CLIENT_ID')
        self.certificado = certificado or os.getenv('SICOOB_CERTIFICADO')
        self.chave_privada = chave_privada or os.getenv('SICOOB_CHAVE_PRIVADA')
        self.sandbox_mode = sandbox_mode

        if not all([self.client_id, self.certificado, self.chave_privada]):
            raise ValueError(
                'Credenciais incompletas. Configure via parâmetros ou arquivo .env'
            )

        self.oauth_client = OAuth2Client(
            client_id=self.client_id,
            certificado=self.certificado,
            chave_privada=self.chave_privada,
        )
        self.session = requests.Session()
        self.session.cert = (self.certificado, self.chave_privada)

    def _get_token(self) -> dict[str, str]:
        """Obtém token de acesso usando OAuth2Client"""
        try:
            access_token = self.oauth_client.get_access_token()
            return {'access_token': access_token}
        except Exception as e:
            raise Exception(f'Falha ao obter token de acesso: {e!s}') from e

    @property
    def cobranca(self) -> 'CobrancaServices':
        """Acesso às APIs de Cobrança (Boleto e PIX)

        Retorna um objeto com duas propriedades:
        - boleto: API para operações de boleto bancário
        - pix: API para operações de PIX

        Exemplo:
            >>> sicoob = Sicoob(client_id, certificado, chave)
            >>> boleto = sicoob.cobranca.boleto.emitir_boleto(dados)
            >>> pix = sicoob.cobranca.pix.criar_cobranca_pix(txid, dados)
        """

        return CobrancaServices(self.oauth_client, self.session, self.sandbox_mode)

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

        return ContaCorrenteAPI(self.oauth_client, self.session, self.sandbox_mode)
