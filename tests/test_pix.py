from unittest.mock import Mock

import pytest

from sicoob.exceptions import (
    CobrancaPixNaoEncontradaError,
    WebhookPixNaoEncontradoError,
)
from sicoob.pix import PixAPI


@pytest.fixture
def pix_client(mock_oauth_client: Mock) -> PixAPI:
    """Fixture que retorna um cliente PixAPI configurado para testes"""
    session = Mock()
    return PixAPI(mock_oauth_client, session)


def test_criar_cobranca_pix(pix_client: PixAPI) -> None:
    """Testa a criação de cobrança PIX"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {'status': 'ATIVA'}
    pix_client.session.put.return_value = mock_response

    # Dados de teste
    txid = '123e4567-e89b-12d3-a456-426614174000'
    dados = {
        'calendario': {'expiracao': 3600},
        'valor': {'original': '100.50'},
        'chave': '12345678901',
    }

    # Chama o método
    result = pix_client.criar_cobranca_pix(txid, dados)

    # Verificações
    if result != {'status': 'ATIVA'}:
        raise ValueError(
            'Resultado da criação de cobrança PIX não corresponde ao esperado'
        )
    pix_client.session.put.assert_called_once()
    args, kwargs = pix_client.session.put.call_args
    assert txid in args[0]  # Verifica se txid está na URL
    assert kwargs['json'] == dados


def test_consultar_cobranca_pix(pix_client: PixAPI) -> None:
    """Testa a consulta de cobrança PIX"""
    # Configura o mock para sucesso
    mock_response = Mock()
    mock_response.json.return_value = {'status': 'ATIVA'}
    pix_client.session.get.return_value = mock_response

    txid = '123e4567-e89b-12d3-a456-426614174000'
    result = pix_client.consultar_cobranca_pix(txid)

    if result != {'status': 'ATIVA'}:
        raise ValueError(
            'Resultado da consulta de cobrança PIX não corresponde ao esperado'
        )
    pix_client.session.get.assert_called_once()

    # Testa caso de não encontrado (404)
    mock_response.raise_for_status.side_effect = Exception('404')
    mock_response.status_code = 404
    with pytest.raises(CobrancaPixNaoEncontradaError) as exc_info:
        pix_client.consultar_cobranca_pix(txid)
    assert txid in str(exc_info.value)


def test_cancelar_cobranca_pix(pix_client: PixAPI) -> None:
    """Testa o cancelamento de cobrança PIX"""
    # Configura o mock para sucesso
    mock_response = Mock()
    pix_client.session.delete.return_value = mock_response

    txid = '123e4567-e89b-12d3-a456-426614174000'
    result = pix_client.cancelar_cobranca_pix(txid)

    if result is not True:
        raise ValueError('Cancelamento de cobrança PIX não retornou True')
    pix_client.session.delete.assert_called_once()

    # Testa caso de não encontrado (404)
    mock_response.raise_for_status.side_effect = Exception('404')
    mock_response.status_code = 404
    with pytest.raises(CobrancaPixNaoEncontradaError) as exc_info:
        pix_client.cancelar_cobranca_pix(txid)
    assert txid in str(exc_info.value)


def test_obter_qrcode_pix(pix_client: PixAPI) -> None:
    """Testa a obtenção do QR Code PIX"""
    mock_response = Mock()
    mock_response.json.return_value = {
        'qrcode': 'base64encodedimage',
        'imagemQrcode': 'base64encodedimage',
    }
    pix_client.session.get.return_value = mock_response

    txid = '123e4567-e89b-12d3-a456-426614174000'
    result = pix_client.obter_qrcode_pix(txid)

    if 'qrcode' not in result:
        raise ValueError("Resultado deve conter 'qrcode'")
    if 'imagemQrcode' not in result:
        raise ValueError("Resultado deve conter 'imagemQrcode'")
    pix_client.session.get.assert_called_once()


def test_configurar_webhook_pix(pix_client: PixAPI) -> None:
    """Testa a configuração de webhook PIX"""
    mock_response = Mock()
    mock_response.json.return_value = {'status': 'CONFIGURADO'}
    pix_client.session.put.return_value = mock_response

    chave = '12345678901'
    webhook_url = 'https://meusite.com/webhook'
    result = pix_client.configurar_webhook_pix(chave, webhook_url)

    if result != {'status': 'CONFIGURADO'}:
        raise ValueError(
            'Resultado da configuração de webhook PIX não corresponde ao esperado'
        )
    pix_client.session.put.assert_called_once()
    args, kwargs = pix_client.session.put.call_args
    assert chave in args[0]  # Verifica se chave está na URL
    assert kwargs['json'] == {'webhookUrl': webhook_url}


def test_consultar_webhook_pix(pix_client: PixAPI) -> None:
    """Testa a consulta de webhook PIX"""
    # Configura o mock para sucesso
    mock_response = Mock()
    mock_response.json.return_value = {'webhookUrl': 'https://meusite.com/webhook'}
    pix_client.session.get.return_value = mock_response

    chave = '12345678901'
    result = pix_client.consultar_webhook_pix(chave)

    if result != {'webhookUrl': 'https://meusite.com/webhook'}:
        raise ValueError(
            'Resultado da consulta de webhook PIX não corresponde ao esperado'
        )
    pix_client.session.get.assert_called_once()

    # Testa caso de não encontrado (404)
    mock_response.raise_for_status.side_effect = Exception('404')
    mock_response.status_code = 404
    with pytest.raises(WebhookPixNaoEncontradoError) as exc_info:
        pix_client.consultar_webhook_pix(chave)
    assert chave in str(exc_info.value)


def test_criar_cobranca_pix_com_vencimento(pix_client: PixAPI) -> None:
    """Testa a criação de cobrança PIX com vencimento"""
    mock_response = Mock()
    mock_response.json.return_value = {'status': 'ATIVA'}
    pix_client.session.put.return_value = mock_response

    txid = '123e4567-e89b-12d3-a456-426614174000'
    dados = {
        'calendario': {'dataDeVencimento': '2025-12-31'},
        'valor': {'original': '100.50'},
        'chave': '12345678901',
    }

    result = pix_client.criar_cobranca_pix_com_vencimento(txid, dados)

    if result != {'status': 'ATIVA'}:
        raise ValueError(
            'Resultado da criação de cobrança PIX com vencimento não corresponde ao esperado'
        )
    pix_client.session.put.assert_called_once()
    args, kwargs = pix_client.session.put.call_args
    assert 'cobv' in args[0]  # Verifica se está usando endpoint cobv
    assert kwargs['json'] == dados


def test_consultar_cobranca_pix_com_vencimento(pix_client: PixAPI) -> None:
    """Testa a consulta de cobrança PIX com vencimento"""
    mock_response = Mock()
    mock_response.json.return_value = {'status': 'ATIVA'}
    pix_client.session.get.return_value = mock_response

    txid = '123e4567-e89b-12d3-a456-426614174000'
    result = pix_client.consultar_cobranca_pix_com_vencimento(txid)

    if result != {'status': 'ATIVA'}:
        raise ValueError(
            'Resultado da consulta de cobrança PIX com vencimento não corresponde ao esperado'
        )
    pix_client.session.get.assert_called_once()

    # Testa caso de não encontrado (404)
    mock_response.raise_for_status.side_effect = Exception('404')
    mock_response.status_code = 404
    with pytest.raises(CobrancaPixNaoEncontradaError) as exc_info:
        pix_client.consultar_cobranca_pix_com_vencimento(txid)
    assert txid in str(exc_info.value)


def test_cancelar_cobranca_pix_com_vencimento(pix_client: PixAPI) -> None:
    """Testa o cancelamento de cobrança PIX com vencimento"""
    mock_response = Mock()
    pix_client.session.delete.return_value = mock_response

    txid = '123e4567-e89b-12d3-a456-426614174000'
    result = pix_client.cancelar_cobranca_pix_com_vencimento(txid)

    if result is not True:
        raise ValueError(
            'Cancelamento de cobrança PIX com vencimento não retornou True'
        )
    pix_client.session.delete.assert_called_once()

    # Testa caso de não encontrado (404)
    mock_response.raise_for_status.side_effect = Exception('404')
    mock_response.status_code = 404
    with pytest.raises(CobrancaPixNaoEncontradaError) as exc_info:
        pix_client.cancelar_cobranca_pix_com_vencimento(txid)
    assert txid in str(exc_info.value)


def test_obter_qrcode_pix_com_vencimento(pix_client: PixAPI) -> None:
    """Testa a obtenção do QR Code de cobrança com vencimento"""
    mock_response = Mock()
    mock_response.json.return_value = {
        'qrcode': 'base64encodedimage',
        'imagemQrcode': 'base64encodedimage',
    }
    pix_client.session.get.return_value = mock_response

    txid = '123e4567-e89b-12d3-a456-426614174000'
    result = pix_client.obter_qrcode_pix_com_vencimento(txid)

    if 'qrcode' not in result:
        raise ValueError("Resultado deve conter 'qrcode'")
    if 'imagemQrcode' not in result:
        raise ValueError("Resultado deve conter 'imagemQrcode'")
    pix_client.session.get.assert_called_once()


def test_excluir_webhook_pix(pix_client: PixAPI) -> None:
    """Testa a exclusão de webhook PIX"""
    mock_response = Mock()
    pix_client.session.delete.return_value = mock_response

    chave = '12345678901'
    result = pix_client.excluir_webhook_pix(chave)

    if result is not True:
        raise ValueError('Exclusão de webhook PIX não retornou True')
    pix_client.session.delete.assert_called_once()

    # Testa caso de não encontrado (404)
    mock_response.raise_for_status.side_effect = Exception('404')
    mock_response.status_code = 404
    with pytest.raises(WebhookPixNaoEncontradoError) as exc_info:
        pix_client.excluir_webhook_pix(chave)
    assert chave in str(exc_info.value)


def test_criar_lote_cobranca_pix_com_vencimento(pix_client: PixAPI) -> None:
    """Testa a criação de lote de cobranças PIX com vencimento"""
    mock_response = Mock()
    mock_response.json.return_value = {'status': 'PROCESSANDO'}
    pix_client.session.put.return_value = mock_response

    id_lote = 'LOTE123'
    cobrancas = [
        {
            'txid': '123e4567-e89b-12d3-a456-426614174001',
            'valor': {'original': '100.50'},
            'chave': '12345678901',
        }
    ]

    result = pix_client.criar_lote_cobranca_pix_com_vencimento(id_lote, cobrancas)

    if result != {'status': 'PROCESSANDO'}:
        raise ValueError(
            'Resultado da criação de lote de cobranças PIX não corresponde ao esperado'
        )
    pix_client.session.put.assert_called_once()
    args, kwargs = pix_client.session.put.call_args
    assert 'lotecobv' in args[0]
    assert kwargs['json'] == {'cobrancas': cobrancas}


def test_consultar_lote_cobranca_pix_com_vencimento(pix_client: PixAPI) -> None:
    """Testa a consulta de lote de cobranças PIX com vencimento"""
    mock_response = Mock()
    mock_response.json.return_value = {'status': 'PROCESSADO'}
    pix_client.session.get.return_value = mock_response

    id_lote = 'LOTE123'
    result = pix_client.consultar_lote_cobranca_pix_com_vencimento(id_lote)

    if result != {'status': 'PROCESSADO'}:
        raise ValueError(
            'Resultado da consulta de lote de cobranças PIX não corresponde ao esperado'
        )
    pix_client.session.get.assert_called_once()

    # Testa caso de não encontrado (404)
    mock_response.raise_for_status.side_effect = Exception('404')
    mock_response.status_code = 404
    with pytest.raises(CobrancaPixNaoEncontradaError) as exc_info:
        pix_client.consultar_lote_cobranca_pix_com_vencimento(id_lote)
    if id_lote not in str(exc_info.value):
        raise ValueError('ID do lote não encontrado na mensagem de erro')
