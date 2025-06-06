from typing import Dict, Optional
import requests

from .api_client import APIClientBase
from .exceptions import (
    BoletoEmissaoError,
    BoletoConsultaError,
    BoletoConsultaPagadorError,
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
        ...     "numeroCliente": 123456,
        ...     "codigoModalidade": 1,
        ...     "numeroContaCorrente": 1234,
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
                    dados_boleto=dados_boleto,
                ) from e
            raise BoletoEmissaoError(
                f"Falha na comunicação com API de boletos: {str(e)}",
                dados_boleto=dados_boleto,
            ) from e

    def consultar_boletos_por_pagador(
        self,
        numero_cpf_cnpj: str,
        numero_cliente: int,
        client_id: str,
        codigo_situacao: Optional[int] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
    ) -> Dict:
        """Consulta lista de boletos por pagador

        Args:
            numero_cpf_cnpj: CPF ou CNPJ do pagador (máx 14 caracteres)
            numero_cliente: Número que identifica o contrato do beneficiário no Sisbr
            client_id: ClientId utilizado na utilização do TOKEN
            codigo_situacao: Código da Situação do Boleto (1-Em Aberto, 2-Baixado, 3-Liquidado)
            data_inicio: Data de Vencimento Inicial (formato yyyy-MM-dd)
            data_fim: Data de Vencimento Final (formato yyyy-MM-dd)

        Returns:
            Lista de boletos encontrados

        Raises:
            BoletoConsultaPagadorError: Em caso de falha na requisição
        """
        try:
            params = {
                "numeroCliente": numero_cliente,
            }

            if codigo_situacao:
                params["codigoSituacao"] = codigo_situacao
            if data_inicio:
                params["dataInicio"] = data_inicio
            if data_fim:
                params["dataFim"] = data_fim

            url = f"{self._get_base_url()}/cobranca-bancaria/v3/pagadores/{numero_cpf_cnpj}/boletos"
            headers = self._get_headers(scope="boletos_consulta")
            headers["client_id"] = client_id

            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoConsultaPagadorError(
                    f"Falha na consulta de boletos por pagador - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    numero_cpf_cnpj=numero_cpf_cnpj,
                ) from e
            raise BoletoConsultaPagadorError(
                f"Falha na comunicação com API de boletos: {str(e)}",
                numero_cpf_cnpj=numero_cpf_cnpj,
            ) from e

    def emitir_segunda_via(
        self,
        numero_cliente: int,
        codigo_modalidade: int,
        nosso_numero: Optional[int] = None,
        linha_digitavel: Optional[str] = None,
        codigo_barras: Optional[str] = None,
        gerar_pdf: bool = False,
        numero_contrato_cobranca: Optional[int] = None,
        client_id: Optional[str] = None,
    ) -> Dict:
        """Emite segunda via de um boleto existente

        Args:
            numero_cliente: Número que identifica o contrato do beneficiário no Sisbr
            codigo_modalidade: Identifica a modalidade do boleto (1-8)
            nosso_numero: Número identificador do boleto no Sisbr (opcional)
            linha_digitavel: Linha digitável do boleto com 47 posições (opcional)
            codigo_barras: Código de barras do boleto com 44 posições (opcional)
            gerar_pdf: Se True, retorna PDF em base64 (default: False)
            numero_contrato_cobranca: ID do contrato de cobrança (opcional)
            client_id: ClientId utilizado na utilização do TOKEN (opcional)

        Returns:
            Dados do boleto ou PDF em base64 se gerar_pdf=True

        Raises:
            ValueError: Se nenhum identificador de boleto for fornecido
            BoletoEmissaoError: Em caso de falha na requisição
        """
        try:
            params = {
                "numeroCliente": numero_cliente,
                "codigoModalidade": codigo_modalidade,
                "gerarPdf": "true" if gerar_pdf else "false"
            }

            if nosso_numero:
                params["nossoNumero"] = nosso_numero
            elif linha_digitavel:
                params["linhaDigitavel"] = linha_digitavel
            elif codigo_barras:
                params["codigoBarras"] = codigo_barras
            else:
                raise ValueError(
                    "Deve ser fornecido pelo menos um identificador de boleto "
                    "(nossoNumero, linhaDigitavel ou codigoBarras)"
                )

            if numero_contrato_cobranca:
                params["numeroContratoCobranca"] = numero_contrato_cobranca

            url = f"{self._get_base_url()}/cobranca-bancaria/v3/boletos/segunda-via"
            headers = self._get_headers(scope="boletos_inclusao")
            if client_id:
                headers["client_id"] = client_id

            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoEmissaoError(
                    f"Falha na emissão da segunda via - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    dados_boleto=params,
                ) from e
            raise BoletoEmissaoError(
                f"Falha na comunicação com API de boletos: {str(e)}",
                dados_boleto=params,
            ) from e

    def consultar_boleto(
        self,
        numero_cliente: int,
        codigo_modalidade: int,
        nosso_numero: Optional[int] = None,
        linha_digitavel: Optional[str] = None,
        codigo_barras: Optional[str] = None,
        numero_contrato_cobranca: Optional[int] = None,
        client_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """Consulta um boleto existente conforme parâmetros da API Sicoob

        Args:
            numero_cliente: Número que identifica o contrato do beneficiário no Sisbr
            codigo_modalidade: Identifica a modalidade do boleto (1-8)
            nosso_numero: Número identificador do boleto no Sisbr (opcional)
            linha_digitavel: Linha digitável do boleto com 47 posições (opcional)
            codigo_barras: Código de barras do boleto com 44 posições (opcional)
            numero_contrato_cobranca: ID do contrato de cobrança (opcional)
            client_id: ClientId utilizado na utilização do TOKEN (opcional)

        Returns:
            Dados do boleto ou None se não encontrado

        Raises:
            ValueError: Se nenhum identificador de boleto for fornecido
        """
        try:
            params = {
                "numeroCliente": numero_cliente,
                "codigoModalidade": codigo_modalidade,
            }

            if nosso_numero:
                params["nossoNumero"] = nosso_numero
            elif linha_digitavel:
                params["linhaDigitavel"] = linha_digitavel
            elif codigo_barras:
                params["codigoBarras"] = codigo_barras
            else:
                raise ValueError(
                    (
                        "Deve ser fornecido pelo menos um identificador de boleto "
                        "(nossoNumero, linhaDigitavel ou codigoBarras)"
                    )
                )

            if numero_contrato_cobranca:
                params["numeroContratoCobranca"] = numero_contrato_cobranca

            url = f"{self._get_base_url()}/cobranca-bancaria/v3/boletos"
            headers = self._get_headers(scope="boletos_consulta")
            if client_id:
                headers["client_id"] = client_id

            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                if e.response.status_code == 404:
                    return None
                raise BoletoConsultaError(
                    f"Falha na consulta do boleto - Status: {e.response.status_code}",
                    code=e.response.status_code,
                    nosso_numero=str(params.get("nossoNumero", "")),
                ) from e
            raise BoletoConsultaError(
                f"Falha na comunicação com API de boletos: {str(e)}",
                nosso_numero=str(params.get("nossoNumero", "")),
            ) from e
