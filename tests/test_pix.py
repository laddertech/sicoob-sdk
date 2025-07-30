from unittest.mock import Mock

import pytest
from pypix_api.banks.sicoob import SicoobPixAPI

from sicoob.exceptions import (
    CobrancaPixNaoEncontradaError,
    WebhookPixNaoEncontradoError,
)


@pytest.fixture
def pix_client(mock_oauth_client: Mock) -> SicoobPixAPI:
    """Fixture que retorna um cliente PixAPI configurado para testes"""
    from sicoob.client import SicoobPixAPICustom
    return SicoobPixAPICustom(mock_oauth_client, True)


def test_criar_cobranca_pix(pix_client: SicoobPixAPI) -> None:
    """Testa a criação de cobrança PIX"""
    # Configura o mock
    mock_response = Mock()
    mock_response.status_code = 200  # Status de sucesso
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
    result = pix_client.criar_cob(txid, dados)

    # Verificações
    if result != {'status': 'ATIVA'}:
        raise ValueError(
            'Resultado da criação de cobrança PIX não corresponde ao esperado'
        )
    pix_client.session.put.assert_called_once()
    args, kwargs = pix_client.session.put.call_args
    assert txid in args[0]  # Verifica se txid está na URL
    assert kwargs['json'] == dados


def test_consultar_cobranca_pix(pix_client: SicoobPixAPI) -> None:
    """Testa a consulta de cobrança PIX"""
    # Configura o mock para sucesso
    mock_response = Mock()
    mock_response.status_code = 200  # Status HTTP de sucesso
    mock_response.json.return_value = {'status': 'ATIVA'}
    mock_response.raise_for_status.return_value = None
    pix_client.session.get.return_value = mock_response

    txid = '123e4567-e89b-12d3-a456-426614174000'
    result = pix_client.consultar_cob(txid)

    if result != {'status': 'ATIVA'}:
        raise ValueError(
            'Resultado da consulta de cobrança PIX não corresponde ao esperado'
        )
    pix_client.session.get.assert_called_once()

    # Testa caso de não encontrado (404)
    mock_response_404 = Mock()
    mock_response_404.raise_for_status.side_effect = Exception('404')
    mock_response_404.status_code = 404
    mock_response_404.json.return_value = {
        'type': 'RecursoNaoEncontrado',
        'title': 'Cobrança não encontrada',
        'status': 404,
        'detail': f'Cobrança com txid {txid} não encontrada'
    }
    pix_client.session.get.return_value = mock_response_404
    with pytest.raises(CobrancaPixNaoEncontradaError) as exc_info:
        pix_client.consultar_cob(txid)
    assert txid in str(exc_info.value)


# def test_obter_qrcode_pix(pix_client: SicoobPixAPI) -> None:
#     """Testa a obtenção do QR Code PIX"""
#     mock_response = Mock()
#     mock_response.json.return_value = {
#         'qrcode': 'base64encodedimage',
#         'imagemQrcode': 'base64encodedimage',
#     }
#     pix_client.session.get.return_value = mock_response

#     txid = '123e4567-e89b-12d3-a456-426614174000'
#     result = pix_client.obter_qrcode_pix(txid)

