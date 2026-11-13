"""Validação de credenciais passadas explicitamente ao SDK (uso interno)."""

from __future__ import annotations

import os


def validar_client_id(client_id: object) -> str:
    """Exige um ``client_id`` não vazio.

    O SDK não procura credenciais no ambiente do processo: um valor ausente
    ou em branco é erro de configuração, nunca motivo para usar a credencial
    de outra conta que esteja em variável de ambiente.

    Raises:
        ValueError: ``client_id`` ausente, vazio ou que não seja texto.
    """
    if not isinstance(client_id, str) or not client_id.strip():
        raise ValueError('client_id é obrigatório')
    return client_id.strip()


def ler_env(dotenv: bool) -> dict[str, str | None]:
    """Lê as variáveis SICOOB_* — só usado pelos construtores ``from_env``."""
    if dotenv:
        from dotenv import load_dotenv

        load_dotenv()
    return {
        'client_id': os.getenv('SICOOB_CLIENT_ID'),
        'certificado': os.getenv('SICOOB_CERTIFICADO'),
        'chave_privada': os.getenv('SICOOB_CHAVE_PRIVADA'),
        'certificado_pfx': os.getenv('SICOOB_CERTIFICADO_PFX'),
        'senha_pfx': os.getenv('SICOOB_SENHA_PFX'),
        'environment': os.getenv('SICOOB_ENVIRONMENT') or 'production',
        'sandbox_token': os.getenv('SICOOB_SANDBOX_TOKEN'),
    }
