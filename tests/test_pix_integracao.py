import os
import uuid
import pytest
from dotenv import load_dotenv

from sicoob.client import Sicoob

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()


@pytest.fixture
def sicoob_client():
    """Fixture que retorna um cliente Sicoob configurado para sandbox"""
    client_id = os.getenv('SICOOB_SANDBOX_CLIENT_ID')
    if not client_id:
        pytest.skip('SICOOB_SANDBOX_CLIENT_ID não configurado no ambiente')

    return Sicoob(
        client_id=client_id,
        sandbox_mode=True,  # Modo sandbox não requer certificado
    )


def test_criar_cobranca_pix_integracao_real(sicoob_client):
    """Teste de integração real com API de cobrança PIX (sandbox)"""
    # Gera um txid válido (27-36 caracteres)
    txid = str(uuid.uuid4()).replace('-', '')

    # Payload da cobrança PIX
    payload = {
        'calendario': {'expiracao': 3600},
        'devedor': {'cnpj': '12345678000195', 'nome': 'Empresa de Serviços SA'},
        'valor': {'original': '37.00'},
        'chave': '7d9f0335-8dcc-4054-9bf9-0dbd61d36906',
        'solicitacaoPagador': 'Serviço realizado.',
        'infoAdicionais': [
            {'nome': 'Campo 1', 'valor': 'Informação Adicional1 do PSP-Recebedor'},
            {'nome': 'Campo 2', 'valor': 'Informação Adicional2 do PSP-Recebedor'},
        ],
    }

    try:
        # Chama a API real (sem mocks)
        resultado = sicoob_client.cobranca.pix.criar_cob(txid, payload)

        # Verifica campos obrigatórios no JSON de resposta
        required_fields = [
            'brcode',
            'calendario',
            'devedor',
            'valor',
            'chave',
            'solicitacaoPagador',
            'infoAdicionais',
            'loc',
            'location',
        ]
        for field in required_fields:
            assert field in resultado, (
                f"Campo obrigatório '{field}' não encontrado no retorno"
            )

    except Exception as e:
        print(
            f'\nResposta completa da API: {e.response.text if hasattr(e, "response") else str(e)}'
        )
        raise
