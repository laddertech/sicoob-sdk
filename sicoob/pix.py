import requests

from sicoob.api_client import APIClientBase
from sicoob.exceptions import (
    CobrancaPixError,
    CobrancaPixNaoEncontradaError,
    CobrancaPixVencimentoError,
    LoteCobrancaPixError,
    QrCodePixError,
    WebhookPixError,
    WebhookPixNaoEncontradoError,
)


class PixAPI(APIClientBase):
    """Implementação da API de Cobrança PIX do Sicoob"""

    def _handle_error_response(
        self, response: requests.Response, error_class: type, **kwargs
    ) -> None:
        """Trata respostas de erro da API de forma centralizada

        Args:
            response: Objeto Response da requisição
            error_class: Classe de exceção a ser lançada
            **kwargs: Argumentos adicionais para a exceção

        Raises:
            Exceção do tipo error_class com mensagens formatadas
        """
        if response.status_code in (400, 406, 500):
            error_data = response.json()
            mensagens = error_data.get(
                'mensagens',
                [
                    {
                        'mensagem': 'Erro desconhecido',
                        'codigo': str(response.status_code),
                    }
                ],
            )
            raise error_class(
                message=mensagens[0]['mensagem'],
                code=response.status_code,
                mensagens=mensagens,
                **kwargs,
            )
        response.raise_for_status()

    def criar_cobranca_pix(self, txid: str, dados_cobranca: dict) -> dict:
        """Cria uma cobrança imediata via PIX"""
        try:
            url = f'{self._get_base_url()}/pix/api/v2/cob/{txid}'
            headers = self._get_headers(scope='cob.write pix.write')
            response = self.session.put(url, json=dados_cobranca, headers=headers)

            try:
                self._handle_error_response(response, CobrancaPixError, txid=txid)
            except CobrancaPixError:
                raise  # Re-raise se já foi tratado como erro 400/406/500

            return self._validate_response(response)
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                try:
                    self._handle_error_response(e.response, CobrancaPixError, txid=txid)
                except CobrancaPixError:
                    raise  # Re-raise se já foi tratado como erro 400/406/500
                raise CobrancaPixError(
                    f'Falha na criação de cobrança PIX - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    txid=txid,
                ) from e
            raise CobrancaPixError(f'Erro ao criar cobrança PIX: {e}', txid=txid) from e
        except Exception as e:
            raise CobrancaPixError(f'Erro ao criar cobrança PIX: {e}', txid=txid) from e

    def consultar_cobranca_pix(self, txid: str) -> dict:
        """Consulta uma cobrança PIX existente"""
        try:
            url = f'{self._get_base_url()}/pix/api/v2/cob/{txid}'
            headers = self._get_headers(scope='cob.read')
            response = self.session.get(url, headers=headers)

            if response.status_code == 404:
                raise CobrancaPixNaoEncontradaError(txid)

            try:
                self._handle_error_response(response, CobrancaPixError, txid=txid)
            except CobrancaPixError:
                raise  # Re-raise se já foi tratado como erro 400/406/500

            return self._validate_response(response)
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                if e.response.status_code == 404:
                    raise CobrancaPixNaoEncontradaError(txid) from e
                try:
                    self._handle_error_response(e.response, CobrancaPixError, txid=txid)
                except CobrancaPixError:
                    raise  # Re-raise se já foi tratado como erro 400/406/500
                raise CobrancaPixError(
                    f'Falha na consulta de cobrança PIX - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    txid=txid,
                ) from e
            raise CobrancaPixError(
                f'Erro ao consultar cobrança PIX: {e}', txid=txid
            ) from e
        except Exception as e:
            if isinstance(e, CobrancaPixNaoEncontradaError):
                raise  # Re-raise the CobrancaPixNaoEncontradaError
            raise CobrancaPixError(
                f'Erro ao consultar cobrança PIX: {e}', txid=txid
            ) from e

    def cancelar_cobranca_pix(self, txid: str) -> bool:
        """Cancela uma cobrança PIX existente"""
        try:
            url = f'{self._get_base_url()}/pix/api/v2/cob/{txid}'
            headers = self._get_headers(scope='cob.write')
            response = self.session.delete(url, headers=headers)

            if response.status_code == 404:
                raise CobrancaPixNaoEncontradaError(txid)

            try:
                self._handle_error_response(response, CobrancaPixError, txid=txid)
            except CobrancaPixError:
                raise  # Re-raise se já foi tratado como erro 400/406/500

            return True
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                if e.response.status_code == 404:
                    raise CobrancaPixNaoEncontradaError(txid) from e
                try:
                    self._handle_error_response(e.response, CobrancaPixError, txid=txid)
                except CobrancaPixError:
                    raise  # Re-raise se já foi tratado como erro 400/406/500
                raise CobrancaPixError(
                    f'Falha no cancelamento de cobrança PIX - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    txid=txid,
                ) from e
            raise CobrancaPixError(
                f'Erro ao cancelar cobrança PIX: {e}', txid=txid
            ) from e
        except Exception as e:
            if isinstance(e, CobrancaPixNaoEncontradaError):
                raise  # Re-raise the CobrancaPixNaoEncontradaError
            raise CobrancaPixError(
                f'Erro ao cancelar cobrança PIX: {e}', txid=txid
            ) from e

    def obter_qrcode_pix(self, txid: str) -> dict:
        """Obtém o QR Code de uma cobrança PIX"""
        try:
            url = f'{self._get_base_url()}/pix/api/v2/cob/{txid}/qrcode'
            headers = self._get_headers(scope='cob.read')
            response = self.session.get(url, headers=headers)

            if response.status_code == 404:
                raise CobrancaPixNaoEncontradaError(txid)

            response.raise_for_status()
            return self._validate_response(response)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise CobrancaPixNaoEncontradaError(txid) from e
            raise QrCodePixError(
                f'Falha ao obter QR Code - Status: {e.response.status_code}',
                code=e.response.status_code,
                txid=txid,
            ) from e
        except Exception as e:
            raise QrCodePixError(f'Erro ao obter QR Code: {e}', txid=txid) from e

    def criar_cobranca_pix_com_vencimento(
        self, txid: str, dados_cobranca: dict
    ) -> dict:
        """Cria uma cobrança PIX com vencimento

        Args:
            txid: Identificador único da cobrança
            dados_cobranca: Dicionário com dados da cobrança

        Returns:
            Dados da cobrança criada

        Raises:
            CobrancaPixVencimentoError: Em caso de falha na requisição com status 400, 406 ou 500
        """
        try:
            url = f'{self._get_base_url()}/pix/api/v2/cobv/{txid}'
            headers = self._get_headers(scope='cobv.write')
            response = self.session.put(url, json=dados_cobranca, headers=headers)

            try:
                self._handle_error_response(
                    response, CobrancaPixVencimentoError, txid=txid
                )
            except CobrancaPixVencimentoError:
                raise  # Re-raise se já foi tratado como erro 400/406/500

            return self._validate_response(response)
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                try:
                    self._handle_error_response(
                        e.response, CobrancaPixVencimentoError, txid=txid
                    )
                except CobrancaPixVencimentoError:
                    raise  # Re-raise se já foi tratado como erro 400/406/500
                raise CobrancaPixVencimentoError(
                    f'Falha na criação de cobrança PIX com vencimento - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    txid=txid,
                ) from e
            raise CobrancaPixVencimentoError(
                f'Erro ao criar cobrança PIX com vencimento: {e}', txid=txid
            ) from e
        except Exception as e:
            raise CobrancaPixVencimentoError(
                f'Erro ao criar cobrança PIX com vencimento: {e}', txid=txid
            ) from e

    def consultar_cobranca_pix_com_vencimento(self, txid: str) -> dict:
        """Consulta uma cobrança PIX com vencimento"""
        try:
            url = f'{self._get_base_url()}/pix/api/v2/cobv/{txid}'
            headers = self._get_headers(scope='cobv.read')
            response = self.session.get(url, headers=headers)

            if response.status_code == 404:
                raise CobrancaPixNaoEncontradaError(txid)

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise  # Re-raise the CobrancaPixNaoEncontradaError
            raise CobrancaPixVencimentoError(
                f'Falha na consulta de cobrança PIX com vencimento - Status: {e.response.status_code}',
                code=e.response.status_code,
                txid=txid,
            ) from e
        except Exception as e:
            if isinstance(e, CobrancaPixNaoEncontradaError):
                raise  # Re-raise the CobrancaPixNaoEncontradaError
            raise CobrancaPixVencimentoError(
                f'Erro ao consultar cobrança PIX com vencimento: {e}', txid=txid
            ) from e

    def cancelar_cobranca_pix_com_vencimento(self, txid: str) -> bool:
        """Cancela uma cobrança PIX com vencimento"""
        try:
            url = f'{self._get_base_url()}/pix/api/v2/cobv/{txid}'
            headers = self._get_headers(scope='cobv.write')
            response = self.session.delete(url, headers=headers)

            if response.status_code == 404:
                raise CobrancaPixNaoEncontradaError(txid)

            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise  # Re-raise the CobrancaPixNaoEncontradaError
            raise CobrancaPixVencimentoError(
                f'Falha no cancelamento de cobrança PIX com vencimento - Status: {e.response.status_code}',
                code=e.response.status_code,
                txid=txid,
            ) from e
        except Exception as e:
            if isinstance(e, CobrancaPixNaoEncontradaError):
                raise  # Re-raise the CobrancaPixNaoEncontradaError
            raise CobrancaPixVencimentoError(
                f'Erro ao cancelar cobrança PIX com vencimento: {e}', txid=txid
            ) from e

    def obter_qrcode_pix_com_vencimento(self, txid: str) -> dict:
        """Obtém o QR Code de uma cobrança PIX com vencimento"""
        try:
            url = f'{self._get_base_url()}/pix/api/v2/cobv/{txid}/qrcode'
            headers = self._get_headers(scope='cobv.read')
            response = self.session.get(url, headers=headers)

            if response.status_code == 404:
                raise CobrancaPixNaoEncontradaError(txid)

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise CobrancaPixNaoEncontradaError(txid) from e
            raise QrCodePixError(
                f'Falha ao obter QR Code de cobrança com vencimento - Status: {e.response.status_code}',
                code=e.response.status_code,
                txid=txid,
            ) from e
        except Exception as e:
            raise QrCodePixError(
                f'Erro ao obter QR Code de cobrança com vencimento: {e}', txid=txid
            ) from e

    def configurar_webhook_pix(self, chave: str, webhook_url: str) -> dict:
        """Configura um webhook para notificações PIX

        Args:
            chave: Chave PIX associada ao webhook
            webhook_url: URL que receberá as notificações

        Returns:
            Dados da configuração do webhook

        Raises:
            WebhookPixError: Em caso de falha na requisição com status 400, 406 ou 500
        """
        try:
            url = f'{self._get_base_url()}/pix/api/v2/webhook/{chave}'
            headers = self._get_headers(scope='webhook.write')
            payload = {'webhookUrl': webhook_url}
            response = self.session.put(url, json=payload, headers=headers)

            try:
                self._handle_error_response(response, WebhookPixError, chave=chave)
            except WebhookPixError:
                raise  # Re-raise se já foi tratado como erro 400/406/500

            return self._validate_response(response)
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                try:
                    self._handle_error_response(
                        e.response, WebhookPixError, chave=chave
                    )
                except WebhookPixError:
                    raise  # Re-raise se já foi tratado como erro 400/406/500
                raise WebhookPixError(
                    f'Falha ao configurar webhook PIX - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    chave=chave,
                ) from e
            raise WebhookPixError(
                f'Erro ao configurar webhook PIX: {e}', chave=chave
            ) from e
        except Exception as e:
            raise WebhookPixError(
                f'Erro ao configurar webhook PIX: {e}', chave=chave
            ) from e

    def consultar_webhook_pix(self, chave: str) -> dict:
        """Consulta a configuração de um webhook PIX

        Args:
            chave: Chave PIX associada ao webhook

        Returns:
            Dados da configuração do webhook

        Raises:
            WebhookPixNaoEncontradoError: Se o webhook não for encontrado (status 404)
            WebhookPixError: Em caso de falha na requisição com status 400, 406 ou 500
        """
        try:
            url = f'{self._get_base_url()}/pix/api/v2/webhook/{chave}'
            headers = self._get_headers(scope='webhook.read')
            response = self.session.get(url, headers=headers)

            # Trata 404 como WebhookPixNaoEncontradoError
            if response.status_code == 404:
                raise WebhookPixNaoEncontradoError(chave)

            try:
                self._handle_error_response(response, WebhookPixError, chave=chave)
            except WebhookPixError:
                raise  # Re-raise se já foi tratado como erro 400/406/500

            return self._validate_response(response)
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                if e.response.status_code == 404:
                    raise WebhookPixNaoEncontradoError(chave) from e
                try:
                    self._handle_error_response(
                        e.response, WebhookPixError, chave=chave
                    )
                except WebhookPixError:
                    raise  # Re-raise se já foi tratado como erro 400/406/500
                raise WebhookPixError(
                    f'Falha ao consultar webhook PIX - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    chave=chave,
                ) from e
            raise WebhookPixError(
                f'Erro ao consultar webhook PIX: {e}', chave=chave
            ) from e
        except Exception as e:
            if isinstance(e, WebhookPixNaoEncontradoError):
                raise  # Re-raise the WebhookPixNaoEncontradoError
            raise WebhookPixError(
                f'Erro ao consultar webhook PIX: {e}', chave=chave
            ) from e

    def excluir_webhook_pix(self, chave: str) -> bool:
        """Remove a configuração de um webhook PIX

        Args:
            chave: Chave PIX associada ao webhook

        Returns:
            True se a exclusão foi bem sucedida

        Raises:
            WebhookPixNaoEncontradoError: Se o webhook não for encontrado (status 404)
            WebhookPixError: Em caso de falha na requisição com status 400, 406 ou 500
        """
        try:
            url = f'{self._get_base_url()}/pix/api/v2/webhook/{chave}'
            headers = self._get_headers(scope='webhook.write')
            response = self.session.delete(url, headers=headers)

            # Trata 404 como WebhookPixNaoEncontradoError
            if response.status_code == 404:
                raise WebhookPixNaoEncontradoError(chave)

            try:
                self._handle_error_response(response, WebhookPixError, chave=chave)
            except WebhookPixError:
                raise  # Re-raise se já foi tratado como erro 400/406/500

            return True
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                if e.response.status_code == 404:
                    raise WebhookPixNaoEncontradoError(chave) from e
                try:
                    self._handle_error_response(
                        e.response, WebhookPixError, chave=chave
                    )
                except WebhookPixError:
                    raise  # Re-raise se já foi tratado como erro 400/406/500
                raise WebhookPixError(
                    f'Falha ao excluir webhook PIX - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    chave=chave,
                ) from e
            raise WebhookPixError(
                f'Erro ao excluir webhook PIX: {e}', chave=chave
            ) from e
        except Exception as e:
            if isinstance(e, WebhookPixNaoEncontradoError):
                raise  # Re-raise the WebhookPixNaoEncontradoError
            raise WebhookPixError(
                f'Erro ao excluir webhook PIX: {e}', chave=chave
            ) from e

    def criar_lote_cobranca_pix_com_vencimento(
        self, id_lote: str, cobrancas: list[dict]
    ) -> dict:
        """Cria um lote de cobranças PIX com vencimento"""
        try:
            url = f'{self._get_base_url()}/pix/api/v2/lotecobv/{id_lote}'
            headers = self._get_headers(scope='lotecobv.write')
            payload = {'cobrancas': cobrancas}
            response = self.session.put(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            raise LoteCobrancaPixError(
                f'Falha na criação de lote de cobranças PIX - Status: {e.response.status_code}',
                code=e.response.status_code,
                id_lote=id_lote,
            ) from e
        except Exception as e:
            raise LoteCobrancaPixError(
                f'Erro ao criar lote de cobranças PIX: {e}', id_lote=id_lote
            ) from e

    def consultar_lote_cobranca_pix_com_vencimento(self, id_lote: str) -> dict:
        """Consulta um lote de cobranças PIX com vencimento"""
        try:
            url = f'{self._get_base_url()}/pix/api/v2/lotecobv/{id_lote}'
            headers = self._get_headers(scope='lotecobv.read')
            response = self.session.get(url, headers=headers)

            if response.status_code == 404:
                raise CobrancaPixNaoEncontradaError(id_lote)

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise  # Re-raise the CobrancaPixNaoEncontradaError
            raise LoteCobrancaPixError(
                f'Falha na consulta de lote de cobranças PIX - Status: {e.response.status_code}',
                code=e.response.status_code,
                id_lote=id_lote,
            ) from e
        except Exception as e:
            if isinstance(e, CobrancaPixNaoEncontradaError):
                raise  # Re-raise the CobrancaPixNaoEncontradaError
            raise LoteCobrancaPixError(
                f'Erro ao consultar lote de cobranças PIX: {e}', id_lote=id_lote
            ) from e
