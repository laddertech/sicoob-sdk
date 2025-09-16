import requests


class SicoobError(Exception):
    """Classe base para todas as exceções do pacote Sicoob"""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        mensagens: list[dict] | None = None,
        response: requests.Response | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.response = response
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
        status_code = (
            response.status_code
            if response and hasattr(response, 'status_code')
            else None
        )
        super().__init__(message, status_code)
        self.message = message  # Definindo explicitamente após super().__init__


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


# Exceções de Resiliência


class ResilienceError(SicoobError):
    """Classe base para erros de resiliência"""

    pass


class MaxRetriesExceededError(ResilienceError):
    """Erro quando o número máximo de tentativas é excedido"""

    def __init__(
        self,
        message: str,
        attempts: int | None = None,
        last_error: Exception | None = None,
    ) -> None:
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(message)


class CircuitBreakerOpenError(ResilienceError):
    """Erro quando circuit breaker está aberto"""

    def __init__(
        self,
        message: str,
        failure_count: int | None = None,
        recovery_timeout: float | None = None,
    ) -> None:
        self.failure_count = failure_count
        self.recovery_timeout = recovery_timeout
        super().__init__(message)


class TimeoutConfigurationError(ResilienceError):
    """Erro na configuração de timeout"""

    pass


# Exceções de Paginação


class PaginationError(SicoobError):
    """Classe base para erros de paginação"""

    def __init__(
        self,
        message: str,
        page: int | None = None,
        page_size: int | None = None,
        total_pages: int | None = None,
    ) -> None:
        self.page = page
        self.page_size = page_size
        self.total_pages = total_pages
        super().__init__(message)


class InvalidPageError(PaginationError):
    """Erro quando página solicitada é inválida"""

    pass


class PageSizeError(PaginationError):
    """Erro quando tamanho da página é inválido"""

    pass


# Exceções de Cache


class CacheError(SicoobError):
    """Classe base para erros de cache"""

    def __init__(
        self,
        message: str,
        key: str | None = None,
        backend: str | None = None,
        operation: str | None = None,
    ) -> None:
        self.key = key
        self.backend = backend
        self.operation = operation
        super().__init__(message)


class CacheBackendError(CacheError):
    """Erro no backend de cache"""

    def __init__(
        self,
        message: str,
        backend: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        self.original_error = original_error
        super().__init__(message, backend=backend)


class CacheSerializationError(CacheError):
    """Erro na serialização/deserialização de dados do cache"""

    def __init__(
        self,
        message: str,
        key: str | None = None,
        data_type: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        self.data_type = data_type
        self.original_error = original_error
        super().__init__(message, key=key)


class CacheKeyError(CacheError):
    """Erro relacionado a chaves de cache inválidas"""

    def __init__(
        self, message: str, key: str | None = None, reason: str | None = None
    ) -> None:
        self.reason = reason
        super().__init__(message, key=key)


class CacheConfigurationError(CacheError):
    """Erro na configuração do sistema de cache"""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_value: str | None = None,
    ) -> None:
        self.config_key = config_key
        self.config_value = config_value
        super().__init__(message)


class CacheEvictionError(CacheError):
    """Erro durante processo de despejo de cache"""

    def __init__(
        self,
        message: str,
        eviction_policy: str | None = None,
        items_to_evict: int | None = None,
        original_error: Exception | None = None,
    ) -> None:
        self.eviction_policy = eviction_policy
        self.items_to_evict = items_to_evict
        self.original_error = original_error
        super().__init__(message)


class CacheFullError(CacheError):
    """Erro quando cache está cheio e não pode aceitar novos items"""

    def __init__(
        self,
        message: str,
        max_size: int | None = None,
        current_size: int | None = None,
        backend: str | None = None,
    ) -> None:
        self.max_size = max_size
        self.current_size = current_size
        super().__init__(message, backend=backend)


class CacheExpiredError(CacheError):
    """Erro quando item do cache expirou"""

    def __init__(
        self,
        message: str,
        key: str | None = None,
        expiry_time: float | None = None,
        current_time: float | None = None,
    ) -> None:
        self.expiry_time = expiry_time
        self.current_time = current_time
        super().__init__(message, key=key)


class CacheInvalidationError(CacheError):
    """Erro durante invalidação de cache"""

    def __init__(
        self,
        message: str,
        keys: list[str] | None = None,
        tags: list[str] | None = None,
        pattern: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        self.keys = keys or []
        self.tags = tags or []
        self.pattern = pattern
        self.original_error = original_error
        super().__init__(message)
