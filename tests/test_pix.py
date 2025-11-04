from unittest.mock import Mock, patch

import pytest

from sicoob.exceptions import (
    CobrancaPixNaoEncontradaError,
    WebhookPixNaoEncontradoError,
)
from sicoob.pix import PixAPI


@pytest.fixture
def pix_client(mock_oauth_client: Mock) -> PixAPI:
    """Fixture que retorna um cliente PixAPI configurado para testes"""
    mock_session = Mock()
    return PixAPI(mock_oauth_client, mock_session)


def test_criar_cobranca_pix(pix_client: PixAPI) -> None:
    """Testa a criação de cobrança PIX"""
    # Configura o mock
    with patch.object(pix_client._pix_api, 'criar_cob') as mock_criar:
        mock_criar.return_value = {'status': 'ATIVA'}

        # Dados de teste
        txid = 'abcd1234567890123456789012345'  # 29 caracteres
        dados = {
            'calendario': {'expiracao': 3600},
            'valor': {'original': '100.50'},
            'chave': '12345678901',
        }

        # Chama o método
        result = pix_client.criar_cobranca_imediata(txid, dados)

        # Verificações
        assert result == {'status': 'ATIVA'}
        mock_criar.assert_called_once_with(txid, dados)


def test_consultar_cobranca_pix(pix_client: PixAPI) -> None:
    """Testa a consulta de cobrança PIX"""
    # Configura o mock
    with patch.object(pix_client._pix_api, 'consultar_cob') as mock_consultar:
        mock_consultar.return_value = {'status': 'ATIVA', 'txid': '123'}

        # Chama o método
        txid = 'abcd1234567890123456789012345'  # 29 caracteres
        result = pix_client.consultar_cobranca_imediata(txid)

        # Verificações
        assert result == {'status': 'ATIVA', 'txid': '123'}
        mock_consultar.assert_called_once_with(txid)


def test_consultar_cobranca_pix_nao_encontrada(pix_client: PixAPI) -> None:
    """Testa consulta de cobrança PIX não encontrada"""
    with patch.object(pix_client._pix_api, 'consultar_cob') as mock_consultar:
        mock_consultar.side_effect = CobrancaPixNaoEncontradaError(
            'Cobrança com txid 123 não encontrada'
        )

        txid = 'abcd1234567890123456789012345'  # 29 caracteres
        with pytest.raises(CobrancaPixNaoEncontradaError) as exc_info:
            pix_client.consultar_cobranca_imediata(txid)

        assert 'não encontrada' in str(exc_info.value)


def test_consultar_webhook_pix(pix_client: PixAPI) -> None:
    """Testa a consulta de webhook PIX"""
    # Configura o mock
    with patch.object(pix_client._pix_api, 'consultar_webhook') as mock_consultar:
        mock_consultar.return_value = {
            'webhookUrl': 'https://example.com/webhook',
            'chave': '12345678901',
        }

        # Chama o método
        chave = '12345678901'
        result = pix_client.consultar_webhook(chave)

        # Verificações
        assert result == {
            'webhookUrl': 'https://example.com/webhook',
            'chave': '12345678901',
        }
        mock_consultar.assert_called_once_with(chave)


def test_criar_cobranca_pix_com_vencimento(pix_client: PixAPI) -> None:
    """Testa a criação de cobrança PIX com vencimento"""
    # Configura o mock
    with patch.object(pix_client._pix_api, 'criar_cobv') as mock_criar:
        mock_criar.return_value = {'status': 'ATIVA', 'txid': '456'}

        # Dados de teste
        txid = '456e4567-e89b-12d3-a456-426614174000'
        dados = {
            'calendario': {'dataDeVencimento': '2024-12-31'},
            'valor': {'original': '250.00'},
            'chave': '98765432100',
        }

        # Chama o método
        result = pix_client.criar_cobranca_com_vencimento(txid, dados)

        # Verificações
        assert result == {'status': 'ATIVA', 'txid': '456'}
        mock_criar.assert_called_once_with(txid, dados)


def test_consultar_cobranca_pix_com_vencimento(pix_client: PixAPI) -> None:
    """Testa a consulta de cobrança PIX com vencimento"""
    # Configura o mock
    with patch.object(pix_client._pix_api, 'consultar_cobv') as mock_consultar:
        mock_consultar.return_value = {
            'status': 'ATIVA',
            'calendario': {'dataDeVencimento': '2024-12-31'},
        }

        # Chama o método
        txid = '456e4567-e89b-12d3-a456-426614174000'
        result = pix_client.consultar_cobranca_com_vencimento(txid)

        # Verificações
        expected = {'status': 'ATIVA', 'calendario': {'dataDeVencimento': '2024-12-31'}}
        assert result == expected
        mock_consultar.assert_called_once_with(txid, 0)  # revisao=0 por padrão


def test_excluir_webhook_pix_sucesso(pix_client: PixAPI) -> None:
    """Testa exclusão bem sucedida de webhook PIX"""
    # Configura o mock
    with patch.object(pix_client._pix_api, 'excluir_webhook') as mock_excluir:
        mock_excluir.return_value = True  # Exclusão retorna True

        # Chama o método
        chave = '12345678901'
        pix_client.excluir_webhook(chave)

        # Verificações
        mock_excluir.assert_called_once_with(chave)


def test_excluir_webhook_pix_nao_encontrado(pix_client: PixAPI) -> None:
    """Testa exclusão de webhook PIX não encontrado"""
    # Configura o mock para lançar exceção
    with patch.object(pix_client._pix_api, 'excluir_webhook') as mock_excluir:
        mock_excluir.side_effect = WebhookPixNaoEncontradoError(
            'O webhook para a chave informada não foi encontrado'
        )

        # Testa se a exceção correta é lançada
        chave = '99999999999'
        with pytest.raises(WebhookPixNaoEncontradoError) as exc_info:
            pix_client.excluir_webhook(chave)

        assert 'webhook' in str(exc_info.value).lower()
        mock_excluir.assert_called_once_with(chave)
