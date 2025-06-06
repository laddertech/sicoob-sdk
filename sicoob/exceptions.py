class SicoobError(Exception):
    """Classe base para todas as exceções do pacote Sicoob"""
    def __init__(self, message: str, code: int = None):
        self.message = message
        self.code = code
        super().__init__(message)

    def __str__(self):
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class BoletoError(SicoobError):
    """Classe base para erros relacionados a boletos"""
    pass


class BoletoEmissaoError(BoletoError):
    """Erro durante a emissão de boleto"""
    def __init__(self, message: str, code: int = None, dados_boleto: dict = None):
        self.dados_boleto = dados_boleto
        super().__init__(message, code)


class BoletoConsultaError(BoletoError):
    """Erro durante a consulta de boleto"""
    def __init__(self, message: str, code: int = None, nosso_numero: str = None):
        self.nosso_numero = nosso_numero
        super().__init__(message, code)


class BoletoConsultaPagadorError(BoletoError):
    """Erro durante a consulta de boletos por pagador"""
    def __init__(self, message: str, code: int = None, numero_cpf_cnpj: str = None):
        self.numero_cpf_cnpj = numero_cpf_cnpj
        super().__init__(message, code)


class BoletoConsultaFaixaError(BoletoError):
    """Erro durante a consulta de faixas de nosso número"""
    def __init__(self, message: str, code: int = None, numero_cliente: int = None):
        self.numero_cliente = numero_cliente
        super().__init__(message, code)


class BoletoNaoEncontradoError(BoletoConsultaError):
    """Boleto não encontrado durante consulta"""
    def __init__(self, nosso_numero: str):
        super().__init__(
            f"Boleto com nosso número {nosso_numero} não encontrado",
            code=404,
            nosso_numero=nosso_numero
        )


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
    def __init__(self, message: str, code: int = None, periodo: str = None):
        self.periodo = periodo
        super().__init__(message, code)


class SaldoError(ContaCorrenteError):
    """Erro durante consulta de saldo"""
    def __init__(self, message: str, code: int = None, conta: str = None):
        self.conta = conta
        super().__init__(message, code)


class TransferenciaError(ContaCorrenteError):
    """Erro durante transferência"""
    def __init__(self, message: str, code: int = None, dados: dict = None):
        self.dados = dados
        super().__init__(message, code)


class CobrancaPixError(PixError):
    """Erro durante operações de cobrança PIX"""
    def __init__(self, message: str, code: int = None, txid: str = None):
        self.txid = txid
        super().__init__(message, code)


class CobrancaPixNaoEncontradaError(CobrancaPixError):
    """Cobrança PIX não encontrada"""
    def __init__(self, txid: str):
        super().__init__(
            f"Cobrança PIX com txid {txid} não encontrada",
            code=404,
            txid=txid
        )


class CobrancaPixVencimentoError(PixError):
    """Erro durante operações de cobrança PIX com vencimento"""
    def __init__(self, message: str, code: int = None, txid: str = None):
        self.txid = txid
        super().__init__(message, code)


class WebhookPixError(PixError):
    """Erro durante operações de webhook PIX"""
    def __init__(self, message: str, code: int = None, chave: str = None):
        self.chave = chave
        super().__init__(message, code)


class WebhookPixNaoEncontradoError(WebhookPixError):
    """Webhook PIX não encontrado"""
    def __init__(self, chave: str):
        super().__init__(
            f"Webhook PIX para chave {chave} não encontrado",
            code=404,
            chave=chave
        )


class LoteCobrancaPixError(PixError):
    """Erro durante operações com lote de cobranças PIX"""
    def __init__(self, message: str, code: int = None, id_lote: str = None):
        self.id_lote = id_lote
        super().__init__(message, code)


class QrCodePixError(PixError):
    """Erro durante geração/consulta de QR Code PIX"""
    def __init__(self, message: str, code: int = None, txid: str = None):
        self.txid = txid
        super().__init__(message, code)