#     if 'qrcode' not in result:
#         raise ValueError("Resultado deve conter 'qrcode'")
#     if 'imagemQrcode' not in result:
#         raise ValueError("Resultado deve conter 'imagemQrcode'")
#     pix_client.session.get.assert_called_once()


    def test_configurar_webhook_pix(pix_client: SicoobPixAPI) -> None:
        """Testa a configuração de webhook PIX"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'CONFIGURADO'}
        pix_client.session.put.return_value = mock_response

        chave = '12345678901'
        webhook_url = 'https://meusite.com/webhook'
        result = pix_client.configurar_webhook(chave, webhook_url)

        if result != {'status': 'CONFIGURADO'}:
            raise ValueError(
                'Resultado da configuração de webhook PIX não corresponde ao esperado'
            )
        pix_client.session.put.assert_called_once()
        args, kwargs = pix_client.session.put.call_args
        assert chave in args[0]  # Verifica se chave está na URL
        assert kwargs['json'] == {'webhookUrl': webhook_url}


def test_consultar_webhook_pix(pix_client: SicoobPixAPI) -> None:
    """Testa a consulta de webhook PIX"""
    # Configura o mock para sucesso
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'webhookUrl': 'https://meusite.com/webhook'}
    mock_response.raise_for_status.return_value = None
    pix_client.session.get.return_value = mock_response

    chave = '12345678901'
    result = pix_client.consultar_webhook(chave)

    if result != {'webhookUrl': 'https://meusite.com/webhook'}:
        raise ValueError(
            'Resultado da consulta de webhook PIX não corresponde ao esperado'
        )
    pix_client.session.get.assert_called_once()

    # Testa caso de não encontrado (404)
    mock_response_404 = Mock()
    mock_response_404.raise_for_status.side_effect = Exception('404')
    mock_response_404.status_code = 404
    mock_response_404.json.return_value = {
        'type': 'RecursoNaoEncontrado',
        'title': 'Webhook não encontrado',
        'status': 404,
        'detail': f'Webhook para chave {chave} não encontrado'
    }
    pix_client.session.get.return_value = mock_response_404
    with pytest.raises(WebhookPixNaoEncontradoError) as exc_info:
        pix_client.consultar_webhook(chave)
    assert chave in str(exc_info.value)


def test_criar_cobranca_pix_com_vencimento(pix_client: SicoobPixAPI) -> None:
    """Testa a criação de cobrança PIX com vencimento"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'status': 'ATIVA'}
    pix_client.session.put.return_value = mock_response

    txid = '123e4567-e89b-12d3-a456-426614174000'
    dados = {
        'calendario': {'dataDeVencimento': '2025-12-31'},
        'valor': {'original': '100.50'},
        'chave': '12345678901',
    }

    result = pix_client.criar_cobv(txid, dados)

    if result != {'status': 'ATIVA'}:
        raise ValueError(
            'Resultado da criação de cobrança PIX com vencimento não corresponde ao esperado'
        )
    pix_client.session.put.assert_called_once()
    args, kwargs = pix_client.session.put.call_args
    assert 'cobv' in args[0]  # Verifica se está usando endpoint cobv
    assert kwargs['json'] == dados


