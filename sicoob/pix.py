from typing import Dict, Optional
import requests
from .api_client import APIClientBase

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
            Exception: Em caso de falha na requisição
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/cob/{txid}"
            headers = self._get_headers()
            response = self.session.put(url, json=dados_cobranca, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            raise Exception(f"Erro HTTP na criação de cobrança PIX: {http_err}")
        except Exception as e:
            raise Exception(f"Erro na criação de cobrança PIX: {str(e)}")
            
    def consultar_cobranca_pix(self, txid: str) -> Optional[Dict]:
        """Consulta uma cobrança PIX existente pelo txid
        
        Args:
            txid: Identificador único da cobrança PIX
            
        Returns:
            Dados da cobrança PIX ou None se não encontrada
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/cob/{txid}"
            headers = self._get_headers()
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            raise Exception(f"Erro HTTP na consulta de cobrança PIX: {http_err}")
        except Exception as e:
            raise Exception(f"Erro na consulta de cobrança PIX: {str(e)}")
            
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
            headers = self._get_headers()
            response = self.session.delete(url, headers=headers)
            
            if response.status_code == 404:
                return False
                
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as http_err:
            raise Exception(f"Erro HTTP no cancelamento de cobrança PIX: {http_err}")
        except Exception as e:
            raise Exception(f"Erro no cancelamento de cobrança PIX: {str(e)}")

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
            headers = self._get_headers()
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            raise Exception(f"Erro HTTP ao obter QR Code: {http_err}")
        except Exception as e:
            raise Exception(f"Erro ao obter QR Code: {str(e)}")

    def criar_cobranca_pix_com_vencimento(self, txid: str, dados_cobranca: Dict) -> Dict:
        """Cria uma cobrança com vencimento via PIX (CobV)
        
        Args:
            txid: Identificador único da transação (obrigatório)
            dados_cobranca: Dicionário com dados da cobrança PIX com vencimento
            
        Returns:
            Resposta da API com dados da cobrança PIX criada
            
        Raises:
            Exception: Em caso de falha na requisição
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/cobv/{txid}"
            headers = self._get_headers()
            response = self.session.put(url, json=dados_cobranca, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            raise Exception(f"Erro HTTP na criação de cobrança PIX com vencimento: {http_err}")
        except Exception as e:
            raise Exception(f"Erro na criação de cobrança PIX com vencimento: {str(e)}")
            
    def consultar_cobranca_pix_com_vencimento(self, txid: str) -> Optional[Dict]:
        """Consulta uma cobrança PIX com vencimento existente pelo txid
        
        Args:
            txid: Identificador único da cobrança PIX
            
        Returns:
            Dados da cobrança PIX ou None se não encontrada
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/cobv/{txid}"
            headers = self._get_headers()
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            raise Exception(f"Erro HTTP na consulta de cobrança PIX com vencimento: {http_err}")
        except Exception as e:
            raise Exception(f"Erro na consulta de cobrança PIX com vencimento: {str(e)}")
            
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
            headers = self._get_headers()
            response = self.session.delete(url, headers=headers)
            
            if response.status_code == 404:
                return False
                
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as http_err:
            raise Exception(f"Erro HTTP no cancelamento de cobrança PIX com vencimento: {http_err}")
        except Exception as e:
            raise Exception(f"Erro no cancelamento de cobrança PIX com vencimento: {str(e)}")

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
            headers = self._get_headers()
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            raise Exception(f"Erro HTTP ao obter QR Code de cobrança com vencimento: {http_err}")
        except Exception as e:
            raise Exception(f"Erro ao obter QR Code de cobrança com vencimento: {str(e)}")

    def configurar_webhook_pix(self, chave: str, webhook_url: str) -> Dict:
        """Configura um webhook para receber notificações de recebimento PIX
        
        Args:
            chave: Chave PIX (CPF/CNPJ/Telefone/Email/Chave Aleatória)
            webhook_url: URL que receberá as notificações
            
        Returns:
            Dicionário com resposta da API
            
        Raises:
            Exception: Em caso de falha na requisição
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/webhook/{chave}"
            headers = self._get_headers()
            payload = {"webhookUrl": webhook_url}
            response = self.session.put(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            raise Exception(f"Erro HTTP ao configurar webhook PIX: {http_err}")
        except Exception as e:
            raise Exception(f"Erro ao configurar webhook PIX: {str(e)}")

    def consultar_webhook_pix(self, chave: str) -> Optional[Dict]:
        """Consulta a configuração de webhook para uma chave PIX
        
        Args:
            chave: Chave PIX (CPF/CNPJ/Telefone/Email/Chave Aleatória)
            
        Returns:
            Dicionário com configuração do webhook ou None se não encontrado
            
        Raises:
            Exception: Em caso de falha na requisição
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/webhook/{chave}"
            headers = self._get_headers()
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            raise Exception(f"Erro HTTP ao consultar webhook PIX: {http_err}")
        except Exception as e:
            raise Exception(f"Erro ao consultar webhook PIX: {str(e)}")

    def excluir_webhook_pix(self, chave: str) -> bool:
        """Remove a configuração de webhook para uma chave PIX
        
        Args:
            chave: Chave PIX (CPF/CNPJ/Telefone/Email/Chave Aleatória)
            
        Returns:
            True se removido com sucesso, False caso contrário
            
        Raises:
            Exception: Em caso de falha na requisição
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/webhook/{chave}"
            headers = self._get_headers()
            response = self.session.delete(url, headers=headers)
            
            if response.status_code == 404:
                return False
                
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as http_err:
            raise Exception(f"Erro HTTP ao excluir webhook PIX: {http_err}")
        except Exception as e:
            raise Exception(f"Erro ao excluir webhook PIX: {str(e)}")

    def criar_lote_cobranca_pix_com_vencimento(self, id_lote: str, cobrancas: list) -> Dict:
        """Cria um lote de cobranças PIX com vencimento
        
        Args:
            id_lote: Identificador único do lote
            cobrancas: Lista de dicionários com dados das cobranças PIX com vencimento
            
        Returns:
            Resposta da API com dados do lote criado
            
        Raises:
            Exception: Em caso de falha na requisição
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/lotecobv/{id_lote}"
            headers = self._get_headers()
            payload = {"cobrancas": cobrancas}
            response = self.session.put(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            raise Exception(f"Erro HTTP na criação de lote de cobranças PIX com vencimento: {http_err}")
        except Exception as e:
            raise Exception(f"Erro na criação de lote de cobranças PIX com vencimento: {str(e)}")

    def consultar_lote_cobranca_pix_com_vencimento(self, id_lote: str) -> Optional[Dict]:
        """Consulta o status de um lote de cobranças PIX com vencimento
        
        Args:
            id_lote: Identificador único do lote
            
        Returns:
            Dados do lote ou None se não encontrado
            
        Raises:
            Exception: Em caso de falha na requisição
        """
        try:
            url = f"{self._get_base_url()}/pix/api/v2/lotecobv/{id_lote}"
            headers = self._get_headers()
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            raise Exception(f"Erro HTTP na consulta de lote de cobranças PIX com vencimento: {http_err}")
        except Exception as e:
            raise Exception(f"Erro na consulta de lote de cobranças PIX com vencimento: {str(e)}")
