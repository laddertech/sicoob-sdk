from typing import Any

import requests
from pypix_api.banks.sicoob import SicoobPixAPI

from sicoob.api_client import APIClientBase
from sicoob.exceptions import (
    CobrancaPixNaoEncontradaError,
    PixError,
    WebhookPixNaoEncontradoError,
)


class PixAPI(APIClientBase):
    """API de PIX do Sicoob integrada ao SDK

    Esta classe encapsula a pypix-api e oferece uma interface consistente
    com o resto do SDK Sicoob, incluindo tratamento de erros padronizado.
    """

    def __init__(self, oauth_client, session, sandbox_mode=False):
        """Inicializa a API de PIX.

        Args:
            oauth_client: Cliente OAuth2 para autenticação
            session: Sessão de requests configurada
            sandbox_mode: Modo sandbox (default: False)
        """
        super().__init__(oauth_client, session, sandbox_mode)

        # Inicializa a API PIX subjacente
        self._pix_api = SicoobPixAPICustom(
            oauth=oauth_client, sandbox_mode=sandbox_mode
        )

        # Define o caminho base da API
        self.base_path = '/pix/api/v2'

    def criar_cobranca_imediata(self, txid: str, dados_cobranca: dict) -> dict:
        """Cria uma cobrança PIX imediata

        Args:
            txid: Identificador único da transação (27-36 caracteres)
            dados_cobranca: Dados da cobrança conforme especificação do BACEN

        Returns:
            dict: Resposta da API com os dados da cobrança criada

        Raises:
            PixError: Erro genérico na operação
            CobrancaPixNaoEncontradaError: Cobrança não encontrada
        """
        try:
            return self._pix_api.criar_cob(txid, dados_cobranca)
        except Exception as e:
            self._handle_pix_error(e)

    def consultar_cobranca_imediata(self, txid: str) -> dict:
        """Consulta uma cobrança PIX imediata

        Args:
            txid: Identificador único da transação

        Returns:
            dict: Dados da cobrança

        Raises:
            CobrancaPixNaoEncontradaError: Cobrança não encontrada
            PixError: Erro genérico na operação
        """
        try:
            return self._pix_api.consultar_cob(txid)
        except Exception as e:
            self._handle_pix_error(e)

    def criar_cobranca_com_vencimento(self, txid: str, dados_cobranca: dict) -> dict:
        """Cria uma cobrança PIX com vencimento (COBV)

        Args:
            txid: Identificador único da transação
            dados_cobranca: Dados da cobrança incluindo vencimento

        Returns:
            dict: Resposta da API com os dados da cobrança criada

        Raises:
            PixError: Erro genérico na operação
        """
        try:
            return self._pix_api.criar_cobv(txid, dados_cobranca)
        except Exception as e:
            self._handle_pix_error(e)

    def consultar_cobranca_com_vencimento(self, txid: str) -> dict:
        """Consulta uma cobrança PIX com vencimento

        Args:
            txid: Identificador único da transação

        Returns:
            dict: Dados da cobrança

        Raises:
            CobrancaPixNaoEncontradaError: Cobrança não encontrada
            PixError: Erro genérico na operação
        """
        try:
            return self._pix_api.consultar_cobv(txid, 0)  # revisao=0 por padrão
        except Exception as e:
            self._handle_pix_error(e)

    def listar_cobrancas(self, inicio: str, fim: str, **filtros) -> dict:
        """Lista cobranças PIX em um período

        Args:
            inicio: Data/hora de início (ISO 8601)
            fim: Data/hora de fim (ISO 8601)
            **filtros: Filtros adicionais (cpf, cnpj, status, etc)

        Returns:
            dict: Lista de cobranças

        Raises:
            PixError: Erro genérico na operação
        """
        try:
            return self._pix_api.listar_cob(inicio, fim, **filtros)
        except Exception as e:
            self._handle_pix_error(e)

    def criar_lote_cobranca(self, id_lote: int, dados_lote: dict) -> dict:
        """Cria um lote de cobranças PIX

        Args:
            id_lote: Identificador do lote
            dados_lote: Dados do lote de cobranças

        Returns:
            dict: Resposta da API com os dados do lote criado

        Raises:
            PixError: Erro genérico na operação
        """
        try:
            return self._pix_api.criar_lotecobv(id_lote, dados_lote)
        except Exception as e:
            self._handle_pix_error(e)

    def consultar_lote_cobranca(self, id_lote: int) -> dict:
        """Consulta um lote de cobranças PIX

        Args:
            id_lote: Identificador do lote

        Returns:
            dict: Dados do lote

        Raises:
            PixError: Erro genérico na operação
        """
        try:
            return self._pix_api.consultar_lotecobv(id_lote)
        except Exception as e:
            self._handle_pix_error(e)

    def cadastrar_webhook(self, chave_pix: str, url_webhook: str) -> dict:
        """Cadastra um webhook PIX

        Args:
            chave_pix: Chave PIX para receber notificações
            url_webhook: URL para receber as notificações

        Returns:
            dict: Dados do webhook cadastrado

        Raises:
            PixError: Erro genérico na operação
        """
        try:
            return self._pix_api.configurar_webhook(chave_pix, url_webhook)
        except Exception as e:
            self._handle_pix_error(e)

    def consultar_webhook(self, chave_pix: str) -> dict:
        """Consulta um webhook PIX

        Args:
            chave_pix: Chave PIX do webhook

        Returns:
            dict: Dados do webhook

        Raises:
            WebhookPixNaoEncontradoError: Webhook não encontrado
            PixError: Erro genérico na operação
        """
        try:
            return self._pix_api.consultar_webhook(chave_pix)
        except Exception as e:
            self._handle_pix_error(e)

    def excluir_webhook(self, chave_pix: str) -> None:
        """Exclui um webhook PIX

        Args:
            chave_pix: Chave PIX do webhook

        Raises:
            WebhookPixNaoEncontradoError: Webhook não encontrado
            PixError: Erro genérico na operação
        """
        try:
            self._pix_api.excluir_webhook(chave_pix)
        except Exception as e:
            self._handle_pix_error(e)

    def _handle_pix_error(self, error: Exception) -> None:
        """Trata erros da API PIX de forma padronizada

        Args:
            error: Exceção capturada

        Raises:
            CobrancaPixNaoEncontradaError: Cobrança não encontrada
            WebhookPixNaoEncontradoError: Webhook não encontrado
            PixError: Erro genérico
        """
        # Repassa exceções específicas do domínio
        if isinstance(
            error, (CobrancaPixNaoEncontradaError, WebhookPixNaoEncontradoError)
        ):
            raise error

        # Converte outras exceções em PixError genérico
        raise PixError(f'Erro na operação PIX: {error!s}') from error


class SicoobPixAPICustom(SicoobPixAPI):
    """Customização da API PIX do Sicoob para tratamento de erros"""

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

        type_ = error_data.get('type', '')
        title = error_data.get('title', '')
        status = error_data.get('status', status_code)
        detail = error_data.get('detail', '')

        # Verifica se é uma exceção de domínio específica
        if status == 404:
            if 'Cobrança' in title or 'cobranca' in detail.lower():
                raise CobrancaPixNaoEncontradaError(detail or title)
            elif 'Webhook' in title or 'webhook' in detail.lower():
                raise WebhookPixNaoEncontradoError(detail or title)

        # Para outros erros, lança PixError genérico com detalhes
        error_msg = detail or title or f'Erro {status}: {type_}'
        raise PixError(error_msg)
