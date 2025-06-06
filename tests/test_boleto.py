import pytest
import requests
from unittest.mock import Mock
from sicoob.boleto import BoletoAPI
from sicoob.exceptions import BoletoConsultaError, BoletoConsultaPagadorError, BoletoEmissaoError


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
        "codigoBarras": "00190000090123456789012345678901234567890000",
    }
    boleto_client.session.post.return_value = mock_response

    # Dados de teste
    dados = {
        "numeroContrato": 123456,
        "modalidade": 1,
        "valor": 100.50,
        "beneficiario": {"nome": "Teste Beneficiário", "documento": "12345678901"},
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
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "400 Bad Request"
    )
    mock_response.status_code = 400
    boleto_client.session.post.return_value = mock_response

    dados = {"numeroContrato": 123456, "valor": 100.50}

    # Verifica se exceção é levantada
    with pytest.raises(Exception, match="400 Bad Request"):
        boleto_client.emitir_boleto(dados)


def test_emitir_boleto_erro_generico(boleto_client):
    """Testa a emissão de boleto com erro genérico"""
    # Configura o mock para erro genérico
    boleto_client.session.post.side_effect = requests.exceptions.RequestException(
        "Erro de conexão"
    )

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
        "situacao": "REGISTRADO",
    }
    boleto_client.session.get.return_value = mock_response

    result = boleto_client.consultar_boleto(
        numero_cliente=123456, codigo_modalidade=1, nosso_numero="123456789"
    )

    assert result == {"nossoNumero": "123456789", "situacao": "REGISTRADO"}
    boleto_client.session.get.assert_called_once()
    args, kwargs = boleto_client.session.get.call_args
    assert "boletos" in args[0]  # Verifica se está no endpoint correto
    assert kwargs["params"]["nossoNumero"] == "123456789"


def test_consultar_boleto_nao_encontrado(boleto_client):
    """Testa a consulta de boleto não encontrado (deve retornar None)"""
    # Configura o mock para 404
    mock_response = Mock()
    http_error = requests.exceptions.HTTPError("404 Not Found")
    http_error.response = mock_response
    mock_response.status_code = 404
    boleto_client.session.get.side_effect = http_error

    result = boleto_client.consultar_boleto(
        numero_cliente=123456, codigo_modalidade=1, nosso_numero="000000000"
    )
    assert result is None
    boleto_client.session.get.assert_called_once()


def test_consultar_boleto_erro_http(boleto_client):
    """Testa a consulta de boleto com erro HTTP"""
    # Configura o mock para erro HTTP (não 404)
    mock_response = Mock()
    http_error = requests.exceptions.HTTPError("500 Server Error")
    http_error.response = mock_response
    mock_response.status_code = 500
    boleto_client.session.get.side_effect = http_error

    # Verifica se exceção é levantada
    with pytest.raises(BoletoConsultaError) as exc_info:
        boleto_client.consultar_boleto(
            numero_cliente=123456, codigo_modalidade=1, nosso_numero="123456789"
        )
    assert "[500] Falha na consulta do boleto - Status: 500" in str(exc_info.value)


def test_consultar_boleto_erro_generico(boleto_client):
    """Testa a consulta de boleto com erro genérico"""
    # Configura o mock para erro genérico
    boleto_client.session.get.side_effect = requests.exceptions.RequestException(
        "Erro de conexão"
    )

    # Verifica se exceção é levantada
    with pytest.raises(Exception, match="Erro de conexão"):
        boleto_client.consultar_boleto(
            numero_cliente=123456, codigo_modalidade=1, nosso_numero="123456789"
        )


def test_consultar_boletos_por_pagador_sucesso(boleto_client):
    """Testa a consulta de boletos por pagador com sucesso"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {
        "boletos": [
            {"nossoNumero": "123", "situacao": "EM_ABERTO"},
            {"nossoNumero": "456", "situacao": "LIQUIDADO"}
        ]
    }
    boleto_client.session.get.return_value = mock_response

    # Chama o método com todos os parâmetros
    result = boleto_client.consultar_boletos_por_pagador(
        numero_cpf_cnpj="12345678901",
        numero_cliente=123456,
        client_id="client-id-123",
        codigo_situacao=1,
        data_inicio="2025-01-01",
        data_fim="2025-06-30"
    )

    # Verificações
    assert len(result["boletos"]) == 2
    boleto_client.session.get.assert_called_once()
    args, kwargs = boleto_client.session.get.call_args
    assert "pagadores/12345678901/boletos" in args[0]
    assert kwargs["params"]["numeroCliente"] == 123456
    assert kwargs["params"]["codigoSituacao"] == 1
    assert kwargs["params"]["dataInicio"] == "2025-01-01"
    assert kwargs["params"]["dataFim"] == "2025-06-30"
    assert kwargs["headers"]["client_id"] == "client-id-123"


def test_consultar_boletos_por_pagador_apenas_obrigatorios(boleto_client):
    """Testa a consulta de boletos por pagador apenas com parâmetros obrigatórios"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {"boletos": []}
    boleto_client.session.get.return_value = mock_response

    # Chama o método apenas com parâmetros obrigatórios
    result = boleto_client.consultar_boletos_por_pagador(
        numero_cpf_cnpj="12345678901",
        numero_cliente=123456,
        client_id="client-id-123"
    )

    # Verificações
    assert len(result["boletos"]) == 0
    args, kwargs = boleto_client.session.get.call_args
    assert "pagadores/12345678901/boletos" in args[0]
    assert kwargs["params"]["numeroCliente"] == 123456
    assert "codigoSituacao" not in kwargs["params"]
    assert "dataInicio" not in kwargs["params"]
    assert "dataFim" not in kwargs["params"]


