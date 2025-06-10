from unittest.mock import Mock

import pytest

from sicoob.conta_corrente import ContaCorrenteAPI
from sicoob.exceptions import ExtratoError, TransferenciaError


@pytest.fixture
def conta_corrente_client(mock_oauth_client: Mock) -> ContaCorrenteAPI:
    """Fixture que retorna um cliente ContaCorrenteAPI configurado para testes"""
    session = Mock()
    return ContaCorrenteAPI(mock_oauth_client, session)


def test_extrato_sucesso(conta_corrente_client: ContaCorrenteAPI) -> None:
    """Testa a obtenção de extrato com sucesso"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = [{'transacao': 'DEPOSITO', 'valor': 100.50}]
    conta_corrente_client.session.get.return_value = mock_response

    # Chama o método
    result = conta_corrente_client.extrato(
        mes=6, ano=2025, dia_inicial=1, dia_final=30, numero_conta_corrente=12345
    )

    # Verificações
    if len(result) != 1:
        raise ValueError('Extrato deveria retornar 1 transação')
    if result[0]['transacao'] != 'DEPOSITO':
        raise ValueError('Tipo de transação não corresponde ao esperado')
    conta_corrente_client.session.get.assert_called_once()
    args, kwargs = conta_corrente_client.session.get.call_args
    assert 'extrato/6/2025' in args[0]
    assert (
        str(kwargs['params']['numeroContaCorrente']) == '12345'
    )  # Aceita int ou string


def test_extrato_erro(conta_corrente_client: ContaCorrenteAPI) -> None:
    """Testa o tratamento de erro na obtenção de extrato"""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception('Erro API')
    mock_response.json.side_effect = Exception('Erro ao consultar extrato')
    conta_corrente_client.session.get.return_value = mock_response

    with pytest.raises(ExtratoError) as exc_info:
        conta_corrente_client.extrato(
            mes=6, ano=2025, dia_inicial=1, dia_final=30, numero_conta_corrente=12345
        )
    assert 'Erro API' in str(exc_info.value)


def test_saldo_sucesso(conta_corrente_client: ContaCorrenteAPI) -> None:
    """Testa a obtenção de saldo com sucesso"""
    mock_response = Mock()
    mock_response.json.return_value = {'saldo': 1500.75}
    conta_corrente_client.session.get.return_value = mock_response

    result = conta_corrente_client.saldo(numero_conta='12345')

    if result != {'saldo': 1500.75}:
        raise ValueError('Saldo não corresponde ao esperado')
    conta_corrente_client.session.get.assert_called_once()
    args, kwargs = conta_corrente_client.session.get.call_args
    assert 'saldo' in args[0]
    assert kwargs['params']['numeroConta'] == '12345'


def test_saldo_sem_numero_conta(conta_corrente_client: ContaCorrenteAPI) -> None:
    """Testa a obtenção de saldo sem especificar número da conta"""
    mock_response = Mock()
    mock_response.json.return_value = {'saldo': 1500.75}
    conta_corrente_client.session.get.return_value = mock_response

    result = conta_corrente_client.saldo()

    if result != {'saldo': 1500.75}:
        raise ValueError('Saldo sem número de conta não corresponde ao esperado')
    conta_corrente_client.session.get.assert_called_once()
    args, kwargs = conta_corrente_client.session.get.call_args
    assert 'saldo' in args[0]
    assert 'numeroConta' not in kwargs['params']


def test_transferencia_sucesso(conta_corrente_client: ContaCorrenteAPI) -> None:
    """Testa transferência entre contas com sucesso"""
    mock_response = Mock()
    mock_response.json.return_value = {'status': 'PROCESSADA'}
    conta_corrente_client.session.post.return_value = mock_response

    result = conta_corrente_client.transferencia(
        valor=500.00,
        conta_destino='54321',
        tipo_transferencia='TED',
        descricao='Pagamento serviço',
        numero_conta='12345',
    )

    if result != {'status': 'PROCESSADA'}:
        raise ValueError('Status da transferência não corresponde ao esperado')
    conta_corrente_client.session.post.assert_called_once()
    args, kwargs = conta_corrente_client.session.post.call_args
    assert 'transferencia' in args[0]
    assert kwargs['json']['valor'] == 500.00
    assert kwargs['json']['contaDestino'] == '54321'
    assert kwargs['json']['tipoTransferencia'] == 'TED'
    assert kwargs['json']['descricao'] == 'Pagamento serviço'
    assert kwargs['json']['numeroConta'] == '12345'


def test_transferencia_minima(conta_corrente_client: ContaCorrenteAPI) -> None:
    """Testa transferência com apenas parâmetros obrigatórios"""
    mock_response = Mock()
    mock_response.json.return_value = {'status': 'PROCESSADA'}
    conta_corrente_client.session.post.return_value = mock_response

    result = conta_corrente_client.transferencia(valor=100.00, conta_destino='54321')

    if result != {'status': 'PROCESSADA'}:
        raise ValueError('Status da transferência mínima não corresponde ao esperado')
    conta_corrente_client.session.post.assert_called_once()
    args, kwargs = conta_corrente_client.session.post.call_args
    assert 'transferencia' in args[0]
    assert kwargs['json']['valor'] == 100.00
    assert kwargs['json']['contaDestino'] == '54321'
    assert kwargs['json']['tipoTransferencia'] == 'TED'  # Valor default
    assert 'descricao' not in kwargs['json']
    assert 'numeroConta' not in kwargs['json']


def test_transferencia_erro(conta_corrente_client: ContaCorrenteAPI) -> None:
    """Testa tratamento de erro na transferência"""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception('Erro API')
    mock_response.json.side_effect = Exception('Erro na transferência')
    conta_corrente_client.session.post.return_value = mock_response

    with pytest.raises(TransferenciaError) as exc_info:
        conta_corrente_client.transferencia(valor=500.00, conta_destino='54321')
    assert 'Erro API' in str(exc_info.value)
