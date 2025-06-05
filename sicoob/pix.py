from typing import Dict, Optional
import requests
from .api_client import APIClientBase
from .exceptions import (
    CobrancaPixError,
    CobrancaPixNaoEncontradaError,
    CobrancaPixVencimentoError,
    WebhookPixError,
    LoteCobrancaPixError,
    QrCodePixError
)


class PixAPI(APIClientBase):
    """Implementação da API de Cobrança PIX do Sicoob

    Exemplo de uso:
        >>> from sicoob.auth import OAuth2Client
        >>> from sicoob.pix import PixAPI
        >>> import requests
        >>>
        >>> oauth = OAuth2Client(client_id, client_secret)
        >>> session = requests.Session()
        >>> pix_api = PixAPI(oauth, session)
        >>>
        >>> txid = "123e4567-e89b-12d3-a456-426614174000"
        >>> dados = {
        ...     "calendario": {"expiracao": 3600},
        ...     "valor": {"original": "100.50"},
        ...     "chave": "12345678901",
        ...     # ... outros campos obrigatórios
        ... }
        >>> cobranca = pix_api.criar_cobranca_pix(txid, dados)
    """

    def criar_cobranca_pix(self, txid: str, dados_cobranca: Dict) -> Dict:
        """Cria uma cobrança imediata via PIX

        Args:
            txid: Identificador único da transação (obrigatório)
            dados_cobranca: Dicionário com dados da cobrança PIX conforme especificação da API

        Returns:
            Resposta da API com dados da cobrança PIX criada

        Raises:
            CobrancaPixError: Em caso de falha na criação da cobrança PIX
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/cob/{txid}"
            headers = self._get_headers(scope="cob.write")
            response = self.session.put(url, json=dados_cobranca, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise CobrancaPixError(
                    f"Falha na criação de cobrança PIX - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    txid=txid
                )
            raise CobrancaPixError(
                f"Falha na comunicação com API PIX: {str(e)}",
                txid=txid
            )

    def consultar_cobranca_pix(self, txid: str) -> Optional[Dict]:
        """Consulta uma cobrança PIX existente pelo txid

        Args:
            txid: Identificador único da cobrança PIX

        Returns:
            Dados da cobrança PIX ou None se não encontrada
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/cob/{txid}"
            headers = self._get_headers(scope="cob.read")
            response = self.session.get(url, headers=headers)

            if response.status_code == 404:
                raise CobrancaPixNaoEncontradaError(txid)

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise CobrancaPixError(
                    f"Falha na consulta de cobrança PIX - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    txid=txid
                )
            raise CobrancaPixError(
                f"Falha na comunicação com API PIX: {str(e)}",
                txid=txid
            )

    def cancelar_cobranca_pix(self, txid: str) -> bool:
        """Cancela uma cobrança PIX existente

        Args:
            txid: Identificador único da cobrança PIX

        Returns:
            True se cancelada com sucesso, False caso contrário

        Raises:
            Exception: Em caso de falha na requisição
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/cob/{txid}"
            headers = self._get_headers(scope="cob.write")
            response = self.session.delete(url, headers=headers)

            if response.status_code == 404:
                raise CobrancaPixNaoEncontradaError(txid)

            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise CobrancaPixError(
                    f"Falha no cancelamento de cobrança PIX - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    txid=txid
                )
            raise CobrancaPixError(
                f"Falha na comunicação com API PIX: {str(e)}",
                txid=txid
            )

    def obter_qrcode_pix(self, txid: str) -> Dict:
        """Obtém a imagem QR Code de uma cobrança PIX existente

        Args:
            txid: Identificador único da cobrança PIX

        Returns:
            Dicionário contendo os dados do QR Code (incluindo imagem em base64)

        Raises:
            Exception: Em caso de falha na requisição
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/cob/{txid}/qrcode"
            headers = self._get_headers(scope="cob.read")
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise QrCodePixError(
                    f"Falha ao obter QR Code - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    txid=txid
                )
            raise QrCodePixError(
                f"Falha na comunicação com API PIX: {str(e)}",
                txid=txid
            )

    def criar_cobranca_pix_com_vencimento(
        self, txid: str, dados_cobranca: Dict
    ) -> Dict:
        """Cria uma cobrança com vencimento via PIX (CobV)

        Args:
            txid: Identificador único da transação (obrigatório)
            dados_cobranca: Dicionário com dados da cobrança PIX com vencimento

        Returns:
            Resposta da API com dados da cobrança PIX criada

        Raises:
            CobrancaPixVencimentoError: Em caso de falha na criação da cobrança PIX com vencimento
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/cobv/{txid}"
            headers = self._get_headers(scope="cobv.write")
            response = self.session.put(url, json=dados_cobranca, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise CobrancaPixVencimentoError(
                    f"Falha na criação de cobrança PIX com vencimento - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    txid=txid
                )
            raise CobrancaPixVencimentoError(
                f"Falha na comunicação com API PIX: {str(e)}",
                txid=txid
            )

    def consultar_cobranca_pix_com_vencimento(self, txid: str) -> Optional[Dict]:
        """Consulta uma cobrança PIX com vencimento existente pelo txid

        Args:
            txid: Identificador único da cobrança PIX

        Returns:
            Dados da cobrança PIX ou None se não encontrada
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/cobv/{txid}"
            headers = self._get_headers(scope="cobv.read")
            response = self.session.get(url, headers=headers)

            if response.status_code == 404:
                raise CobrancaPixNaoEncontradaError(txid)

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise CobrancaPixVencimentoError(
                    f"Falha na consulta de cobrança PIX com vencimento - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    txid=txid
                )
            raise CobrancaPixVencimentoError(
                f"Falha na comunicação com API PIX: {str(e)}",
                txid=txid
            )

    def cancelar_cobranca_pix_com_vencimento(self, txid: str) -> bool:
        """Cancela uma cobrança PIX com vencimento existente

        Args:
            txid: Identificador único da cobrança PIX

        Returns:
            True se cancelada com sucesso, False caso contrário

        Raises:
            Exception: Em caso de falha na requisição
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/cobv/{txid}"
            headers = self._get_headers(scope="cobv.write")
            response = self.session.delete(url, headers=headers)

            if response.status_code == 404:
                raise CobrancaPixNaoEncontradaError(txid)

            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise CobrancaPixVencimentoError(
                    f"Falha no cancelamento de cobrança PIX com vencimento - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    txid=txid
                )
            raise CobrancaPixVencimentoError(
                f"Falha na comunicação com API PIX: {str(e)}",
                txid=txid
            )

    def obter_qrcode_pix_com_vencimento(self, txid: str) -> Dict:
        """Obtém a imagem QR Code de uma cobrança PIX com vencimento existente

        Args:
            txid: Identificador único da cobrança PIX

        Returns:
            Dicionário contendo os dados do QR Code (incluindo imagem em base64)

        Raises:
            Exception: Em caso de falha na requisição
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/cobv/{txid}/qrcode"
            headers = self._get_headers(scope="cobv.read")
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise QrCodePixError(
                    f"Falha ao obter QR Code de cobrança com vencimento - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    txid=txid
                )
            raise QrCodePixError(
                f"Falha na comunicação com API PIX: {str(e)}",
                txid=txid
            )

    def configurar_webhook_pix(self, chave: str, webhook_url: str) -> Dict:
        """Configura um webhook para receber notificações de recebimento PIX

        Args:
            chave: Chave PIX (CPF/CNPJ/Telefone/Email/Chave Aleatória)
            webhook_url: URL que receberá as notificações

        Returns:
            Dicionário com resposta da API

        Raises:
            WebhookPixError: Em caso de falha na configuração do webhook
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/webhook/{chave}"
            headers = self._get_headers(scope="webhook.write")
            payload = {"webhookUrl": webhook_url}
            response = self.session.put(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise WebhookPixError(
                    f"Falha ao configurar webhook PIX - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    chave=chave
                )
            raise WebhookPixError(
                f"Falha na comunicação com API PIX: {str(e)}",
                chave=chave
            )

    def consultar_webhook_pix(self, chave: str) -> Optional[Dict]:
        """Consulta a configuração de webhook para uma chave PIX

        Args:
            chave: Chave PIX (CPF/CNPJ/Telefone/Email/Chave Aleatória)

        Returns:
            Dicionário com configuração do webhook ou None se não encontrado

        Raises:
            WebhookPixError: Em caso de falha na consulta do webhook
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/webhook/{chave}"
            headers = self._get_headers(scope="webhook.read")
            response = self.session.get(url, headers=headers)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise WebhookPixError(
                    f"Falha ao consultar webhook PIX - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    chave=chave
                )
            raise WebhookPixError(
                f"Falha na comunicação com API PIX: {str(e)}",
                chave=chave
            )

    def excluir_webhook_pix(self, chave: str) -> bool:
        """Remove a configuração de webhook para uma chave PIX

        Args:
            chave: Chave PIX (CPF/CNPJ/Telefone/Email/Chave Aleatória)

        Returns:
            True se removido com sucesso, False caso contrário

        Raises:
            WebhookPixError: Em caso de falha na exclusão do webhook
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/webhook/{chave}"
            headers = self._get_headers(scope="webhook.write")
            response = self.session.delete(url, headers=headers)

            if response.status_code == 404:
                return False

            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise WebhookPixError(
                    f"Falha ao excluir webhook PIX - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    chave=chave
                )
            raise WebhookPixError(
                f"Falha na comunicação com API PIX: {str(e)}",
                chave=chave
            )

    def criar_lote_cobranca_pix_com_vencimento(
        self, id_lote: str, cobrancas: list
    ) -> Dict:
        """Cria um lote de cobranças PIX com vencimento

        Args:
            id_lote: Identificador único do lote
            cobrancas: Lista de dicionários com dados das cobranças PIX com vencimento

        Returns:
            Resposta da API com dados do lote criado

        Raises:
            LoteCobrancaPixError: Em caso de falha na criação do lote
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/lotecobv/{id_lote}"
            headers = self._get_headers(scope="lotecobv.write")
            payload = {"cobrancas": cobrancas}
            response = self.session.put(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise LoteCobrancaPixError(
                    f"Falha na criação de lote de cobranças PIX - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    id_lote=id_lote
                )
            raise LoteCobrancaPixError(
                f"Falha na comunicação com API PIX: {str(e)}",
                id_lote=id_lote
            )

    def consultar_lote_cobranca_pix_com_vencimento(
        self, id_lote: str
    ) -> Optional[Dict]:
        """Consulta o status de um lote de cobranças PIX com vencimento

        Args:
            id_lote: Identificador único do lote

        Returns:
            Dados do lote ou None se não encontrado

        Raises:
            LoteCobrancaPixError: Em caso de falha na consulta do lote
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/lotecobv/{id_lote}"
            headers = self._get_headers(scope="lotecobv.read")
            response = self.session.get(url, headers=headers)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise LoteCobrancaPixError(
                    f"Falha na consulta de lote de cobranças PIX - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    id_lote=id_lote
                )
            raise LoteCobrancaPixError(
                f"Falha na comunicação com API PIX: {str(e)}",
                id_lote=id_lote
            )
