import os
from typing import Any, BinaryIO, Union

import requests
from dotenv import load_dotenv
from pypix_api.banks.sicoob import SicoobPixAPI
from pypix_api.banks.exceptions import (
    PixAcessoNegadoException,
    PixErroDesconhecidoException,
    PixErroServicoIndisponivelException,
    PixErroValidacaoException,
    PixRecursoNaoEncontradoException,
)

from sicoob.auth import OAuth2Client
from sicoob.cobranca import BoletoAPI
from sicoob.conta_corrente import ContaCorrenteAPI


class SicoobPixAPICustom(SicoobPixAPI):
    def _handle_error_response(
        self, response: requests.Response, **kwargs: Any
    ) -> None:
        """Trata respostas de erro da API de forma centralizada

        Sobrescreve o método original para lidar corretamente com status de sucesso
        e lançar exceções específicas do domínio.
        """
        # Se for uma resposta de sucesso, não faz nada
        status_code = getattr(response, 'status_code', None)
        if status_code and 200 <= status_code < 300:
            return

        try:
            error_data = response.json()
        except (ValueError, AttributeError):
            error_data = {}

        type_ = error_data.get("type", "")
        title = error_data.get("title", "")
        status = error_data.get("status", status_code)
        detail = error_data.get("detail", "")

        # Verifica se é uma exceção de domínio específica
        if status == 404:
            if "Cobrança" in title:
                from sicoob.exceptions import CobrancaPixNaoEncontradaError
                raise CobrancaPixNaoEncontradaError(detail)
            elif "Webhook" in title:
                from sicoob.exceptions import WebhookPixNaoEncontradoError
                raise WebhookPixNaoEncontradoError(detail)

        # Mapeamento para exceções genéricas
        if status == 403 or "AcessoNegado" in type_:
            raise PixAcessoNegadoException(type_, title, status, detail)
        elif status == 400 or "ErroValidacao" in type_:
            raise PixErroValidacaoException(type_, title, status, detail)
        elif status == 503:
            raise PixErroServicoIndisponivelException(type_, title, status, detail)
        else:
            raise PixErroDesconhecidoException(type_, title, status, detail)

class CobrancaServices:
    def __init__(
        self, oauth_client: OAuth2Client, session: requests.Session, sandbox_mode: bool
    ) -> None:
        self.boleto = BoletoAPI(oauth_client, session, sandbox_mode=sandbox_mode)
        self.pix = SicoobPixAPICustom(oauth=oauth_client, sandbox_mode=sandbox_mode)


class Sicoob:
    """Cliente para API do Sicoob"""

    def __init__(
        self,
        client_id: str | None = None,
        certificado: str | None = None,
        chave_privada: str | None = None,
        certificado_pfx: Union[str, bytes, BinaryIO] | None = None,
        senha_pfx: str | None = None,
        sandbox_mode: bool = False,
    ) -> None:
        """Inicializa o cliente com credenciais

        Args:
            client_id: Client ID para autenticação OAuth2
            certificado: Path para o certificado PEM (opcional)
            chave_privada: Path para a chave privada PEM (opcional)
            certificado_pfx: Path (str), bytes ou arquivo aberto (BinaryIO) do certificado PFX (opcional)
            senha_pfx: Senha do certificado PFX (opcional)
            sandbox_mode: Modo sandbox (default: False)
        """
        load_dotenv()

        self.client_id = client_id or os.getenv('SICOOB_CLIENT_ID')
        self.certificado = certificado or os.getenv('SICOOB_CERTIFICADO')
        self.chave_privada = chave_privada or os.getenv('SICOOB_CHAVE_PRIVADA')
        self.certificado_pfx = certificado_pfx or os.getenv('SICOOB_CERTIFICADO_PFX')
        self.senha_pfx = senha_pfx or os.getenv('SICOOB_SENHA_PFX')
        self.sandbox_mode = sandbox_mode

        # Valida credenciais mínimas
        if not self.client_id:
            raise ValueError('client_id é obrigatório')

        # Em modo sandbox, não é obrigatório ter certificado
        if not self.sandbox_mode:
            # Verifica se pelo menos um conjunto de credenciais foi fornecido explicitamente
            has_pem = bool(certificado and chave_privada)
            has_pfx = bool(certificado_pfx and senha_pfx)

            if not (has_pem or has_pfx):
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
            sandbox_mode=self.sandbox_mode,
        )

        # Armazena a sessão do OAuth2Client
        # para reutilização nas APIs
        self.session = self.oauth_client.session

    def _get_token(self) -> dict[str, str]:
        """Obtém token de acesso usando OAuth2Client"""
        try:
            access_token = self.oauth_client.get_access_token()
            return {'access_token': access_token}
        except Exception as e:
            raise Exception(f'Falha ao obter token de acesso: {e!s}') from e

    @property
    def cobranca(self) -> CobrancaServices:
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
