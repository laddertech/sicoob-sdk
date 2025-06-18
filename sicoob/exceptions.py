import requests


class SicoobError(Exception):
    """Classe base para todas as exceções do pacote Sicoob"""

    def __init__(
        self, message: str, code: int | None = None, mensagens: list[dict] | None = None
    ) -> None:
        self.message = message
        self.code = code
        self.mensagens = mensagens or [
            {'mensagem': message, 'codigo': str(code) if code else '0'}
        ]
        super().__init__(message)

    def __str__(self) -> str:
        if self.code:
            return f'[{self.code}] {self.message}'
        return self.message

    def to_dict(self) -> dict:
        """Retorna o erro no formato padrão da API Sicoob"""
        return {'mensagens': self.mensagens}


class RespostaInvalidaError(SicoobError):
    """Erro quando a resposta da API não está no formato esperado"""

    def __init__(self, message: str, response: requests.Response | None = None) -> None:
        self.response = response
        self.message = message  # Definindo explicitamente
        super().__init__(message, response.status_code if response else None)


class BoletoError(SicoobError):
    """Classe base para erros relacionados a boletos"""

    pass


class BoletoEmissaoError(BoletoError):
    """Erro durante a emissão de boleto"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        dados_boleto: dict | None = None,
        mensagens: list[dict] | None = None,
    ) -> None:
        self.dados_boleto = dados_boleto
        super().__init__(message, code, mensagens)


class BoletoConsultaError(BoletoError):
    """Erro durante a consulta de boleto"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        nosso_numero: str | None = None,
        mensagens: list[dict] | None = None,
    ) -> None:
        self.nosso_numero = nosso_numero
        super().__init__(message, code, mensagens)


class BoletoConsultaPagadorError(BoletoError):
    """Erro durante a consulta de boletos por pagador"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        numero_cpf_cnpj: str | None = None,
        mensagens: list[dict] | None = None,
    ) -> None:
        self.numero_cpf_cnpj = numero_cpf_cnpj
        super().__init__(message, code, mensagens)


class BoletoConsultaFaixaError(BoletoError):
    """Erro durante a consulta de faixas de nosso número"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        numero_cliente: int | None = None,
        mensagens: list[dict] | None = None,
    ) -> None:
        self.numero_cliente = numero_cliente
        super().__init__(message, code, mensagens)


class BoletoNaoEncontradoError(BoletoConsultaError):
    """Boleto não encontrado durante consulta"""

    def __init__(self, nosso_numero: str) -> None:
        super().__init__(
            f'Boleto com nosso número {nosso_numero} não encontrado',
            code=404,
            nosso_numero=nosso_numero,
        )


class BoletoBaixaError(BoletoError):
    """Erro durante a baixa de boleto"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        nosso_numero: int | None = None,
        dados_boleto: dict | None = None,
        mensagens: list[dict] | None = None,
    ) -> None:
        self.nosso_numero = nosso_numero
        self.dados_boleto = dados_boleto
        super().__init__(message, code, mensagens)


class BoletoAlteracaoError(BoletoError):
    """Erro durante a alteração de boleto"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        nosso_numero: str | None = None,
        dados_alteracao: dict | None = None,
        mensagens: list[dict] | None = None,
    ) -> None:
        self.nosso_numero = nosso_numero
        self.dados_alteracao = dados_alteracao
        super().__init__(message, code, mensagens)


class BoletoAlteracaoPagadorError(BoletoError):
    """Erro durante a alteração de dados do pagador"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        numero_cpf_cnpj: str | None = None,
        dados_pagador: dict | None = None,
        mensagens: list[dict] | None = None,
    ) -> None:
        self.numero_cpf_cnpj = numero_cpf_cnpj
        self.dados_pagador = dados_pagador
        super().__init__(message, code, mensagens)


class BoletoWebhookError(BoletoError):
    """Erro durante operações de webhook de boleto"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        url: str | None = None,
        dados_webhook: dict | None = None,
        id_webhook: int | None = None,
        mensagens: list[dict] | None = None,
        operation: str | None = None,
    ) -> None:
        self.url = url
        self.dados_webhook = dados_webhook
        self.id_webhook = id_webhook
        self.operation = operation
        super().__init__(message, code, mensagens)


class ContaCorrenteError(SicoobError):
    """Classe base para erros relacionados a conta corrente"""

    pass


class PixError(SicoobError):
    """Classe base para erros relacionados a PIX"""

    pass


class AutenticacaoError(SicoobError):
    """Erros relacionados a autenticação"""

    pass


class ExtratoError(ContaCorrenteError):
    """Erro durante consulta de extrato"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        periodo: str | None = None,
        mensagens: list[dict] | None = None,
    ) -> None:
        self.periodo = periodo
        super().__init__(message, code, mensagens)


class SaldoError(ContaCorrenteError):
    """Erro durante consulta de saldo"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        conta: str | None = None,
        mensagens: list[dict] | None = None,
    ) -> None:
        self.conta = conta
        super().__init__(message, code, mensagens)


class TransferenciaError(ContaCorrenteError):
    """Erro durante transferência"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        dados: dict | None = None,
        mensagens: list[dict] | None = None,
    ) -> None:
        self.dados = dados
        super().__init__(message, code, mensagens)


class CobrancaPixError(PixError):
    """Erro durante operações de cobrança PIX"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        txid: str | None = None,
        mensagens: list[dict] | None = None,
    ) -> None:
        self.txid = txid
        super().__init__(message, code, mensagens)


class CobrancaPixNaoEncontradaError(CobrancaPixError):
    """Cobrança PIX não encontrada"""

    def __init__(self, txid: str) -> None:
        super().__init__(
            f'Cobrança PIX com txid {txid} não encontrada', code=404, txid=txid
        )


class CobrancaPixVencimentoError(PixError):
    """Erro durante operações de cobrança PIX com vencimento"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        txid: str | None = None,
        mensagens: list[dict] | None = None,
    ) -> None:
        self.txid = txid
        super().__init__(message, code, mensagens)


class WebhookPixError(PixError):
    """Erro durante operações de webhook PIX"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        chave: str | None = None,
        mensagens: list[dict] | None = None,
    ) -> None:
        self.chave = chave
        super().__init__(message, code, mensagens)


class WebhookPixNaoEncontradoError(WebhookPixError):
    """Webhook PIX não encontrado"""

    def __init__(self, chave: str) -> None:
        super().__init__(
            f'Webhook PIX para chave {chave} não encontrado', code=404, chave=chave
        )


class LoteCobrancaPixError(PixError):
    """Erro durante operações com lote de cobranças PIX"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        id_lote: str | None = None,
        mensagens: list[dict] | None = None,
    ) -> None:
        self.id_lote = id_lote
        super().__init__(message, code, mensagens)


class QrCodePixError(PixError):
    """Erro durante geração/consulta de QR Code PIX"""

    def __init__(
        self, message: str, code: int | None = None, txid: str | None = None
    ) -> None:
        self.txid = txid
        super().__init__(message, code)