def test_consultar_boletos_por_pagador_erro_http(boleto_client):
    """Testa a consulta de boletos por pagador com erro HTTP"""
    # Configura o mock para erro HTTP
    mock_response = Mock()
    http_error = requests.exceptions.HTTPError("500 Server Error")
    http_error.response = mock_response
    mock_response.status_code = 500
    boleto_client.session.get.side_effect = http_error

    # Verifica se exceção é levantada
    with pytest.raises(BoletoConsultaPagadorError) as exc_info:
        boleto_client.consultar_boletos_por_pagador(
            numero_cpf_cnpj="12345678901",
            numero_cliente=123456,
            client_id="client-id-123"
        )
    assert "[500] Falha na consulta de boletos por pagador - Status: 500" in str(exc_info.value)
    assert exc_info.value.numero_cpf_cnpj == "12345678901"


def test_consultar_boletos_por_pagador_erro_generico(boleto_client):
    """Testa a consulta de boletos por pagador com erro genérico"""
    # Configura o mock para erro genérico
    boleto_client.session.get.side_effect = requests.exceptions.RequestException(
        "Erro de conexão"
    )

    # Verifica se exceção é levantada
    with pytest.raises(BoletoConsultaPagadorError) as exc_info:
        boleto_client.consultar_boletos_por_pagador(
            numero_cpf_cnpj="12345678901",
            numero_cliente=123456,
            client_id="client-id-123"
        )
    assert "Falha na comunicação com API de boletos: Erro de conexão" in str(exc_info.value)
    assert exc_info.value.numero_cpf_cnpj == "12345678901"


def test_emitir_segunda_via_sucesso(boleto_client):
    """Testa a emissão de segunda via de boleto com sucesso"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {
        "nossoNumero": "123456789",
        "linhaDigitavel": "00190000090123456789012345678901234567890000",
        "pdfBase64": None
    }
    boleto_client.session.get.return_value = mock_response

    # Chama o método
    result = boleto_client.emitir_segunda_via(
        numero_cliente=123456,
        codigo_modalidade=1,
        nosso_numero=987654321
    )

    # Verificações
    assert "nossoNumero" in result
    assert "linhaDigitavel" in result
    boleto_client.session.get.assert_called_once()
    args, kwargs = boleto_client.session.get.call_args
    assert "boletos/segunda-via" in args[0]
    assert kwargs["params"]["numeroCliente"] == 123456
    assert kwargs["params"]["codigoModalidade"] == 1
    assert kwargs["params"]["nossoNumero"] == 987654321
    assert kwargs["params"]["gerarPdf"] == "false"


def test_emitir_segunda_via_com_pdf(boleto_client):
    """Testa a emissão de segunda via com PDF"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {
        "pdfBase64": "JVBERi0xLjQK..."
    }
    boleto_client.session.get.return_value = mock_response

    # Chama o método com gerar_pdf=True
    result = boleto_client.emitir_segunda_via(
        numero_cliente=123456,
        codigo_modalidade=1,
        linha_digitavel="00190000090123456789012345678901234567890000",
        gerar_pdf=True
    )

    # Verificações
    assert "pdfBase64" in result
    args, kwargs = boleto_client.session.get.call_args
    assert kwargs["params"]["linhaDigitavel"] == "00190000090123456789012345678901234567890000"
    assert kwargs["params"]["gerarPdf"] == "true"


def test_emitir_segunda_via_com_codigo_barras(boleto_client):
    """Testa a emissão de segunda via usando código de barras"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {
        "nossoNumero": "123456789",
        "linhaDigitavel": "00190000090123456789012345678901234567890000"
    }
    boleto_client.session.get.return_value = mock_response

    # Chama o método com código de barras
    result = boleto_client.emitir_segunda_via(
        numero_cliente=123456,
        codigo_modalidade=1,
        codigo_barras="00190000090123456789012345678901234567890000"
    )

    # Verificações
    assert "nossoNumero" in result
    assert "linhaDigitavel" in result
    args, kwargs = boleto_client.session.get.call_args
    assert kwargs["params"]["codigoBarras"] == "00190000090123456789012345678901234567890000"
    assert "nossoNumero" not in kwargs["params"]
    assert "linhaDigitavel" not in kwargs["params"]


def test_emitir_segunda_via_erro_http(boleto_client):
    """Testa a emissão de segunda via com erro HTTP"""
    # Configura o mock para erro HTTP
    mock_response = Mock()
    http_error = requests.exceptions.HTTPError("400 Bad Request")
    http_error.response = mock_response
    mock_response.status_code = 400
    boleto_client.session.get.side_effect = http_error

    # Verifica se exceção é levantada
    with pytest.raises(BoletoEmissaoError) as exc_info:
        boleto_client.emitir_segunda_via(
            numero_cliente=123456,
            codigo_modalidade=1,
            nosso_numero=987654321
        )
    assert "[400] Falha na emissão da segunda via - Status: 400" in str(exc_info.value)
    assert exc_info.value.code == 400


def test_emitir_segunda_via_erro_generico(boleto_client):
    """Testa a emissão de segunda via com erro genérico"""
    # Configura o mock para erro genérico
    boleto_client.session.get.side_effect = requests.exceptions.RequestException(
        "Erro de conexão"
    )

    # Verifica se exceção é levantada
    with pytest.raises(Exception, match="Erro de conexão"):
        boleto_client.emitir_segunda_via(
            numero_cliente=123456,
            codigo_modalidade=1,
            nosso_numero=987654321
        )
