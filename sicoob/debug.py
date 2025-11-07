"""Utilitários para debugging do sicoob-sdk.

Este módulo fornece ferramentas para facilitar o debugging temporário
de requisições e respostas da API Sicoob.

Example:
    >>> from sicoob.debug import debug_mode
    >>> from sicoob import AsyncSicoob
    >>>
    >>> # Debug temporário para uma operação específica
    >>> with debug_mode(log_payloads=True):
    ...     async with AsyncSicoob(client_id="...") as client:
    ...         resultado = await client.cobranca.boleto.emitir_boleto(dados)
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sicoob.config import SicoobConfig


@contextmanager
def debug_mode(log_payloads: bool = False) -> Generator[None, None, None]:
    """Context manager para ativar modo debug temporariamente.

    Ativa logs verbosos (DEBUG level) para toda a biblioteca sicoob
    durante a execução do bloco. Ao sair, restaura as configurações
    anteriores.

    Args:
        log_payloads: Se True, loga payloads completos das requisições.
                     Use com cuidado pois pode expor dados sensíveis.

    Yields:
        None

    Example:
        >>> with debug_mode(log_payloads=True):
        ...     resultado = await sicoob.cobranca.boleto.emitir_boleto(dados)
        ...     # Logs detalhados serão exibidos apenas para esta operação

        >>> # Após o bloco, logs voltam ao normal
        >>> resultado2 = await sicoob.cobranca.boleto.consultar_boleto("123")
        >>> # Sem logs verbosos

    Warning:
        Quando log_payloads=True, dados sensíveis podem ser logados.
        Não use em produção ou limpe logs após debugging.
    """
    # Salva estado anterior da configuração
    original_debug = SicoobConfig.get_current_config().debug_mode
    original_log_level = SicoobConfig.get_log_level()
    original_log_requests = SicoobConfig.should_log_requests()
    original_log_responses = SicoobConfig.should_log_responses()

    # Salva níveis de logging anteriores
    logger_sicoob = logging.getLogger('sicoob')
    logger_async_client = logging.getLogger('sicoob.async_client')
    logger_async_boleto = logging.getLogger('sicoob.async_boleto')

    original_levels = {
        'sicoob': logger_sicoob.level,
        'async_client': logger_async_client.level,
        'async_boleto': logger_async_boleto.level,
    }

    try:
        # Ativa modo debug
        SicoobConfig.enable_debug()

        # Se log_payloads, ativa logs de requisição/resposta
        if log_payloads:
            SicoobConfig.update_config(log_requests=True, log_responses=True)

        yield

    finally:
        # Restaura configurações anteriores
        SicoobConfig.update_config(
            debug_mode=original_debug,
            log_level=original_log_level,
            log_requests=original_log_requests,
            log_responses=original_log_responses,
        )

        # Restaura níveis de logging
        logger_sicoob.setLevel(original_levels['sicoob'])
        logger_async_client.setLevel(original_levels['async_client'])
        logger_async_boleto.setLevel(original_levels['async_boleto'])


@contextmanager
def suppress_sicoob_logs() -> Generator[None, None, None]:
    """Context manager para suprimir temporariamente logs do sicoob-sdk.

    Útil quando você quer silenciar logs durante operações em lote
    ou quando os logs estão poluindo a saída.

    Yields:
        None

    Example:
        >>> # Processa 1000 boletos sem poluir os logs
        >>> with suppress_sicoob_logs():
        ...     for dados in lista_boletos:
        ...         await client.cobranca.boleto.emitir_boleto(dados)
    """
    # Salva níveis anteriores
    logger_sicoob = logging.getLogger('sicoob')
    original_level = logger_sicoob.level

    try:
        # Suprime logs (só mostra CRITICAL)
        logger_sicoob.setLevel(logging.CRITICAL)
        yield

    finally:
        # Restaura nível anterior
        logger_sicoob.setLevel(original_level)


def enable_http_logging() -> None:
    """Ativa logging detalhado de requisições HTTP.

    Útil para debugging de problemas de conectividade, timeouts
    ou para ver exatamente o que está sendo enviado/recebido.

    Warning:
        Isso também ativa logs do aiohttp, que podem ser muito verbosos.

    Example:
        >>> from sicoob.debug import enable_http_logging
        >>> enable_http_logging()
        >>> # Agora todos os logs HTTP serão exibidos
    """
    # Ativa logging para módulos HTTP
    logging.getLogger('aiohttp').setLevel(logging.DEBUG)
    logging.getLogger('aiohttp.client').setLevel(logging.DEBUG)
    logging.getLogger('aiohttp.access').setLevel(logging.DEBUG)

    # Ativa logging do sicoob
    SicoobConfig.enable_debug()

    print('✅ HTTP logging ativado (DEBUG level)')


def disable_http_logging() -> None:
    """Desativa logging detalhado de requisições HTTP.

    Restaura níveis de logging para valores padrão.

    Example:
        >>> from sicoob.debug import disable_http_logging
        >>> disable_http_logging()
        >>> # Logs voltam ao normal
    """
    # Desativa logging para módulos HTTP
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('aiohttp.client').setLevel(logging.WARNING)
    logging.getLogger('aiohttp.access').setLevel(logging.WARNING)

    # Desativa debug do sicoob
    SicoobConfig.disable_debug()

    print('✅ HTTP logging desativado (WARNING level)')