def test_consultar_cobranca_pix_com_vencimento(pix_client: SicoobPixAPI) -> None:
    """Testa a consulta de cobrança PIX com vencimento"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'status': 'ATIVA'}
    mock_response.raise_for_status.return_value = None
    pix_client.session.get.return_value = mock_response

    txid = '123e4567-e89b-12d3-a456-426614174000'
    revisao = 0
    result = pix_client.consultar_cobv(txid, revisao)

    if result != {'status': 'ATIVA'}:
        raise ValueError(
            'Resultado da consulta de cobrança PIX com vencimento não corresponde ao esperado'
        )
    pix_client.session.get.assert_called_once()

    # Testa caso de não encontrado (404)
    mock_response_404 = Mock()
    mock_response_404.raise_for_status.side_effect = Exception('404')
    mock_response_404.status_code = 404
    mock_response_404.json.return_value = {
        'type': 'RecursoNaoEncontrado',
        'title': 'Cobrança não encontrada',
        'status': 404,
        'detail': f'Cobrança com txid {txid} não encontrada'
    }
    pix_client.session.get.return_value = mock_response_404
    with pytest.raises(CobrancaPixNaoEncontradaError) as exc_info:
        pix_client.consultar_cobv(txid, revisao)
    assert txid in str(exc_info.value)

# def test_obter_qrcode_pix_com_vencimento(pix_client: SicoobPixAPI) -> None:
#     """Testa a obtenção do QR Code de cobrança com vencimento"""
#     mock_response = Mock()
#     mock_response.json.return_value = {
#         'qrcode': 'base64encodedimage',
#         'imagemQrcode': 'base64encodedimage',
#     }
#     pix_client.session.get.return_value = mock_response

#     txid = '123e4567-e89b-12d3-a456-426614174000'
#     result = pix_client.obter_qrcode_pix_com_vencimento(txid)

#     if 'qrcode' not in result:
#         raise ValueError("Resultado deve conter 'qrcode'")
#     if 'imagemQrcode' not in result:
#         raise ValueError("Resultado deve conter 'imagemQrcode'")
#     pix_client.session.get.assert_called_once()


def test_excluir_webhook_pix_sucesso(pix_client: SicoobPixAPI) -> None:
    """Testa a exclusão de webhook PIX com sucesso"""
    mock_response = Mock()
    mock_response.status_code = 204
    mock_response.json.return_value = None
    mock_response.raise_for_status.return_value = None
    pix_client.session.delete.return_value = mock_response

    chave = '12345678901'
    result = pix_client.excluir_webhook(chave)

    assert result is True, f"Esperado True, mas recebeu: {result}"
    pix_client.session.delete.assert_called_once()


def test_excluir_webhook_pix_nao_encontrado(pix_client: SicoobPixAPI) -> None:
    """Testa a exclusão de webhook PIX quando não encontrado"""
    chave = '12345678901'
    mock_response_404 = Mock()
    mock_response_404.raise_for_status.side_effect = Exception('404')
    mock_response_404.status_code = 404
    mock_response_404.json.return_value = {
        'type': 'RecursoNaoEncontrado',
        'title': 'Webhook não encontrado',
        'status': 404,
        'detail': f'Webhook para chave {chave} não encontrado'
    }
    pix_client.session.delete.return_value = mock_response_404

    with pytest.raises(WebhookPixNaoEncontradoError) as exc_info:
        pix_client.excluir_webhook(chave)
    assert chave in str(exc_info.value)


# def test_criar_lote_cobranca_pix_com_vencimento(pix_client: SicoobPixAPI) -> None:
#     """Testa a criação de lote de cobranças PIX com vencimento"""
#     mock_response = Mock()
#     mock_response.json.return_value = {'status': 'PROCESSANDO'}
#     pix_client.session.put.return_value = mock_response

#     id_lote = 'LOTE123'
#     cobrancas = [
#         {
#             'txid': '123e4567-e89b-12d3-a456-426614174001',
#             'valor': {'original': '100.50'},
#             'chave': '12345678901',
#         }
#     ]

#     result = pix_client.criar_lote_cobranca_pix_com_vencimento(id_lote, cobrancas)

#     if result != {'status': 'PROCESSANDO'}:
#         raise ValueError(
#             'Resultado da criação de lote de cobranças PIX não corresponde ao esperado'
#         )
#     pix_client.session.put.assert_called_once()
#     args, kwargs = pix_client.session.put.call_args
#     assert 'lotecobv' in args[0]
#     assert kwargs['json'] == {'cobrancas': cobrancas}


# def test_consultar_lote_cobranca_pix_com_vencimento(pix_client: SicoobPixAPI) -> None:
#     """Testa a consulta de lote de cobranças PIX com vencimento"""
#     mock_response = Mock()
#     mock_response.json.return_value = {'status': 'PROCESSADO'}
#     pix_client.session.get.return_value = mock_response

#     id_lote = 'LOTE123'
#     result = pix_client.consultar_lote_cobranca_pix_com_vencimento(id_lote)

#     if result != {'status': 'PROCESSADO'}:
#         raise ValueError(
#             'Resultado da consulta de lote de cobranças PIX não corresponde ao esperado'
#         )
#     pix_client.session.get.assert_called_once()

#     # Testa caso de não encontrado (404)
#     mock_response.raise_for_status.side_effect = Exception('404')
#     mock_response.status_code = 404
#     with pytest.raises(CobrancaPixNaoEncontradaError) as exc_info:
#         pix_client.consultar_lote_cobranca_pix_com_vencimento(id_lote)
#     if id_lote not in str(exc_info.value):
#         raise ValueError('ID do lote não encontrado na mensagem de erro')
