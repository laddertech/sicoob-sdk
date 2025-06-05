import pytest
import requests
from unittest.mock import Mock
from sicoob.boleto import BoletoAPI
from sicoob.exceptions import (
    BoletoNaoEncontradoError,
    BoletoConsultaError,
    BoletoError
)

@pytest.fixture
def boleto_client(mock_oauth_client):
    """Fixture que retorna um cliente BoletoAPI configurado para testes"""
    session = Mock()
    return BoletoAPI(mock_oauth_client, session)

def test_emitir_boleto_sucesso(boleto_client):
    """Testa a emissão de boleto com sucesso"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {
        "nossoNumero": "123456789",
        "codigoBarras": "00190000090123456789012345678901234567890000"
    }
    boleto_client.session.post.return_value = mock_response

    # Dados de teste
    dados = {
        "numeroContrato": 123456,
        "modalidade": 1,
        "valor": 100.50,
        "beneficiario": {
            "nome": "Teste Beneficiário",
            "documento": "12345678901"
        }
    }

    # Chama o método
    result = boleto_client.emitir_boleto(dados)

    # Verificações
    assert "nossoNumero" in result
    assert "codigoBarras" in result
    boleto_client.session.post.assert_called_once()
    args, kwargs = boleto_client.session.post.call_args
    assert "boletos" in args[0]  # Verifica se está no endpoint correto
    assert kwargs["json"] == dados

def test_emitir_boleto_erro_http(boleto_client):
    """Testa a emissão de boleto com erro HTTP"""
    # Configura o mock para erro HTTP
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Bad Request")
    mock_response.status_code = 400
    boleto_client.session.post.return_value = mock_response

    dados = {"numeroContrato": 123456, "valor": 100.50}

    # Verifica se exceção é levantada
    with pytest.raises(Exception, match="400 Bad Request"):
        boleto_client.emitir_boleto(dados)

def test_emitir_boleto_erro_generico(boleto_client):
    """Testa a emissão de boleto com erro genérico"""
    # Configura o mock para erro genérico
    boleto_client.session.post.side_effect = requests.exceptions.RequestException("Erro de conexão")

    dados = {"numeroContrato": 123456, "valor": 100.50}

    # Verifica se exceção é levantada
    with pytest.raises(Exception, match="Erro de conexão"):
        boleto_client.emitir_boleto(dados)

def test_consultar_boleto_sucesso(boleto_client):
    """Testa a consulta de boleto com sucesso"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {
        "nossoNumero": "123456789",
        "situacao": "REGISTRADO"
    }
    boleto_client.session.get.return_value = mock_response

    nosso_numero = "123456789"
    result = boleto_client.consultar_boleto(nosso_numero)

    assert result == {
        "nossoNumero": "123456789",
        "situacao": "REGISTRADO"
    }
    boleto_client.session.get.assert_called_once()
    args, kwargs = boleto_client.session.get.call_args
    assert nosso_numero in args[0]  # Verifica se nossoNumero está na URL

def test_consultar_boleto_nao_encontrado(boleto_client):
    """Testa a consulta de boleto não encontrado"""
    # Configura o mock para 404
    mock_response = Mock()
    http_error = requests.exceptions.HTTPError("404 Not Found")
    http_error.response = mock_response
    mock_response.status_code = 404
    boleto_client.session.get.side_effect = http_error

    nosso_numero = "000000000"
    with pytest.raises(BoletoNaoEncontradoError) as exc_info:
        boleto_client.consultar_boleto(nosso_numero)
    assert str(exc_info.value) == "[404] Boleto com nosso número 000000000 não encontrado"

def test_consultar_boleto_erro_http(boleto_client):
    """Testa a consulta de boleto com erro HTTP"""
    # Configura o mock para erro HTTP (não 404)
    mock_response = Mock()
    http_error = requests.exceptions.HTTPError("500 Server Error")
    http_error.response = mock_response
    mock_response.status_code = 500
    boleto_client.session.get.side_effect = http_error

    nosso_numero = "123456789"

    # Verifica se exceção é levantada
    with pytest.raises(BoletoConsultaError) as exc_info:
        boleto_client.consultar_boleto(nosso_numero)
    assert "[500] Falha na consulta do boleto - Status: 500" in str(exc_info.value)

def test_consultar_boleto_erro_generico(boleto_client):
    """Testa a consulta de boleto com erro genérico"""
    # Configura o mock para erro genérico
    boleto_client.session.get.side_effect = requests.exceptions.RequestException("Erro de conexão")

    nosso_numero = "123456789"

    # Verifica se exceção é levantada
    with pytest.raises(Exception, match="Erro de conexão"):
        boleto_client.consultar_boleto(nosso_numero)
