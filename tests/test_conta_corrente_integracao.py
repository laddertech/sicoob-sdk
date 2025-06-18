import os
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


def test_extrato_conta_corrente_integracao_real(sicoob_client):
    """Teste de integração real com API de extrato da conta corrente (sandbox)"""
    # Parâmetros da consulta
    params = {
        'mes': 6,
        'ano': 2025,
        'dia_inicial': 1,
        'dia_final': 5,
        'numero_conta_corrente': '12345678',  # Número de conta sandbox
        'agrupar_cnab': True,
    }

    try:
        # Chama a API real (sem mocks)
        resultado = sicoob_client.conta_corrente.extrato(**params)

        # Verifica campos obrigatórios no JSON de resposta
        required_fields = [
            'saldoAtual',
            'saldoBloqueado',
            'saldoLimite',
            'saldoAnterior',
            'saldoBloqueioJudicial',
            'saldoBloqueioJudicialAnterior',
            'transacoes',
        ]
        for field in required_fields:
            assert field in resultado, (
                f"Campo obrigatório '{field}' não encontrado no retorno"
            )

        # Verifica estrutura das transações
        assert isinstance(resultado['transacoes'], list), (
            'Transações deve ser uma lista'
        )
        if len(resultado['transacoes']) > 0:
            transacao_fields = [
                'tipo',
                'valor',
                'data',
                'dataLote',
                'descricao',
                'numeroDocumento',
                'cpfCnpj',
                'descInfComplementar',
            ]
            for field in transacao_fields:
                assert field in resultado['transacoes'][0], (
                    f"Campo de transação '{field}' não encontrado"
                )

    except Exception as e:
        print(
            f'\nResposta completa da API: {e.response.text if hasattr(e, "response") else str(e)}'
        )
        raise
