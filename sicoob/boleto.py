from typing import Dict, Optional
import requests
from .api_client import APIClientBase
from .exceptions import (
    BoletoEmissaoError,
    BoletoConsultaError,
    BoletoNaoEncontradoError
)


class BoletoAPI(APIClientBase):
    """Implementação da API de Boletos Bancários do Sicoob

    Exemplo de uso:
        >>> from sicoob.auth import OAuth2Client
        >>> from sicoob.boleto import BoletoAPI
        >>> import requests
        >>>
        >>> oauth = OAuth2Client(client_id, client_secret)
        >>> session = requests.Session()
        >>> boleto_api = BoletoAPI(oauth, session)
        >>>
        >>> dados = {
        ...     "numeroContrato": 123456,
        ...     "modalidade": 1,
        ...     "valor": 100.50,
        ...     # ... outros campos obrigatórios
        ... }
        >>> boleto = boleto_api.emitir_boleto(dados)
    """

    def emitir_boleto(self, dados_boleto: Dict) -> Dict:
        """Emite um novo boleto bancário

        Args:
            dados_boleto: Dicionário com dados do boleto conforme especificação da API

        Returns:
            Resposta da API com dados do boleto emitido

        Raises:
            Exception: Em caso de falha na requisição
        """
        try:
            url = f"{self._get_base_url()}/cobranca-bancaria/v3/boletos"
            headers = self._get_headers(scope="boletos_inclusao")
            response = self.session.post(url, json=dados_boleto, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoEmissaoError(
                    f"Falha na emissão do boleto - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    dados_boleto=dados_boleto
                )
            raise BoletoEmissaoError(
                f"Falha na comunicação com API de boletos: {str(e)}",
                dados_boleto=dados_boleto
            )

    def consultar_boleto(self, nosso_numero: str) -> Optional[Dict]:
        """Consulta um boleto existente pelo nosso número

        Args:
            nosso_numero: Número identificador do boleto

        Returns:
            Dados do boleto ou None se não encontrado
        """
        try:
            url = f"{self._get_base_url()}/cobranca-bancaria/v3/boletos/{nosso_numero}"
            headers = self._get_headers(scope="boletos_consulta")
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                if e.response.status_code == 404:
                    raise BoletoNaoEncontradoError(nosso_numero)
                raise BoletoConsultaError(
                    f"Falha na consulta do boleto - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    nosso_numero=nosso_numero
                )
            raise BoletoConsultaError(
                f"Falha na comunicação com API de boletos: {str(e)}",
                nosso_numero=nosso_numero
            )
