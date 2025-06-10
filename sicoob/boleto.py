import requests

from .api_client import APIClientBase
from .exceptions import (
    BoletoAlteracaoError,
    BoletoAlteracaoPagadorError,
    BoletoBaixaError,
    BoletoConsultaError,
    BoletoConsultaFaixaError,
    BoletoConsultaPagadorError,
    BoletoEmissaoError,
    BoletoWebhookError,
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

    def emitir_boleto(self, dados_boleto: dict) -> dict:
        """Emite um novo boleto bancário

        Args:
            dados_boleto: Dicionário com dados do boleto conforme especificação da API

        Returns:
            Resposta da API com dados do boleto emitido

        Raises:
            Exception: Em caso de falha na requisição
        """
        try:
            url = f'{self._get_base_url()}/cobranca-bancaria/v3/boletos'
            headers = self._get_headers(scope='boletos_inclusao')
            response = self.session.post(url, json=dados_boleto, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoEmissaoError(
                    f'Falha na emissão do boleto - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    dados_boleto=dados_boleto,
                ) from e
            raise BoletoEmissaoError(
                f'Falha na comunicação com API de boletos: {e!s}',
                dados_boleto=dados_boleto,
            ) from e

    def consultar_boletos_por_pagador(
        self,
        numero_cpf_cnpj: str,
        numero_cliente: int,
        client_id: str,
        codigo_situacao: int | None = None,
        data_inicio: str | None = None,
        data_fim: str | None = None,
    ) -> dict:
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
                'numeroCliente': numero_cliente,
            }

            if codigo_situacao:
                params['codigoSituacao'] = codigo_situacao
            if data_inicio:
                params['dataInicio'] = data_inicio
            if data_fim:
                params['dataFim'] = data_fim

            url = f'{self._get_base_url()}/cobranca-bancaria/v3/pagadores/{numero_cpf_cnpj}/boletos'
            headers = self._get_headers(scope='boletos_consulta')
            headers['client_id'] = client_id

            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoConsultaPagadorError(
                    f'Falha na consulta de boletos por pagador - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    numero_cpf_cnpj=numero_cpf_cnpj,
                ) from e
            raise BoletoConsultaPagadorError(
                f'Falha na comunicação com API de boletos: {e!s}',
                numero_cpf_cnpj=numero_cpf_cnpj,
            ) from e

    def emitir_segunda_via(
        self,
        numero_cliente: int,
        codigo_modalidade: int,
        nosso_numero: int | None = None,
        linha_digitavel: str | None = None,
        codigo_barras: str | None = None,
        gerar_pdf: bool = False,
        numero_contrato_cobranca: int | None = None,
        client_id: str | None = None,
    ) -> dict:
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
                'numeroCliente': numero_cliente,
                'codigoModalidade': codigo_modalidade,
                'gerarPdf': 'true' if gerar_pdf else 'false',
            }

            if nosso_numero:
                params['nossoNumero'] = nosso_numero
            elif linha_digitavel:
                params['linhaDigitavel'] = linha_digitavel
            elif codigo_barras:
                params['codigoBarras'] = codigo_barras
            else:
                raise ValueError(
                    'Deve ser fornecido pelo menos um identificador de boleto '
                    '(nossoNumero, linhaDigitavel ou codigoBarras)'
                )

            if numero_contrato_cobranca:
                params['numeroContratoCobranca'] = numero_contrato_cobranca

            url = f'{self._get_base_url()}/cobranca-bancaria/v3/boletos/segunda-via'
            headers = self._get_headers(scope='boletos_inclusao')
            if client_id:
                headers['client_id'] = client_id

            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoEmissaoError(
                    f'Falha na emissão da segunda via - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    dados_boleto=params,
                ) from e
            raise BoletoEmissaoError(
                f'Falha na comunicação com API de boletos: {e!s}',
                dados_boleto=params,
            ) from e

    def consultar_faixas_nosso_numero(
        self,
        numero_cliente: int,
        codigo_modalidade: int,
        quantidade: int,
        client_id: str,
        numero_contrato_cobranca: int | None = None,
    ) -> dict:
        """Consulta faixas de nosso número disponíveis

        Args:
            numero_cliente: Número que identifica o contrato do beneficiário no Sisbr
            codigo_modalidade: Identifica a modalidade do boleto (1-Simples, 3-Caucionada, 4-Vinculada, 8-Conta Capital)
            quantidade: Quantidade mínima de nosso números que devem estar disponíveis
            client_id: ClientId utilizado na utilização do TOKEN
            numero_contrato_cobranca: ID do contrato de cobrança (opcional)

        Returns:
            Dicionário com as faixas de nosso número disponíveis, contendo:
            - numeroInicial: Número inicial da faixa
            - numeroFinal: Número final da faixa
            - validaDigitoVerificadorNossoNumero: Indica se deve calcular DV (0-não, 1-sim)

        Raises:
            BoletoConsultaFaixaError: Em caso de falha na requisição
        """
        try:
            params = {
                'numeroCliente': numero_cliente,
                'codigoModalidade': codigo_modalidade,
                'quantidade': quantidade,
            }

            if numero_contrato_cobranca:
                params['numeroContratoCobranca'] = numero_contrato_cobranca

            url = f'{self._get_base_url()}/cobranca-bancaria/v3/boletos/faixas-nosso-numero'
            headers = self._get_headers(scope='boletos_consulta')
            headers['client_id'] = client_id

            response = self.session.get(url, params=params, headers=headers)

            # Trata erros específicos com códigos 400, 406, 500
            if response.status_code in (400, 406, 500):
                error_data = response.json()
                raise BoletoConsultaFaixaError(
                    f'Falha na consulta de faixas: {error_data.get("mensagens", [{}])[0].get("mensagem", "Erro desconhecido")}',
                    code=response.status_code,
                    numero_cliente=numero_cliente,
                )

            response.raise_for_status()

            data = response.json()
            # Ajusta para a estrutura esperada (array resultado)
            if 'resultado' in data and len(data['resultado']) > 0:
                faixa = data['resultado'][0]
                # Converte validaDigitoVerificadorNossoNumero para int (0/1) se for boolean
                if isinstance(faixa.get('validaDigitoVerificadorNossoNumero'), bool):
                    faixa['validaDigitoVerificadorNossoNumero'] = (
                        1 if faixa['validaDigitoVerificadorNossoNumero'] else 0
                    )
                return faixa

            raise BoletoConsultaFaixaError(
                'Nenhuma faixa disponível encontrada',
                code=404,
                numero_cliente=numero_cliente,
            )
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoConsultaFaixaError(
                    f'Falha na consulta de faixas - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    numero_cliente=numero_cliente,
                ) from e
            raise BoletoConsultaFaixaError(
                f'Falha na comunicação com API de boletos: {e!s}',
                numero_cliente=numero_cliente,
            ) from e

    def consultar_boleto(
        self,
        numero_cliente: int,
        codigo_modalidade: int,
        nosso_numero: int | None = None,
        linha_digitavel: str | None = None,
        codigo_barras: str | None = None,
        numero_contrato_cobranca: int | None = None,
        client_id: str | None = None,
    ) -> dict | None:
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
                'numeroCliente': numero_cliente,
                'codigoModalidade': codigo_modalidade,
            }

            if nosso_numero:
                params['nossoNumero'] = nosso_numero
            elif linha_digitavel:
                params['linhaDigitavel'] = linha_digitavel
            elif codigo_barras:
                params['codigoBarras'] = codigo_barras
            else:
                raise ValueError(
                    'Deve ser fornecido pelo menos um identificador de boleto '
                    '(nossoNumero, linhaDigitavel ou codigoBarras)'
                )

            if numero_contrato_cobranca:
                params['numeroContratoCobranca'] = numero_contrato_cobranca

            url = f'{self._get_base_url()}/cobranca-bancaria/v3/boletos'
            headers = self._get_headers(scope='boletos_consulta')
            if client_id:
                headers['client_id'] = client_id

            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                if e.response.status_code == 404:
                    return None
                raise BoletoConsultaError(
                    f'Falha na consulta do boleto - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    nosso_numero=str(params.get('nossoNumero', '')),
                ) from e
            raise BoletoConsultaError(
                f'Falha na comunicação com API de boletos: {e!s}',
                nosso_numero=str(params.get('nossoNumero', '')),
            ) from e

    def baixar_boleto(
        self,
        nosso_numero: int,
        dados_boleto: dict,
        client_id: str,
    ) -> None:
        """Comanda a baixa de um boleto existente

        Args:
            nosso_numero: Número identificador do boleto no Sisbr
            dados_boleto: Dicionário com os dados do boleto contendo:
                - numeroCliente: Número do cliente
                - codigoModalidade: Código da modalidade
            client_id: ClientId utilizado na utilização do TOKEN

        Returns:
            None em caso de sucesso (status 204)

        Raises:
            BoletoBaixaError: Em caso de falha na requisição com status 400, 406 ou 500
        """
        try:
            url = f'{self._get_base_url()}/cobranca-bancaria/v3/boletos/{nosso_numero}/baixar'
            headers = self._get_headers(scope='boletos_baixa')
            headers['client_id'] = client_id

            response = self.session.post(url, json=dados_boleto, headers=headers)

            # Trata erros específicos com códigos 400, 406, 500
            if response.status_code in (400, 406, 500):
                error_data = response.json()
                raise BoletoBaixaError(
                    f'Falha na baixa do boleto: {error_data.get("mensagens", [{}])[0].get("mensagem", "Erro desconhecido")}',
                    code=response.status_code,
                    nosso_numero=nosso_numero,
                    dados_boleto=dados_boleto,
                )

            # Verifica se o status é 204 (No Content)
            if response.status_code != 204:
                raise BoletoBaixaError(
                    f'Resposta inesperada da API: {response.status_code}',
                    code=response.status_code,
                    nosso_numero=nosso_numero,
                    dados_boleto=dados_boleto,
                )

        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoBaixaError(
                    f'Falha na baixa do boleto - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    nosso_numero=nosso_numero,
                    dados_boleto=dados_boleto,
                ) from e
            raise BoletoBaixaError(
                f'Falha na comunicação com API de boletos: {e!s}',
                nosso_numero=nosso_numero,
                dados_boleto=dados_boleto,
            ) from e

    def alterar_boleto(
        self,
        nosso_numero: int,
        dados_alteracao: dict,
        client_id: str,
    ) -> None:
        """Altera dados de um boleto existente

        Args:
            nosso_numero: Número identificador do boleto no Sisbr
            dados_alteracao: Dicionário com os dados a serem alterados (apenas um objeto por requisição)
            client_id: ClientId utilizado na utilização do TOKEN

        Returns:
            None em caso de sucesso (status 204)

        Raises:
            BoletoAlteracaoError: Em caso de falha na requisição com status 400, 406 ou 500
        """
        try:
            url = f'{self._get_base_url()}/cobranca-bancaria/v3/boletos/{nosso_numero}'
            headers = self._get_headers(scope='boletos_alteracao')
            headers['client_id'] = client_id

            response = self.session.patch(url, json=dados_alteracao, headers=headers)

            # Trata erros específicos com códigos 400, 406, 500
            if response.status_code in (400, 406, 500):
                error_data = response.json()
                raise BoletoAlteracaoError(
                    f'Falha na alteração do boleto: {error_data.get("mensagens", [{}])[0].get("mensagem", "Erro desconhecido")}',
                    code=response.status_code,
                    nosso_numero=str(nosso_numero),
                    dados_alteracao=dados_alteracao,
                )

            # Verifica se o status é 204 (No Content)
            if response.status_code != 204:
                raise BoletoAlteracaoError(
                    f'Resposta inesperada da API: {response.status_code}',
                    code=response.status_code,
                    nosso_numero=str(nosso_numero),
                    dados_alteracao=dados_alteracao,
                )

        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoAlteracaoError(
                    f'Falha na alteração do boleto - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    nosso_numero=str(nosso_numero),
                    dados_alteracao=dados_alteracao,
                ) from e
            raise BoletoAlteracaoError(
                f'Falha na comunicação com API de boletos: {e!s}',
                nosso_numero=str(nosso_numero),
                dados_alteracao=dados_alteracao,
            ) from e

    def alterar_pagador(
        self,
        pagador: dict,
        client_id: str,
    ) -> None:
        """Altera informações do cadastro do pagador

        Args:
            pagador: Dicionário com os dados do pagador contendo:
                - numeroCliente: Número do cliente
                - numeroCpfCnpj: CPF/CNPJ do pagador
                - nome: Nome do pagador
                - endereco: Endereço completo
                - bairro: Bairro
                - cidade: Cidade
                - cep: CEP
                - uf: UF (sigla do estado)
                - email: Email do pagador
            client_id: ClientId utilizado na utilização do TOKEN

        Returns:
            None em caso de sucesso (status 204)

        Raises:
            BoletoAlteracaoPagadorError: Em caso de falha na requisição com status 400, 406 ou 500
        """
        try:
            url = f'{self._get_base_url()}/cobranca-bancaria/v3/pagadores'
            headers = self._get_headers(scope='boletos_alteracao')
            headers['client_id'] = client_id

            response = self.session.put(url, json=pagador, headers=headers)

            # Trata erros específicos com códigos 400, 406, 500
            if response.status_code in (400, 406, 500):
                error_data = response.json()
                raise BoletoAlteracaoPagadorError(
                    f'Falha na alteração do pagador: {error_data.get("mensagens", [{}])[0].get("mensagem", "Erro desconhecido")}',
                    code=response.status_code,
                    numero_cpf_cnpj=pagador.get('numeroCpfCnpj'),
                    dados_pagador=pagador,
                )

            # Verifica se o status é 204 (No Content)
            if response.status_code != 204:
                raise BoletoAlteracaoPagadorError(
                    f'Resposta inesperada da API: {response.status_code}',
                    code=response.status_code,
                    numero_cpf_cnpj=pagador.get('numeroCpfCnpj'),
                    dados_pagador=pagador,
                )

        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoAlteracaoPagadorError(
                    f'Falha na alteração do pagador - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    numero_cpf_cnpj=pagador.get('numeroCpfCnpj'),
                    dados_pagador=pagador,
                ) from e
            raise BoletoAlteracaoPagadorError(
                f'Falha na comunicação com API de boletos: {e!s}',
                numero_cpf_cnpj=pagador.get('numeroCpfCnpj'),
                dados_pagador=pagador,
            ) from e

    def consultar_webhook(
        self,
        id_webhook: int,
        codigo_tipo_movimento: int,
        client_id: str,
    ) -> dict:
        """Consulta os detalhes de um webhook cadastrado

        Args:
            id_webhook: Identificador único do webhook
            codigo_tipo_movimento: Código do tipo de movimento do webhook (7-Pagamento)
            client_id: ClientId utilizado na utilização do TOKEN

        Returns:
            Dicionário com os dados do webhook conforme estrutura da API:
            {
                "resultado": [
                    {
                        "idWebhook": int,
                        "url": str,
                        "email": str,
                        "codigoTipoMovimento": int,
                        "descricaoTipoMovimento": str,
                        "codigoPeriodoMovimento": int,
                        "descricaoPeriodoMovimento": str,
                        "codigoSituacao": int,
                        "descricaoSituacao": str,
                        "dataHoraCadastro": str,
                        "dataHoraUltimaAlteracao": str,
                        "dataHoraInativacao": str,
                        "descricaoMotivoInativacao": str
                    }
                ]
            }

        Raises:
            BoletoWebhookError: Em caso de falha na requisição com status 400, 406 ou 500
        """
        try:
            params = {
                'idWebhook': id_webhook,
                'codigoTipoMovimento': codigo_tipo_movimento,
            }

            url = f'{self._get_base_url()}/cobranca-bancaria/v3/webhooks'
            headers = self._get_headers(scope='boletos_webhook')
            headers['client_id'] = client_id

            response = self.session.get(url, params=params, headers=headers)

            # Trata erros específicos com códigos 400, 406, 500
            if response.status_code in (400, 406, 500):
                error_data = response.json()
                error_msg = error_data.get('mensagens', [{}])[0].get(
                    'mensagem', 'Erro desconhecido'
                )
                raise BoletoWebhookError(
                    f'Falha na consulta do webhook: {error_msg}',
                    code=response.status_code,
                    id_webhook=id_webhook,
                )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoWebhookError(
                    f'Falha na consulta do webhook - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    id_webhook=id_webhook,
                ) from e
            raise BoletoWebhookError(
                f'Falha na comunicação com API de boletos: {e!s}',
                id_webhook=id_webhook,
            ) from e

    def atualizar_webhook(
        self,
        id_webhook: int,
        webhook: dict,
        client_id: str,
    ) -> None:
        """Atualiza um webhook cadastrado

        Args:
            id_webhook: Identificador único do webhook
            webhook: Dicionário com os dados do webhook para atualização contendo:
                - url: URL do webhook (obrigatório)
                - email: Email do associado (opcional)
            client_id: ClientId utilizado na utilização do TOKEN

        Returns:
            None em caso de sucesso (status 204)

        Raises:
            BoletoWebhookError: Em caso de falha na requisição com status 400, 406 ou 500
        """
        try:
            url = f'{self._get_base_url()}/cobranca-bancaria/v3/webhooks/{id_webhook}'
            headers = self._get_headers(scope='boletos_webhook')
            headers['client_id'] = client_id

            response = self.session.patch(url, json=webhook, headers=headers)

            # Trata erros específicos com códigos 400, 406, 500
            if response.status_code in (400, 406, 500):
                error_data = response.json()
                error_msg = error_data.get('mensagens', [{}])[0].get(
                    'mensagem', 'Erro desconhecido'
                )
                raise BoletoWebhookError(
                    f'Falha na atualização do webhook: {error_msg}',
                    code=response.status_code,
                    id_webhook=id_webhook,
                    dados_webhook=webhook,
                )

            # Verifica se o status é 204 (No Content)
            if response.status_code != 204:
                raise BoletoWebhookError(
                    f'Resposta inesperada da API: {response.status_code}',
                    code=response.status_code,
                    id_webhook=id_webhook,
                    dados_webhook=webhook,
                )

        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoWebhookError(
                    f'Falha na atualização do webhook - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    id_webhook=id_webhook,
                    dados_webhook=webhook,
                ) from e
            raise BoletoWebhookError(
                f'Falha na comunicação com API de boletos: {e!s}',
                id_webhook=id_webhook,
                dados_webhook=webhook,
            ) from e

    def excluir_webhook(
        self,
        id_webhook: int,
        client_id: str,
    ) -> None:
        """Exclui permanentemente um webhook cadastrado

        Args:
            id_webhook: Identificador único do webhook
            client_id: ClientId utilizado na utilização do TOKEN

        Returns:
            None em caso de sucesso (status 204)

        Raises:
            BoletoWebhookError: Em caso de falha na requisição com status 400, 406 ou 500
        """
        try:
            url = f'{self._get_base_url()}/cobranca-bancaria/v3/webhooks/{id_webhook}'
            headers = self._get_headers(scope='boletos_webhook')
            headers['client_id'] = client_id

            response = self.session.delete(url, headers=headers)

            # Trata erros específicos com códigos 400, 406, 500
            if response.status_code in (400, 406, 500):
                error_data = response.json()
                error_msg = error_data.get('mensagens', [{}])[0].get(
                    'mensagem', 'Erro desconhecido'
                )
                raise BoletoWebhookError(
                    f'Falha na exclusão do webhook: {error_msg}',
                    code=response.status_code,
                    id_webhook=id_webhook,
                )

            # Verifica se o status é 204 (No Content)
            if response.status_code != 204:
                raise BoletoWebhookError(
                    f'Resposta inesperada da API: {response.status_code}',
                    code=response.status_code,
                    id_webhook=id_webhook,
                )

        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoWebhookError(
                    f'Falha na exclusão do webhook - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    id_webhook=id_webhook,
                ) from e
            raise BoletoWebhookError(
                f'Falha na comunicação com API de boletos: {e!s}',
                id_webhook=id_webhook,
            ) from e

    def consultar_solicitacoes_webhook(
        self,
        id_webhook: int,
        data_solicitacao: str,
        client_id: str,
        pagina: int | None = None,
        codigo_solicitacao_situacao: int | None = None,
    ) -> dict:
        """Consulta as solicitações de notificação para um webhook cadastrado

        Args:
            id_webhook: Identificador único do webhook
            data_solicitacao: Data da solicitação no formato yyyy-MM-dd
            client_id: ClientId utilizado na utilização do TOKEN
            pagina: Número da página a ser consultada (opcional)
            codigo_solicitacao_situacao: Código da situação da solicitação (3-Enviado com sucesso, 6-Erro no envio)

        Returns:
            Dicionário com o histórico de solicitações conforme estrutura da API:
            {
                "resultado": [
                    {
                        "paginalAtual": int,
                        "totalPaginas": int,
                        "totalRegistros": int,
                        "webhookSolicitacoes": [
                            {
                                "codigoWebhookSituacao": int,
                                "descricaoWebhookSituacao": str,
                                "codigoSolicitacaoSituacao": int,
                                "descricaoSolicitacaoSituacao": str,
                                "codigoTipoMovimento": int,
                                "descricaoTipoMovimento": str,
                                "codigoPeriodoMovimento": int,
                                "descricaoPeriodoMovimento": str,
                                "descricaoErroProcessamento": str,
                                "dataHoraCadastro": str,
                                "validacaoWebhook": bool,
                                "webhookNotificacoes": [
                                    {
                                        "url": str,
                                        "dataHoraInicio": str,
                                        "dataHoraFim": str,
                                        "tempoComunicao": int,
                                        "codigoStatusRequisicao": int,
                                        "descricaoMensagemRetorno": str
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }

        Raises:
            BoletoWebhookError: Em caso de falha na requisição com status 400, 406 ou 500
        """
        try:
            params = {'dataSolicitacao': data_solicitacao}

            if pagina is not None:
                params['pagina'] = pagina
            if codigo_solicitacao_situacao is not None:
                params['codigoSolicitacaoSituacao'] = codigo_solicitacao_situacao

            url = f'{self._get_base_url()}/cobranca-bancaria/v3/webhooks/{id_webhook}/solicitacoes'
            headers = self._get_headers(scope='boletos_webhook')
            headers['client_id'] = client_id

            response = self.session.get(url, params=params, headers=headers)

            # Trata erros específicos com códigos 400, 406, 500
            if response.status_code in (400, 406, 500):
                error_data = response.json()
                error_msg = error_data.get('mensagens', [{}])[0].get(
                    'mensagem', 'Erro desconhecido'
                )
                raise BoletoWebhookError(
                    f'Falha na consulta das solicitações do webhook: {error_msg}',
                    code=response.status_code,
                    id_webhook=id_webhook,
                )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoWebhookError(
                    f'Falha na consulta das solicitações do webhook - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    id_webhook=id_webhook,
                ) from e
            raise BoletoWebhookError(
                f'Falha na comunicação com API de boletos: {e!s}',
                id_webhook=id_webhook,
            ) from e

    def cadastrar_webhook(
        self,
        webhook: dict,
        client_id: str,
    ) -> dict:
        """Cadastra um webhook para receber notificações de acordo com o tipo de movimento

        Args:
            webhook: Dicionário com os dados do webhook contendo:
                - url: URL do webhook (obrigatório)
                - codigoTipoMovimento: Código do tipo de movimento (obrigatório)
                - codigoPeriodoMovimento: Código do período de movimento (obrigatório)
                - email: Email do associado (opcional)
            client_id: ClientId utilizado na utilização do TOKEN

        Returns:
            Resposta da API com confirmação do cadastro (status 201)

        Raises:
            BoletoWebhookError: Em caso de falha na requisição com status 400, 406 ou 500
        """
        try:
            # Valida parâmetros obrigatórios
            if not all(
                key in webhook
                for key in ['url', 'codigoTipoMovimento', 'codigoPeriodoMovimento']
            ):
                raise ValueError('Parâmetros obrigatórios do webhook não informados')

            url = f'{self._get_base_url()}/cobranca-bancaria/v3/webhooks'
            headers = self._get_headers(scope='boletos_webhook')
            headers['client_id'] = client_id

            response = self.session.post(url, json=webhook, headers=headers)

            # Trata erros específicos com códigos 400, 406, 500
            if response.status_code in (400, 406, 500):
                error_data = response.json()
                error_msg = error_data.get('mensagens', [{}])[0].get(
                    'mensagem', 'Erro desconhecido'
                )
                raise BoletoWebhookError(
                    f'Falha no cadastro do webhook: {error_msg}',
                    code=response.status_code,
                    url=webhook.get('url'),
                    dados_webhook=webhook,
                )

            # Verifica se o status é 201 (Created)
            if response.status_code != 201:
                raise BoletoWebhookError(
                    f'Resposta inesperada da API: {response.status_code}',
                    code=response.status_code,
                    url=webhook.get('url'),
                    dados_webhook=webhook,
                )

            return response.json()
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                raise BoletoWebhookError(
                    f'Falha no cadastro do webhook - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    url=webhook.get('url'),
                    dados_webhook=webhook,
                ) from e
            raise BoletoWebhookError(
                f'Falha na comunicação com API de boletos: {e!s}',
                url=webhook.get('url'),
                dados_webhook=webhook,
            ) from e
