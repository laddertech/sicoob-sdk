"""Módulo PIX do SDK Sicoob

Este módulo atua como uma ponte (thin wrapper) entre o SDK Sicoob e a
biblioteca pypix-api, que implementa o padrão PIX do BACEN.

Arquitetura:
    - pypix-api: Implementação genérica do PIX (padrão BACEN)
    - sicoob-sdk: Funcionalidades específicas do Sicoob

A separação permite que a pypix-api seja reutilizada por outros bancos,
enquanto o sicoob-sdk foca nas particularidades do Banco Sicoob.
"""

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
    """Interface PIX para o SDK Sicoob

    Esta classe atua como um wrapper fino sobre a pypix-api,
    delegando todas as operações PIX para a implementação genérica
    enquanto mantém consistência com a interface do SDK Sicoob.

    Responsabilidades:
        - Proxy para métodos da pypix-api
        - Tratamento de erros consistente com o SDK
        - Logging e métricas (se necessário)
        - Validações específicas do Sicoob (se necessário)
    """

    def __init__(self, oauth_client, session, sandbox_mode=False):
        """Inicializa a API PIX

        Args:
            oauth_client: Cliente OAuth2 para autenticação
            session: Sessão HTTP (mantida por compatibilidade)
            sandbox_mode: Habilita modo sandbox
        """
        super().__init__(oauth_client, session, sandbox_mode)

        # Inicializa a implementação PIX customizada do Sicoob
        self._pix_api = SicoobPixAPICustom(
            oauth=oauth_client, sandbox_mode=sandbox_mode
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy transparente para pypix-api

        Delega automaticamente qualquer método não definido
        explicitamente para a instância da pypix-api.

        Args:
            name: Nome do método/atributo

        Returns:
            Método ou atributo da pypix-api
        """
        # Delega para a implementação da pypix-api
        attr = getattr(self._pix_api, name)

        # Se for um método, encapsula com tratamento de erro
        if callable(attr):

            def wrapped_method(*args, **kwargs):
                try:
                    return attr(*args, **kwargs)
                except (CobrancaPixNaoEncontradaError, WebhookPixNaoEncontradoError):
                    # Re-lança exceções do domínio
                    raise
                except Exception as e:
                    # Converte outras exceções em PixError
                    raise PixError(f'Erro na operação PIX: {str(e)}') from e

            return wrapped_method

        return attr

    # Métodos explícitos para melhor documentação e IDE support

    def criar_cobranca_imediata(self, txid: str, dados: dict) -> dict:
        """Cria cobrança PIX imediata (COB)

        Args:
            txid: Identificador da transação
            dados: Dados da cobrança

        Returns:
            Dados da cobrança criada
        """
        return self.criar_cob(txid, dados)

    def consultar_cobranca_imediata(self, txid: str) -> dict:
        """Consulta cobrança PIX imediata

        Args:
            txid: Identificador da transação

        Returns:
            Dados da cobrança
        """
        return self.consultar_cob(txid)

    def criar_cobranca_com_vencimento(self, txid: str, dados: dict) -> dict:
        """Cria cobrança PIX com vencimento (COBV)

        Args:
            txid: Identificador da transação
            dados: Dados da cobrança com vencimento

        Returns:
            Dados da cobrança criada
        """
        return self.criar_cobv(txid, dados)

    def consultar_cobranca_com_vencimento(self, txid: str) -> dict:
        """Consulta cobrança PIX com vencimento

        Args:
            txid: Identificador da transação

        Returns:
            Dados da cobrança
        """
        return self.consultar_cobv(txid, 0)

    def cadastrar_webhook(self, chave: str, url: str) -> dict:
        """Cadastra webhook para notificações PIX

        Args:
            chave: Chave PIX
            url: URL do webhook

        Returns:
            Dados do webhook cadastrado
        """
        return self.configurar_webhook(chave, url)

    def consultar_webhook(self, chave: str) -> dict:
        """Consulta webhook cadastrado

        Args:
            chave: Chave PIX

        Returns:
            Dados do webhook
        """
        return self._pix_api.consultar_webhook(chave)

    def excluir_webhook(self, chave: str) -> None:
        """Exclui webhook cadastrado

        Args:
            chave: Chave PIX
        """
        return self._pix_api.excluir_webhook(chave)

    def listar_cobrancas(self, inicio: str, fim: str, **filtros) -> dict:
        """Lista cobranças em um período

        Args:
            inicio: Data/hora inicial (ISO 8601)
            fim: Data/hora final (ISO 8601)
            **filtros: Filtros adicionais

        Returns:
            Lista de cobranças
        """
        return self.listar_cob(inicio, fim, **filtros)

    def criar_lote_cobranca(self, id_lote: int, dados: dict) -> dict:
        """Cria lote de cobranças com vencimento

        Args:
            id_lote: ID do lote
            dados: Dados do lote

        Returns:
            Dados do lote criado
        """
        return self.criar_lotecobv(id_lote, dados)

    def consultar_lote_cobranca(self, id_lote: int) -> dict:
        """Consulta lote de cobranças

        Args:
            id_lote: ID do lote

        Returns:
            Dados do lote
        """
        return self.consultar_lotecobv(id_lote)


class SicoobPixAPICustom(SicoobPixAPI):
    """Customização da pypix-api para Sicoob

    Adiciona tratamento de erros específicos do domínio Sicoob.
    """

    def _handle_error_response(
        self, response: requests.Response, **kwargs: Any
    ) -> None:
        """Trata erros com exceções específicas do domínio

        Args:
            response: Resposta HTTP
            **kwargs: Argumentos adicionais (não utilizado)
        """
        # Respostas de sucesso não são erros
        status_code = getattr(response, 'status_code', None)
        if status_code and 200 <= status_code < 300:
            return

        try:
            error_data = response.json()
        except (ValueError, AttributeError):
            error_data = {}

        detail = error_data.get('detail', '')
        title = error_data.get('title', '')
        status = error_data.get('status', status_code)
        type_ = error_data.get('type', '')

        # Mapeia para exceções específicas do domínio
        if status == 404:
            if 'cobrança' in (detail + title).lower():
                raise CobrancaPixNaoEncontradaError(detail or title)
            elif 'webhook' in (detail + title).lower():
                raise WebhookPixNaoEncontradoError(detail or title)

        # Erro genérico
        error_msg = detail or title or f'Erro {status}: {type_}'
        raise PixError(error_msg)
