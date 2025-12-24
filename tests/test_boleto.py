from unittest.mock import Mock

import pytest
import requests

from sicoob.boleto import BoletoAPI
from sicoob.exceptions import (
    BoletoAlteracaoError,
    BoletoAlteracaoPagadorError,
    BoletoBaixaError,
    BoletoConsultaError,
    BoletoConsultaFaixaError,
    BoletoConsultaPagadorError,
    BoletoEmissaoError,
    BoletoWebhookError,
)


@pytest.fixture
def boleto_client(mock_oauth_client: Mock) -> BoletoAPI:
    """Fixture que retorna um cliente BoletoAPI configurado para testes"""
    session = Mock()
    return BoletoAPI(mock_oauth_client, session)


def test_emitir_boleto_sucesso(boleto_client: BoletoAPI) -> None:
    """Testa a emissão de boleto com sucesso"""
    # Configura o mock
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'resultado': {
            'nossoNumero': '123456789',
            'codigoBarras': '00190000090123456789012345678901234567890000',
        }
    }
    boleto_client.session.post.return_value = mock_response

    # Dados de teste
    dados = {
        'numeroCliente': 123456,
        'codigoModalidade': 1,
        'numeroContaCorrente': 12345,
        'codigoEspecieDocumento': 'DM',
        'dataEmissao': '2024-01-01',
        'dataVencimento': '2024-12-31',
        'valor': 100.50,
        'seuNumero': '123456789',
        'identificacaoEmissaoBoleto': 1,
        'identificacaoDistribuicaoBoleto': 1,
        'tipoDesconto': 0,
        'tipoMulta': 0,
        'tipoJurosMora': 3,
        'numeroParcela': 1,
        'pagador': {
            'numeroCpfCnpj': '11144477735',
            'nome': 'João Silva',
            'endereco': 'Rua Teste, 123',
            'bairro': 'Centro',
            'cidade': 'São Paulo',
            'cep': '01001000',
            'uf': 'SP',
        },
    }

    # Chama o método
    result = boleto_client.emitir_boleto(dados)

    # Verificações
    if 'resultado' not in result:
        raise ValueError("Resultado deve conter 'resultado'")
    if 'nossoNumero' not in result['resultado']:
        raise ValueError("Resultado deve conter 'nossoNumero'")
    if 'codigoBarras' not in result['resultado']:
        raise ValueError("Resultado deve conter 'codigoBarras'")
    boleto_client.session.post.assert_called_once()
    args, kwargs = boleto_client.session.post.call_args
    assert 'boletos' in args[0]  # Verifica se está no endpoint correto
    assert kwargs['json'] == dados


def test_emitir_boleto_erro_http(boleto_client: BoletoAPI) -> None:
    """Testa a emissão de boleto com erro HTTP"""
    # Configura o mock para erro HTTP
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Dados inválidos', 'codigo': 'ERR001'}]
    }
    boleto_client.session.post.return_value = mock_response

    dados = {
        'numeroCliente': 123456,
        'codigoModalidade': 1,
        'numeroContaCorrente': 12345,
        'codigoEspecieDocumento': 'DM',
        'dataEmissao': '2024-01-01',
        'dataVencimento': '2024-12-31',
        'valor': 100.50,
        'seuNumero': '123456789',
        'identificacaoEmissaoBoleto': 1,
        'identificacaoDistribuicaoBoleto': 1,
        'tipoDesconto': 0,
        'tipoMulta': 0,
        'tipoJurosMora': 3,
        'numeroParcela': 1,
        'pagador': {
            'numeroCpfCnpj': '11144477735',
            'nome': 'João Silva',
            'endereco': 'Rua Teste, 123',
            'bairro': 'Centro',
            'cidade': 'São Paulo',
            'cep': '01001000',
            'uf': 'SP',
        },
    }

    # Verifica se exceção é levantada
    with pytest.raises(BoletoEmissaoError) as exc_info:
        boleto_client.emitir_boleto(dados)

    # Verificações
    assert '[400] Falha na emissão do boleto: Dados inválidos' in str(exc_info.value)
    assert exc_info.value.code == 400
    assert exc_info.value.dados_boleto == dados


def test_emitir_boleto_erro_generico(boleto_client: BoletoAPI) -> None:
    """Testa a emissão de boleto com erro genérico"""
    # Configura o mock para erro genérico
    boleto_client.session.post.side_effect = requests.exceptions.RequestException(
        'Erro de conexão'
    )

    dados = {
        'numeroCliente': 123456,
        'codigoModalidade': 1,
        'numeroContaCorrente': 12345,
        'codigoEspecieDocumento': 'DM',
        'dataEmissao': '2024-01-01',
        'dataVencimento': '2024-12-31',
        'valor': 100.50,
        'seuNumero': '123456789',
        'identificacaoEmissaoBoleto': 1,
        'identificacaoDistribuicaoBoleto': 1,
        'tipoDesconto': 0,
        'tipoMulta': 0,
        'tipoJurosMora': 3,
        'numeroParcela': 1,
        'pagador': {
            'numeroCpfCnpj': '11144477735',
            'nome': 'João Silva',
            'endereco': 'Rua Teste, 123',
            'bairro': 'Centro',
            'cidade': 'São Paulo',
            'cep': '01001000',
            'uf': 'SP',
        },
    }

    # Verifica se exceção é levantada
    with pytest.raises(BoletoEmissaoError) as exc_info:
        boleto_client.emitir_boleto(dados)

    # Verificações
    assert 'Falha na comunicação com API de boletos: Erro de conexão' in str(
        exc_info.value
    )
    assert exc_info.value.dados_boleto == dados


def test_emitir_boleto_404_com_dados_validos(boleto_client: BoletoAPI) -> None:
    """Testa emissão com status 404 mas JSON válido (comportamento não-padrão da API)"""
    # Configura o mock para retornar 404 mas com dados válidos
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.headers = {'Content-Type': 'application/json'}
    mock_response.text = '{"resultado": {"nossoNumero": 123456}}'
    mock_response.json.return_value = {
        'resultado': {'nossoNumero': 123456, 'codigoBarras': '123456789'}
    }
    boleto_client.session.post.return_value = mock_response

    dados = {
        'numeroCliente': 123456,
        'codigoModalidade': 1,
        'numeroContaCorrente': 12345,
        'codigoEspecieDocumento': 'DM',
        'dataEmissao': '2024-01-01',
        'dataVencimento': '2024-12-31',
        'valor': 100.50,
        'seuNumero': '123456789',
        'identificacaoEmissaoBoleto': 1,
        'identificacaoDistribuicaoBoleto': 1,
        'tipoDesconto': 0,
        'tipoMulta': 0,
        'tipoJurosMora': 3,
        'numeroParcela': 1,
        'pagador': {
            'numeroCpfCnpj': '11144477735',
            'nome': 'João Silva',
            'endereco': 'Rua Teste, 123',
            'bairro': 'Centro',
            'cidade': 'São Paulo',
            'cep': '01001000',
            'uf': 'SP',
        },
    }

    # Deve processar como sucesso apesar do 404
    resultado = boleto_client.emitir_boleto(dados)

    # Verificações
    assert resultado['resultado']['nossoNumero'] == 123456
    assert resultado['resultado']['codigoBarras'] == '123456789'


def test_emitir_boleto_404_sem_dados(boleto_client: BoletoAPI) -> None:
    """Testa emissão com status 404 sem dados válidos"""
    # Configura o mock para retornar 404 sem dados
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.headers = {'Content-Type': 'application/json'}
    mock_response.text = '{"mensagem": "Não encontrado"}'
    mock_response.json.return_value = {'mensagem': 'Não encontrado'}
    boleto_client.session.post.return_value = mock_response

    dados = {
        'numeroCliente': 123456,
        'codigoModalidade': 1,
        'numeroContaCorrente': 12345,
        'codigoEspecieDocumento': 'DM',
        'dataEmissao': '2024-01-01',
        'dataVencimento': '2024-12-31',
        'valor': 100.50,
        'seuNumero': '123456789',
        'identificacaoEmissaoBoleto': 1,
        'identificacaoDistribuicaoBoleto': 1,
        'tipoDesconto': 0,
        'tipoMulta': 0,
        'tipoJurosMora': 3,
        'numeroParcela': 1,
        'pagador': {
            'numeroCpfCnpj': '11144477735',
            'nome': 'João Silva',
            'endereco': 'Rua Teste, 123',
            'bairro': 'Centro',
            'cidade': 'São Paulo',
            'cep': '01001000',
            'uf': 'SP',
        },
    }

    # Deve lançar exceção
    with pytest.raises(BoletoEmissaoError) as exc_info:
        boleto_client.emitir_boleto(dados)

    # Verificações
    assert exc_info.value.code == 404
    assert 'Boleto não encontrado (404)' in str(exc_info.value)


def test_emitir_e_verificar_boleto_sucesso(boleto_client: BoletoAPI) -> None:
    """Testa emissão e verificação de boleto com sucesso"""
    # Mock da emissão
    mock_emissao = Mock()
    mock_emissao.status_code = 200
    mock_emissao.headers = {'Content-Type': 'application/json'}
    mock_emissao.json.return_value = {
        'resultado': {'nossoNumero': 123456, 'codigoBarras': '123456789'}
    }

    # Mock da consulta (primeira tentativa)
    mock_consulta = Mock()
    mock_consulta.status_code = 200
    mock_consulta.headers = {'Content-Type': 'application/json'}
    mock_consulta.json.return_value = {
        'nossoNumero': 123456,
        'valor': 100.50,
        'dataVencimento': '2024-12-31',
    }

    boleto_client.session.post.return_value = mock_emissao
    boleto_client.session.get.return_value = mock_consulta

    dados = {
        'numeroCliente': 123456,
        'codigoModalidade': 1,
        'numeroContaCorrente': 12345,
        'codigoEspecieDocumento': 'DM',
        'dataEmissao': '2024-01-01',
        'dataVencimento': '2024-12-31',
        'valor': 100.50,
        'seuNumero': '123456789',
        'identificacaoEmissaoBoleto': 1,
        'identificacaoDistribuicaoBoleto': 1,
        'tipoDesconto': 0,
        'tipoMulta': 0,
        'tipoJurosMora': 3,
        'numeroParcela': 1,
        'pagador': {
            'numeroCpfCnpj': '11144477735',
            'nome': 'João Silva',
            'endereco': 'Rua Teste, 123',
            'bairro': 'Centro',
            'cidade': 'São Paulo',
            'cep': '01001000',
            'uf': 'SP',
        },
    }

    # Emite e verifica com delay reduzido para teste
    resultado = boleto_client.emitir_e_verificar_boleto(
        dados, max_tentativas=1, delay_inicial=0.1
    )

    # Verificações
    assert resultado['resultado']['nossoNumero'] == 123456
    assert resultado['resultado']['codigoBarras'] == '123456789'


def test_consultar_boleto_sucesso(boleto_client: BoletoAPI) -> None:
    """Testa a consulta de boleto com sucesso"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {
        'nossoNumero': '123456789',
        'situacao': 'REGISTRADO',
    }
    boleto_client.session.get.return_value = mock_response

    result = boleto_client.consultar_boleto(
        numero_cliente=123456, codigo_modalidade=1, nosso_numero='123456789'
    )

    if result != {'nossoNumero': '123456789', 'situacao': 'REGISTRADO'}:
        raise ValueError('Resultado da consulta não corresponde ao esperado')
    boleto_client.session.get.assert_called_once()
    args, kwargs = boleto_client.session.get.call_args
    if 'boletos' not in args[0]:
        raise ValueError('Endpoint incorreto para consulta de boleto')
    assert kwargs['params']['nossoNumero'] == '123456789'


def test_consultar_boleto_nao_encontrado(boleto_client: BoletoAPI) -> None:
    """Testa a consulta de boleto não encontrado (deve retornar None)"""
    # Configura o mock para 404
    mock_response = Mock()
    http_error = requests.exceptions.HTTPError('404 Not Found')
    http_error.response = mock_response
    mock_response.status_code = 404
    boleto_client.session.get.side_effect = http_error

    result = boleto_client.consultar_boleto(
        numero_cliente=123456, codigo_modalidade=1, nosso_numero='000000000'
    )
    assert result is None
    boleto_client.session.get.assert_called_once()
    args, kwargs = boleto_client.session.get.call_args
    assert kwargs['params']['nossoNumero'] == '000000000'
    assert kwargs['params']['numeroCliente'] == 123456
    assert kwargs['params']['codigoModalidade'] == 1


def test_consultar_boleto_erro_http(boleto_client: BoletoAPI) -> None:
    """Testa a consulta de boleto com erro HTTP"""
    # Configura o mock para erro HTTP (não 404)
    mock_response = Mock()
    http_error = requests.exceptions.HTTPError('500 Server Error')
    http_error.response = mock_response
    mock_response.status_code = 500
    boleto_client.session.get.side_effect = http_error

    # Verifica se exceção é levantada
    with pytest.raises(BoletoConsultaError) as exc_info:
        boleto_client.consultar_boleto(
            numero_cliente=123456, codigo_modalidade=1, nosso_numero='123456789'
        )
    assert '[500] Falha na consulta do boleto - Status: 500' in str(exc_info.value)


def test_consultar_boleto_erro_generico(boleto_client: BoletoAPI) -> None:
    """Testa a consulta de boleto com erro genérico"""
    # Configura o mock para erro genérico
    boleto_client.session.get.side_effect = requests.exceptions.RequestException(
        'Erro de conexão'
    )

    # Verifica se exceção é levantada
    with pytest.raises(BoletoConsultaError) as exc_info:
        boleto_client.consultar_boleto(
            numero_cliente=123456, codigo_modalidade=1, nosso_numero='123456789'
        )

    # Verificações
    assert 'Falha na comunicação com API de boletos: Erro de conexão' in str(
        exc_info.value
    )
    assert exc_info.value.nosso_numero == '123456789'


def test_consultar_boletos_por_pagador_sucesso(boleto_client: BoletoAPI) -> None:
    """Testa a consulta de boletos por pagador com sucesso"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {
        'boletos': [
            {'nossoNumero': '123', 'situacao': 'EM_ABERTO'},
            {'nossoNumero': '456', 'situacao': 'LIQUIDADO'},
        ]
    }
    boleto_client.session.get.return_value = mock_response

    # Chama o método com todos os parâmetros
    result = boleto_client.consultar_boletos_por_pagador(
        numero_cpf_cnpj='12345678901',
        numero_cliente=123456,
        client_id='client-id-123',
        codigo_situacao=1,
        data_inicio='2025-01-01',
        data_fim='2025-06-30',
    )

    # Verificações
    if len(result['boletos']) != 2:
        raise ValueError('Deveriam ser retornados 2 boletos')
    boleto_client.session.get.assert_called_once()
    args, kwargs = boleto_client.session.get.call_args
    if 'pagadores/12345678901/boletos' not in args[0]:
        raise ValueError('Endpoint incorreto para consulta de boletos por pagador')
    assert kwargs['params']['numeroCliente'] == 123456
    assert kwargs['params']['codigoSituacao'] == 1
    assert kwargs['params']['dataInicio'] == '2025-01-01'
    assert kwargs['params']['dataFim'] == '2025-06-30'
    assert kwargs['headers']['client_id'] == 'client-id-123'


def test_consultar_boletos_por_pagador_apenas_obrigatorios(
    boleto_client: BoletoAPI,
) -> None:
    """Testa a consulta de boletos por pagador apenas com parâmetros obrigatórios"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {'boletos': []}
    boleto_client.session.get.return_value = mock_response

    # Chama o método apenas com parâmetros obrigatórios
    result = boleto_client.consultar_boletos_por_pagador(
        numero_cpf_cnpj='12345678901', numero_cliente=123456, client_id='client-id-123'
    )

    # Verificações
    if len(result['boletos']) != 0:
        raise ValueError('Deveria ser retornada lista vazia de boletos')
    args, kwargs = boleto_client.session.get.call_args
    if 'pagadores/12345678901/boletos' not in args[0]:
        raise ValueError('Endpoint incorreto para consulta de boletos por pagador')
    assert kwargs['params']['numeroCliente'] == 123456
    assert 'codigoSituacao' not in kwargs['params']
    assert 'dataInicio' not in kwargs['params']
    assert 'dataFim' not in kwargs['params']


def test_consultar_boletos_por_pagador_erro_http(boleto_client: BoletoAPI) -> None:
    """Testa a consulta de boletos por pagador com erro HTTP"""
    # Configura o mock para erro HTTP
    mock_response = Mock()
    http_error = requests.exceptions.HTTPError('500 Server Error')
    http_error.response = mock_response
    mock_response.status_code = 500
    boleto_client.session.get.side_effect = http_error

    # Verifica se exceção é levantada
    with pytest.raises(BoletoConsultaPagadorError) as exc_info:
        boleto_client.consultar_boletos_por_pagador(
            numero_cpf_cnpj='12345678901',
            numero_cliente=123456,
            client_id='client-id-123',
        )
    assert '[500] Falha na consulta de boletos por pagador - Status: 500' in str(
        exc_info.value
    )
    assert exc_info.value.numero_cpf_cnpj == '12345678901'


def test_consultar_boletos_por_pagador_erro_generico(boleto_client: BoletoAPI) -> None:
    """Testa a consulta de boletos por pagador com erro genérico"""
    # Configura o mock para erro genérico
    boleto_client.session.get.side_effect = requests.exceptions.RequestException(
        'Erro de conexão'
    )

    # Verifica se exceção é levantada
    with pytest.raises(BoletoConsultaPagadorError) as exc_info:
        boleto_client.consultar_boletos_por_pagador(
            numero_cpf_cnpj='12345678901',
            numero_cliente=123456,
            client_id='client-id-123',
        )
    assert 'Falha na comunicação com API de boletos: Erro de conexão' in str(
        exc_info.value
    )
    assert exc_info.value.numero_cpf_cnpj == '12345678901'


def test_atualizar_webhook_sucesso(boleto_client: BoletoAPI) -> None:
    """Testa a atualização de webhook com sucesso (status 204)"""
    # Configura o mock
    mock_response = Mock()
    mock_response.status_code = 204
    boleto_client.session.patch.return_value = mock_response

    # Dados de teste
    id_webhook = 123
    webhook = {
        'url': 'https://new-webhook.example.com/notificacoes',
        'email': 'novo-email@empresa.com',
    }
    client_id = 'client-id-123'

    # Chama o método
    result = boleto_client.atualizar_webhook(
        id_webhook=id_webhook, webhook=webhook, client_id=client_id
    )

    # Verificações
    assert result is None  # Método deve retornar None em caso de sucesso
    boleto_client.session.patch.assert_called_once()
    args, kwargs = boleto_client.session.patch.call_args
    assert f'webhooks/{id_webhook}' in args[0]
    assert kwargs['json'] == webhook
    assert kwargs['headers']['client_id'] == client_id


def test_atualizar_webhook_erro_negocio(boleto_client: BoletoAPI) -> None:
    """Testa erro de negócio (400) na atualização de webhook"""
    # Configura o mock para erro 400
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'URL de webhook inválida', 'codigo': 'ERR001'}]
    }
    boleto_client.session.patch.return_value = mock_response

    # Dados de teste
    id_webhook = 123
    webhook = {'url': 'url-invalida', 'email': 'novo-email@empresa.com'}
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.atualizar_webhook(
            id_webhook=id_webhook, webhook=webhook, client_id=client_id
        )

    # Verificações
    assert '[400] Falha na atualização do webhook: URL de webhook inválida' in str(
        exc_info.value
    )
    assert exc_info.value.code == 400
    assert exc_info.value.id_webhook == id_webhook
    assert exc_info.value.dados_webhook == webhook


def test_atualizar_webhook_erro_dados_inconsistentes(boleto_client: BoletoAPI) -> None:
    """Testa erro de dados inconsistentes (406) na atualização de webhook"""
    # Configura o mock para erro 406
    mock_response = Mock()
    mock_response.status_code = 406
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Email inválido', 'codigo': 'ERR002'}]
    }
    boleto_client.session.patch.return_value = mock_response

    # Dados de teste
    id_webhook = 123
    webhook = {
        'url': 'https://new-webhook.example.com/notificacoes',
        'email': 'email-invalido',
    }
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.atualizar_webhook(
            id_webhook=id_webhook, webhook=webhook, client_id=client_id
        )

    # Verificações
    assert '[406] Falha na atualização do webhook: Email inválido' in str(
        exc_info.value
    )
    assert exc_info.value.code == 406
    assert exc_info.value.id_webhook == id_webhook
    assert exc_info.value.dados_webhook == webhook


def test_atualizar_webhook_erro_interno(boleto_client: BoletoAPI) -> None:
    """Testa erro interno (500) na atualização de webhook"""
    # Configura o mock para erro 500
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Erro interno no servidor', 'codigo': 'ERR500'}]
    }
    boleto_client.session.patch.return_value = mock_response

    # Dados de teste
    id_webhook = 123
    webhook = {
        'url': 'https://new-webhook.example.com/notificacoes',
        'email': 'novo-email@empresa.com',
    }
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.atualizar_webhook(
            id_webhook=id_webhook, webhook=webhook, client_id=client_id
        )

    # Verificações
    assert '[500] Falha na atualização do webhook: Erro interno no servidor' in str(
        exc_info.value
    )
    assert exc_info.value.code == 500
    assert exc_info.value.id_webhook == id_webhook
    assert exc_info.value.dados_webhook == webhook


def test_atualizar_webhook_erro_comunicacao(boleto_client: BoletoAPI) -> None:
    """Testa erro de comunicação na atualização de webhook"""
    # Configura o mock para erro de comunicação
    boleto_client.session.patch.side_effect = requests.exceptions.RequestException(
        'Erro de conexão'
    )

    # Dados de teste
    id_webhook = 123
    webhook = {
        'url': 'https://new-webhook.example.com/notificacoes',
        'email': 'novo-email@empresa.com',
    }
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.atualizar_webhook(
            id_webhook=id_webhook, webhook=webhook, client_id=client_id
        )

    # Verificações
    assert 'Falha na comunicação com API de boletos: Erro de conexão' in str(
        exc_info.value
    )
    assert exc_info.value.id_webhook == id_webhook
    assert exc_info.value.dados_webhook == webhook


def test_emitir_segunda_via_sucesso(boleto_client: BoletoAPI) -> None:
    """Testa a emissão de segunda via de boleto com sucesso"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {
        'nossoNumero': '123456789',
        'linhaDigitavel': '00190000090123456789012345678901234567890000',
        'pdfBase64': None,
    }
    boleto_client.session.get.return_value = mock_response

    # Chama o método
    result = boleto_client.emitir_segunda_via(
        numero_cliente=123456, codigo_modalidade=1, nosso_numero=987654321
    )

    # Verificações
    assert 'nossoNumero' in result
    assert 'linhaDigitavel' in result
    boleto_client.session.get.assert_called_once()
    args, kwargs = boleto_client.session.get.call_args
    assert 'boletos/segunda-via' in args[0]
    assert kwargs['params']['numeroCliente'] == 123456
    assert kwargs['params']['codigoModalidade'] == 1
    assert kwargs['params']['nossoNumero'] == 987654321
    assert kwargs['params']['gerarPdf'] == 'false'


def test_emitir_segunda_via_com_pdf(boleto_client: BoletoAPI) -> None:
    """Testa a emissão de segunda via com PDF"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {'pdfBase64': 'JVBERi0xLjQK...'}
    boleto_client.session.get.return_value = mock_response

    # Chama o método com gerar_pdf=True
    result = boleto_client.emitir_segunda_via(
        numero_cliente=123456,
        codigo_modalidade=1,
        linha_digitavel='00190000090123456789012345678901234567890000',
        gerar_pdf=True,
    )

    # Verificações
    assert 'pdfBase64' in result
    args, kwargs = boleto_client.session.get.call_args
    assert (
        kwargs['params']['linhaDigitavel']
        == '00190000090123456789012345678901234567890000'
    )
    assert kwargs['params']['gerarPdf'] == 'true'


def test_emitir_segunda_via_com_codigo_barras(boleto_client: BoletoAPI) -> None:
    """Testa a emissão de segunda via usando código de barras"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {
        'nossoNumero': '123456789',
        'linhaDigitavel': '00190000090123456789012345678901234567890000',
    }
    boleto_client.session.get.return_value = mock_response

    # Chama o método com código de barras
    result = boleto_client.emitir_segunda_via(
        numero_cliente=123456,
        codigo_modalidade=1,
        codigo_barras='00190000090123456789012345678901234567890000',
    )

    # Verificações
    assert 'nossoNumero' in result
    assert 'linhaDigitavel' in result
    args, kwargs = boleto_client.session.get.call_args
    assert (
        kwargs['params']['codigoBarras']
        == '00190000090123456789012345678901234567890000'
    )
    assert 'nossoNumero' not in kwargs['params']
    assert 'linhaDigitavel' not in kwargs['params']


def test_emitir_segunda_via_erro_http(boleto_client: BoletoAPI) -> None:
    """Testa a emissão de segunda via com erro HTTP"""
    # Configura o mock para erro HTTP
    mock_response = Mock()
    http_error = requests.exceptions.HTTPError('400 Bad Request')
    http_error.response = mock_response
    mock_response.status_code = 400
    boleto_client.session.get.side_effect = http_error

    # Verifica se exceção é levantada
    with pytest.raises(BoletoEmissaoError) as exc_info:
        boleto_client.emitir_segunda_via(
            numero_cliente=123456, codigo_modalidade=1, nosso_numero=987654321
        )
    assert '[400] Falha na emissão da segunda via - Status: 400' in str(exc_info.value)
    assert exc_info.value.code == 400


def test_emitir_segunda_via_erro_generico(boleto_client: BoletoAPI) -> None:
    """Testa a emissão de segunda via com erro genérico"""
    # Configura o mock para erro genérico
    boleto_client.session.get.side_effect = requests.exceptions.RequestException(
        'Erro de conexão'
    )

    # Verifica se exceção é levantada
    with pytest.raises(BoletoEmissaoError) as exc_info:
        boleto_client.emitir_segunda_via(
            numero_cliente=123456, codigo_modalidade=1, nosso_numero=987654321
        )

    # Verificações
    assert 'Falha na comunicação com API de boletos: Erro de conexão' in str(
        exc_info.value
    )
    params = {
        'numeroCliente': 123456,
        'codigoModalidade': 1,
        'nossoNumero': 987654321,
        'gerarPdf': 'false',
    }
    assert exc_info.value.dados_boleto == params


def test_consultar_faixas_nosso_numero_sucesso(boleto_client: BoletoAPI) -> None:
    """Testa a consulta de faixas de nosso número com sucesso"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {
        'resultado': [
            {
                'numeroInicial': 1000,
                'numeroFinal': 1100,
                'validaDigitoVerificadorNossoNumero': 0,
                'numeroCliente': 123456,
                'codigoModalidade': 1,
                'quantidade': 100,
                'numeroContratoCobranca': 789,
            }
        ]
    }
    mock_response.status_code = 200
    boleto_client.session.get.return_value = mock_response

    # Chama o método com todos os parâmetros
    result = boleto_client.consultar_faixas_nosso_numero(
        numero_cliente=123456,
        codigo_modalidade=1,
        quantidade=100,
        client_id='client-id-123',
        numero_contrato_cobranca=789,
    )

    # Verificações
    if result['numeroInicial'] != 1000:
        raise ValueError('Número inicial incorreto')
    if result['numeroFinal'] != 1100:
        raise ValueError('Número final incorreto')
    if result['validaDigitoVerificadorNossoNumero'] != 0:
        raise ValueError('Validação de dígito verificador incorreta')
    boleto_client.session.get.assert_called_once()
    args, kwargs = boleto_client.session.get.call_args
    assert 'boletos/faixas-nosso-numero' in args[0]
    assert kwargs['params']['numeroCliente'] == 123456
    assert kwargs['params']['codigoModalidade'] == 1
    assert kwargs['params']['quantidade'] == 100
    assert kwargs['params']['numeroContratoCobranca'] == 789
    assert kwargs['headers']['client_id'] == 'client-id-123'


def test_consultar_faixas_nosso_numero_sem_contrato(boleto_client: BoletoAPI) -> None:
    """Testa a consulta sem número de contrato de cobrança"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {
        'resultado': [
            {
                'numeroInicial': 5000,
                'numeroFinal': 5100,
                'validaDigitoVerificadorNossoNumero': 1,
                'numeroCliente': 123456,
                'codigoModalidade': 1,
                'quantidade': 100,
            }
        ]
    }
    mock_response.status_code = 200
    boleto_client.session.get.return_value = mock_response

    # Chama o método sem contrato de cobrança
    result = boleto_client.consultar_faixas_nosso_numero(
        numero_cliente=123456,
        codigo_modalidade=1,
        quantidade=100,
        client_id='client-id-123',
    )

    # Verificações
    if result['validaDigitoVerificadorNossoNumero'] != 1:
        raise ValueError('Validação de dígito verificador incorreta')
    args, kwargs = boleto_client.session.get.call_args
    if 'numeroContratoCobranca' in kwargs['params']:
        raise ValueError('Parâmetro numeroContratoCobranca não deveria estar presente')


def test_consultar_faixas_nosso_numero_erro_http(boleto_client: BoletoAPI) -> None:
    """Testa a consulta com erro HTTP"""
    # Configura o mock para erro HTTP
    mock_response = Mock()
    http_error = requests.exceptions.HTTPError('400 Bad Request')
    http_error.response = mock_response
    mock_response.status_code = 400
    boleto_client.session.get.side_effect = http_error

    # Verifica se exceção é levantada
    with pytest.raises(BoletoConsultaFaixaError) as exc_info:
        boleto_client.consultar_faixas_nosso_numero(
            numero_cliente=123456,
            codigo_modalidade=1,
            quantidade=100,
            client_id='client-id-123',
        )
    assert '[400] Falha na consulta de faixas - Status: 400' in str(exc_info.value)
    assert exc_info.value.numero_cliente == 123456


def test_consultar_faixas_nosso_numero_erro_generico(boleto_client: BoletoAPI) -> None:
    """Testa a consulta com erro genérico"""
    # Configura o mock para erro genérico
    boleto_client.session.get.side_effect = requests.exceptions.RequestException(
        'Erro de conexão'
    )

    # Verifica se exceção é levantada
    with pytest.raises(BoletoConsultaFaixaError) as exc_info:
        boleto_client.consultar_faixas_nosso_numero(
            numero_cliente=123456,
            codigo_modalidade=1,
            quantidade=100,
            client_id='client-id-123',
        )
    assert 'Falha na comunicação com API de boletos: Erro de conexão' in str(
        exc_info.value
    )
    assert exc_info.value.numero_cliente == 123456


def test_consultar_faixas_nosso_numero_estrutura_resultado(
    boleto_client: BoletoAPI,
) -> None:
    """Testa a estrutura de resposta com array resultado"""
    # Configura o mock
    mock_response = Mock()
    mock_response.json.return_value = {
        'resultado': [
            {
                'numeroCliente': 5224,
                'nome': 'JOSE PEREIRA',
                'codigoModalidade': 1,
                'numeroInicial': 1,
                'numeroFinal': 10,
                'quantidade': 10,
                'numeroContratoCobranca': 1,
                'validaDigitoVerificadorNossoNumero': True,
            }
        ]
    }
    mock_response.status_code = 200
    boleto_client.session.get.return_value = mock_response

    # Chama o método
    result = boleto_client.consultar_faixas_nosso_numero(
        numero_cliente=5224,
        codigo_modalidade=1,
        quantidade=10,
        client_id='client-id-123',
    )

    # Verificações
    if result['numeroInicial'] != 1:
        raise ValueError('Número inicial incorreto')
    if result['numeroFinal'] != 10:
        raise ValueError('Número final incorreto')
    if result['validaDigitoVerificadorNossoNumero'] != 1:  # Deve converter True para 1
        raise ValueError('Validação de dígito verificador incorreta')


def test_consultar_faixas_nosso_numero_erro_negocio(boleto_client: BoletoAPI) -> None:
    """Testa erro de negócio (400)"""
    # Configura o mock para erro 400
    mock_response = Mock()
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Parâmetros inválidos', 'codigo': 'ERR001'}]
    }
    mock_response.status_code = 400
    boleto_client.session.get.return_value = mock_response

    # Verifica se exceção é levantada
    with pytest.raises(BoletoConsultaFaixaError) as exc_info:
        boleto_client.consultar_faixas_nosso_numero(
            numero_cliente=5224,
            codigo_modalidade=1,
            quantidade=10,
            client_id='client-id-123',
        )
    assert 'Parâmetros inválidos' in str(exc_info.value)
    assert exc_info.value.code == 400


def test_consultar_faixas_nosso_numero_erro_dados(boleto_client: BoletoAPI) -> None:
    """Testa erro de dados inconsistentes (406)"""
    # Configura o mock para erro 406
    mock_response = Mock()
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Dados inconsistentes', 'codigo': 'ERR002'}]
    }
    mock_response.status_code = 406
    boleto_client.session.get.return_value = mock_response

    # Verifica se exceção é levantada
    with pytest.raises(BoletoConsultaFaixaError) as exc_info:
        boleto_client.consultar_faixas_nosso_numero(
            numero_cliente=5224,
            codigo_modalidade=1,
            quantidade=10,
            client_id='client-id-123',
        )
    assert 'Dados inconsistentes' in str(exc_info.value)
    assert exc_info.value.code == 406


def test_consultar_faixas_nosso_numero_sem_resultados(boleto_client: BoletoAPI) -> None:
    """Testa quando não há faixas disponíveis"""
    # Configura o mock para resposta vazia
    mock_response = Mock()
    mock_response.json.return_value = {'resultado': []}
    mock_response.status_code = 200
    boleto_client.session.get.return_value = mock_response

    # Verifica se exceção é levantada
    with pytest.raises(BoletoConsultaFaixaError) as exc_info:
        boleto_client.consultar_faixas_nosso_numero(
            numero_cliente=5224,
            codigo_modalidade=1,
            quantidade=10,
            client_id='client-id-123',
        )
    assert 'Nenhuma faixa disponível encontrada' in str(exc_info.value)
    assert exc_info.value.code == 404


def test_alterar_boleto_sucesso(boleto_client: BoletoAPI) -> None:
    """Testa a alteração de boleto com sucesso (status 204)"""
    # Configura o mock
    mock_response = Mock()
    mock_response.status_code = 204
    boleto_client.session.patch.return_value = mock_response

    # Dados de teste
    nosso_numero = 123456789
    dados_alteracao = {
        'desconto': {
            'tipoDesconto': 1,
            'dataPrimeiroDesconto': '2025-06-10',
            'valorPrimeiroDesconto': 10.50,
        }
    }
    client_id = 'client-id-123'

    # Chama o método
    result = boleto_client.alterar_boleto(
        nosso_numero=nosso_numero, dados_alteracao=dados_alteracao, client_id=client_id
    )

    # Verificações
    assert result is None  # Método deve retornar None em caso de sucesso
    boleto_client.session.patch.assert_called_once()
    args, kwargs = boleto_client.session.patch.call_args
    assert f'boletos/{nosso_numero}' in args[0]
    assert kwargs['json'] == dados_alteracao
    assert kwargs['headers']['client_id'] == client_id


def test_alterar_boleto_erro_negocio(boleto_client: BoletoAPI) -> None:
    """Testa erro de negócio (400) na alteração de boleto"""
    # Configura o mock para erro 400
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Erro de negócio', 'codigo': 'ERR001'}]
    }
    boleto_client.session.patch.return_value = mock_response

    # Dados de teste
    nosso_numero = 123456789
    dados_alteracao = {
        'seuNumero': {'seuNumero': '123', 'identificacaoBoletoEmpresa': '123'}
    }
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoAlteracaoError) as exc_info:
        boleto_client.alterar_boleto(
            nosso_numero=nosso_numero,
            dados_alteracao=dados_alteracao,
            client_id=client_id,
        )

    # Verificações
    assert '[400] Falha na alteração do boleto: Erro de negócio' in str(exc_info.value)
    assert exc_info.value.code == 400
    assert exc_info.value.nosso_numero == str(nosso_numero)
    assert exc_info.value.dados_alteracao == dados_alteracao


def test_alterar_boleto_erro_dados_inconsistentes(boleto_client: BoletoAPI) -> None:
    """Testa erro de dados inconsistentes (406) na alteração de boleto"""
    # Configura o mock para erro 406
    mock_response = Mock()
    mock_response.status_code = 406
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Dados inconsistentes', 'codigo': 'ERR002'}]
    }
    boleto_client.session.patch.return_value = mock_response

    # Dados de teste
    nosso_numero = 123456789
    dados_alteracao = {
        'jurosMora': {
            'tipoJurosMora': 2,
            'dataJurosMora': '2025-06-15',
            'valorJurosMora': 5.0,
        }
    }
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoAlteracaoError) as exc_info:
        boleto_client.alterar_boleto(
            nosso_numero=nosso_numero,
            dados_alteracao=dados_alteracao,
            client_id=client_id,
        )

    # Verificações
    assert '[406] Falha na alteração do boleto: Dados inconsistentes' in str(
        exc_info.value
    )
    assert exc_info.value.code == 406
    assert exc_info.value.nosso_numero == str(nosso_numero)
    assert exc_info.value.dados_alteracao == dados_alteracao


def test_alterar_boleto_erro_interno(boleto_client: BoletoAPI) -> None:
    """Testa erro interno (500) na alteração de boleto"""
    # Configura o mock para erro 500
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Erro interno no servidor', 'codigo': 'ERR500'}]
    }
    boleto_client.session.patch.return_value = mock_response

    # Dados de teste
    nosso_numero = 123456789
    dados_alteracao = {
        'multa': {'tipoMulta': 1, 'dataMulta': '2025-06-20', 'valorMulta': 2.5}
    }
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoAlteracaoError) as exc_info:
        boleto_client.alterar_boleto(
            nosso_numero=nosso_numero,
            dados_alteracao=dados_alteracao,
            client_id=client_id,
        )

    # Verificações
    assert '[500] Falha na alteração do boleto: Erro interno no servidor' in str(
        exc_info.value
    )
    assert exc_info.value.code == 500
    assert exc_info.value.nosso_numero == str(nosso_numero)
    assert exc_info.value.dados_alteracao == dados_alteracao


def test_alterar_boleto_erro_comunicacao(boleto_client: BoletoAPI) -> None:
    """Testa erro de comunicação na alteração de boleto"""
    # Configura o mock para erro de comunicação
    boleto_client.session.patch.side_effect = requests.exceptions.RequestException(
        'Erro de conexão'
    )

    # Dados de teste
    nosso_numero = 123456789
    dados_alteracao = {'pix': {'utilizarPix': True}}
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoAlteracaoError) as exc_info:
        boleto_client.alterar_boleto(
            nosso_numero=nosso_numero,
            dados_alteracao=dados_alteracao,
            client_id=client_id,
        )

    # Verificações
    assert 'Falha na comunicação com API de boletos: Erro de conexão' in str(
        exc_info.value
    )
    assert exc_info.value.nosso_numero == str(nosso_numero)
    assert exc_info.value.dados_alteracao == dados_alteracao


def test_baixar_boleto_sucesso(boleto_client: BoletoAPI) -> None:
    """Testa a baixa de boleto com sucesso (status 204)"""
    # Configura o mock
    mock_response = Mock()
    mock_response.status_code = 204
    boleto_client.session.post.return_value = mock_response

    # Dados de teste
    nosso_numero = 123456789
    dados_boleto = {'numeroCliente': 5224, 'codigoModalidade': 1}
    client_id = 'client-id-123'

    # Chama o método
    result = boleto_client.baixar_boleto(
        nosso_numero=nosso_numero, dados_boleto=dados_boleto, client_id=client_id
    )

    # Verificações
    assert result is None  # Método deve retornar None em caso de sucesso
    boleto_client.session.post.assert_called_once()
    args, kwargs = boleto_client.session.post.call_args
    assert f'boletos/{nosso_numero}/baixar' in args[0]
    assert kwargs['json'] == dados_boleto
    assert kwargs['headers']['client_id'] == client_id


def test_baixar_boleto_erro_negocio(boleto_client: BoletoAPI) -> None:
    """Testa erro de negócio (400) na baixa de boleto"""
    # Configura o mock para erro 400
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Boleto já baixado', 'codigo': 'ERR001'}]
    }
    boleto_client.session.post.return_value = mock_response

    # Dados de teste
    nosso_numero = 123456789
    dados_boleto = {'numeroCliente': 5224, 'codigoModalidade': 1}
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoBaixaError) as exc_info:
        boleto_client.baixar_boleto(
            nosso_numero=nosso_numero, dados_boleto=dados_boleto, client_id=client_id
        )

    # Verificações
    assert '[400] Falha na baixa do boleto: Boleto já baixado' in str(exc_info.value)
    assert exc_info.value.code == 400
    assert exc_info.value.nosso_numero == nosso_numero
    assert exc_info.value.dados_boleto == dados_boleto


def test_baixar_boleto_erro_dados_inconsistentes(boleto_client: BoletoAPI) -> None:
    """Testa erro de dados inconsistentes (406) na baixa de boleto"""
    # Configura o mock para erro 406
    mock_response = Mock()
    mock_response.status_code = 406
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Dados inconsistentes', 'codigo': 'ERR002'}]
    }
    boleto_client.session.post.return_value = mock_response

    # Dados de teste
    nosso_numero = 123456789
    dados_boleto = {'numeroCliente': 5224, 'codigoModalidade': 1}
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoBaixaError) as exc_info:
        boleto_client.baixar_boleto(
            nosso_numero=nosso_numero, dados_boleto=dados_boleto, client_id=client_id
        )

    # Verificações
    assert '[406] Falha na baixa do boleto: Dados inconsistentes' in str(exc_info.value)
    assert exc_info.value.code == 406
    assert exc_info.value.nosso_numero == nosso_numero
    assert exc_info.value.dados_boleto == dados_boleto


def test_baixar_boleto_erro_interno(boleto_client: BoletoAPI) -> None:
    """Testa erro interno (500) na baixa de boleto"""
    # Configura o mock para erro 500
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Erro interno no servidor', 'codigo': 'ERR500'}]
    }
    boleto_client.session.post.return_value = mock_response

    # Dados de teste
    nosso_numero = 123456789
    dados_boleto = {'numeroCliente': 5224, 'codigoModalidade': 1}
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoBaixaError) as exc_info:
        boleto_client.baixar_boleto(
            nosso_numero=nosso_numero, dados_boleto=dados_boleto, client_id=client_id
        )

    # Verificações
    assert '[500] Falha na baixa do boleto: Erro interno no servidor' in str(
        exc_info.value
    )
    assert exc_info.value.code == 500
    assert exc_info.value.nosso_numero == nosso_numero
    assert exc_info.value.dados_boleto == dados_boleto


def test_baixar_boleto_erro_comunicacao(boleto_client: BoletoAPI) -> None:
    """Testa erro de comunicação na baixa de boleto"""
    # Configura o mock para erro de comunicação
    boleto_client.session.post.side_effect = requests.exceptions.RequestException(
        'Erro de conexão'
    )

    # Dados de teste
    nosso_numero = 123456789
    dados_boleto = {'numeroCliente': 5224, 'codigoModalidade': 1}
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoBaixaError) as exc_info:
        boleto_client.baixar_boleto(
            nosso_numero=nosso_numero, dados_boleto=dados_boleto, client_id=client_id
        )

    # Verificações
    assert 'Falha na comunicação com API de boletos: Erro de conexão' in str(
        exc_info.value
    )
    assert exc_info.value.nosso_numero == nosso_numero
    assert exc_info.value.dados_boleto == dados_boleto


def test_alterar_pagador_sucesso(boleto_client: BoletoAPI) -> None:
    """Testa a alteração de pagador com sucesso (status 204)"""
    # Configura o mock
    mock_response = Mock()
    mock_response.status_code = 204
    boleto_client.session.put.return_value = mock_response

    # Dados de teste
    pagador = {
        'numeroCliente': 5224,
        'numeroCpfCnpj': '12345678901',
        'nome': 'Fulano de Tal',
        'endereco': 'Rua Teste, 123',
        'bairro': 'Centro',
        'cidade': 'São Paulo',
        'cep': '01001000',
        'uf': 'SP',
        'email': 'fulano@teste.com',
    }
    client_id = 'client-id-123'

    # Chama o método
    result = boleto_client.alterar_pagador(pagador=pagador, client_id=client_id)

    # Verificações
    assert result is None  # Método deve retornar None em caso de sucesso
    boleto_client.session.put.assert_called_once()
    args, kwargs = boleto_client.session.put.call_args
    assert 'pagadores' in args[0]
    assert kwargs['json'] == pagador
    assert kwargs['headers']['client_id'] == client_id


def test_alterar_pagador_erro_negocio(boleto_client: BoletoAPI) -> None:
    """Testa erro de negócio (400) na alteração de pagador"""
    # Configura o mock para erro 400
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Pagador não encontrado', 'codigo': 'ERR001'}]
    }
    boleto_client.session.put.return_value = mock_response

    # Dados de teste
    pagador = {
        'numeroCliente': 5224,
        'numeroCpfCnpj': '12345678901',
        'nome': 'Fulano de Tal',
    }
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoAlteracaoPagadorError) as exc_info:
        boleto_client.alterar_pagador(pagador=pagador, client_id=client_id)

    # Verificações
    assert '[400] Falha na alteração do pagador: Pagador não encontrado' in str(
        exc_info.value
    )
    assert exc_info.value.code == 400
    assert exc_info.value.numero_cpf_cnpj == '12345678901'
    assert exc_info.value.dados_pagador == pagador


def test_alterar_pagador_erro_dados_inconsistentes(boleto_client: BoletoAPI) -> None:
    """Testa erro de dados inconsistentes (406) na alteração de pagador"""
    # Configura o mock para erro 406
    mock_response = Mock()
    mock_response.status_code = 406
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Dados inconsistentes', 'codigo': 'ERR002'}]
    }
    boleto_client.session.put.return_value = mock_response

    # Dados de teste
    pagador = {
        'numeroCliente': 5224,
        'numeroCpfCnpj': '12345678901',
        'nome': 'Fulano de Tal',
        'email': 'email-invalido',
    }
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoAlteracaoPagadorError) as exc_info:
        boleto_client.alterar_pagador(pagador=pagador, client_id=client_id)

    # Verificações
    assert '[406] Falha na alteração do pagador: Dados inconsistentes' in str(
        exc_info.value
    )
    assert exc_info.value.code == 406
    assert exc_info.value.numero_cpf_cnpj == '12345678901'
    assert exc_info.value.dados_pagador == pagador


def test_alterar_pagador_erro_interno(boleto_client: BoletoAPI) -> None:
    """Testa erro interno (500) na alteração de pagador"""
    # Configura o mock para erro 500
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Erro interno no servidor', 'codigo': 'ERR500'}]
    }
    boleto_client.session.put.return_value = mock_response

    # Dados de teste
    pagador = {
        'numeroCliente': 5224,
        'numeroCpfCnpj': '12345678901',
        'nome': 'Fulano de Tal',
    }
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoAlteracaoPagadorError) as exc_info:
        boleto_client.alterar_pagador(pagador=pagador, client_id=client_id)

    # Verificações
    assert '[500] Falha na alteração do pagador: Erro interno no servidor' in str(
        exc_info.value
    )
    assert exc_info.value.code == 500
    assert exc_info.value.numero_cpf_cnpj == '12345678901'
    assert exc_info.value.dados_pagador == pagador


def test_alterar_pagador_erro_comunicacao(boleto_client: BoletoAPI) -> None:
    """Testa erro de comunicação na alteração de pagador"""
    # Configura o mock para erro de comunicação
    boleto_client.session.put.side_effect = requests.exceptions.RequestException(
        'Erro de conexão'
    )

    # Dados de teste
    pagador = {
        'numeroCliente': 5224,
        'numeroCpfCnpj': '12345678901',
        'nome': 'Fulano de Tal',
    }
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoAlteracaoPagadorError) as exc_info:
        boleto_client.alterar_pagador(pagador=pagador, client_id=client_id)

    # Verificações
    assert 'Falha na comunicação com API de boletos: Erro de conexão' in str(
        exc_info.value
    )
    assert exc_info.value.numero_cpf_cnpj == '12345678901'
    assert exc_info.value.dados_pagador == pagador


def test_cadastrar_webhook_sucesso(boleto_client: BoletoAPI) -> None:
    """Testa o cadastro de webhook com sucesso (status 201)"""
    # Configura o mock
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        'url': 'https://webhook.example.com/notificacoes',
        'codigoTipoMovimento': 7,
        'codigoPeriodoMovimento': 1,
    }
    boleto_client.session.post.return_value = mock_response

    # Dados de teste
    webhook = {
        'url': 'https://webhook.example.com/notificacoes',
        'codigoTipoMovimento': 7,
        'codigoPeriodoMovimento': 1,
        'email': 'notificacoes@empresa.com',
    }
    client_id = 'client-id-123'

    # Chama o método
    result = boleto_client.cadastrar_webhook(webhook=webhook, client_id=client_id)

    # Verificações
    assert result['url'] == webhook['url']
    assert result['codigoTipoMovimento'] == webhook['codigoTipoMovimento']
    boleto_client.session.post.assert_called_once()
    args, kwargs = boleto_client.session.post.call_args
    assert 'webhooks' in args[0]
    assert kwargs['json'] == webhook
    assert kwargs['headers']['client_id'] == client_id


def test_cadastrar_webhook_erro_negocio(boleto_client: BoletoAPI) -> None:
    """Testa erro de negócio (400) no cadastro de webhook"""
    # Configura o mock para erro 400
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'URL de webhook inválida', 'codigo': 'ERR001'}]
    }
    boleto_client.session.post.return_value = mock_response

    # Dados de teste
    webhook = {
        'url': 'https://webhook-invalido.com',
        'codigoTipoMovimento': 7,
        'codigoPeriodoMovimento': 1,
    }
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.cadastrar_webhook(webhook=webhook, client_id=client_id)

    # Verificações
    assert '[400] Falha no cadastro do webhook: URL de webhook inválida' in str(
        exc_info.value
    )
    assert exc_info.value.code == 400
    assert exc_info.value.url == 'https://webhook-invalido.com'
    assert exc_info.value.dados_webhook == webhook


def test_cadastrar_webhook_erro_dados_inconsistentes(boleto_client: BoletoAPI) -> None:
    """Testa erro de dados inconsistentes (406) no cadastro de webhook"""
    # Configura o mock para erro 406
    mock_response = Mock()
    mock_response.status_code = 406
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Tipo de movimento inválido', 'codigo': 'ERR002'}]
    }
    boleto_client.session.post.return_value = mock_response

    # Dados de teste
    webhook = {
        'url': 'https://webhook.example.com/notificacoes',
        'codigoTipoMovimento': 99,  # Inválido
        'codigoPeriodoMovimento': 1,
    }
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.cadastrar_webhook(webhook=webhook, client_id=client_id)

    # Verificações
    assert '[406] Falha no cadastro do webhook: Tipo de movimento inválido' in str(
        exc_info.value
    )
    assert exc_info.value.code == 406
    assert exc_info.value.url == webhook['url']
    assert exc_info.value.dados_webhook == webhook


def test_cadastrar_webhook_erro_interno(boleto_client: BoletoAPI) -> None:
    """Testa erro interno (500) no cadastro de webhook"""
    # Configura o mock para erro 500
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Erro interno no servidor', 'codigo': 'ERR500'}]
    }
    boleto_client.session.post.return_value = mock_response

    # Dados de teste
    webhook = {
        'url': 'https://webhook.example.com/notificacoes',
        'codigoTipoMovimento': 7,
        'codigoPeriodoMovimento': 1,
    }
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.cadastrar_webhook(webhook=webhook, client_id=client_id)

    # Verificações
    assert '[500] Falha no cadastro do webhook: Erro interno no servidor' in str(
        exc_info.value
    )
    assert exc_info.value.code == 500
    assert exc_info.value.url == webhook['url']
    assert exc_info.value.dados_webhook == webhook


def test_cadastrar_webhook_erro_comunicacao(boleto_client: BoletoAPI) -> None:
    """Testa erro de comunicação no cadastro de webhook"""
    # Configura o mock para erro de comunicação
    boleto_client.session.post.side_effect = requests.exceptions.RequestException(
        'Erro de conexão'
    )

    # Dados de teste
    webhook = {
        'url': 'https://webhook.example.com/notificacoes',
        'codigoTipoMovimento': 7,
        'codigoPeriodoMovimento': 1,
    }
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.cadastrar_webhook(webhook=webhook, client_id=client_id)

    # Verificações
    assert 'Falha na comunicação com API de boletos: Erro de conexão' in str(
        exc_info.value
    )
    assert exc_info.value.url == webhook['url']
    assert exc_info.value.dados_webhook == webhook


def test_consultar_webhook_sucesso(boleto_client: BoletoAPI) -> None:
    """Testa a consulta de webhook com sucesso"""
    # Configura o mock
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'resultado': [
            {
                'idWebhook': 123,
                'url': 'https://webhook.example.com/notificacoes',
                'email': 'notificacoes@empresa.com',
                'codigoTipoMovimento': 7,
                'descricaoTipoMovimento': 'Pagamento (Baixa operacional)',
                'codigoPeriodoMovimento': 1,
                'descricaoPeriodoMovimento': 'Movimento atual (D0)',
                'codigoSituacao': 3,
                'descricaoSituacao': 'Inativo',
                'dataHoraCadastro': '2025-06-01T10:00:00.000Z',
                'dataHoraUltimaAlteracao': '2025-06-05T15:30:00.000Z',
                'dataHoraInativacao': '2025-06-05T15:30:00.000Z',
                'descricaoMotivoInativacao': 'Erro ao enviar notificação',
            }
        ]
    }
    boleto_client.session.get.return_value = mock_response

    # Dados de teste
    id_webhook = 123
    codigo_tipo_movimento = 7
    client_id = 'client-id-123'

    # Chama o método
    result = boleto_client.consultar_webhook(
        id_webhook=id_webhook,
        codigo_tipo_movimento=codigo_tipo_movimento,
        client_id=client_id,
    )

    # Verificações
    assert 'resultado' in result
    assert len(result['resultado']) == 1
    assert result['resultado'][0]['idWebhook'] == id_webhook
    boleto_client.session.get.assert_called_once()
    args, kwargs = boleto_client.session.get.call_args
    assert 'webhooks' in args[0]
    assert kwargs['params']['idWebhook'] == id_webhook
    assert kwargs['params']['codigoTipoMovimento'] == codigo_tipo_movimento
    assert kwargs['headers']['client_id'] == client_id


def test_consultar_webhook_erro_negocio(boleto_client: BoletoAPI) -> None:
    """Testa erro de negócio (400) na consulta de webhook"""
    # Configura o mock para erro 400
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Webhook não encontrado', 'codigo': 'ERR001'}]
    }
    boleto_client.session.get.return_value = mock_response

    # Dados de teste
    id_webhook = 999  # Não existe
    codigo_tipo_movimento = 7
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.consultar_webhook(
            id_webhook=id_webhook,
            codigo_tipo_movimento=codigo_tipo_movimento,
            client_id=client_id,
        )

    # Verificações
    assert '[400] Falha na consulta do webhook: Webhook não encontrado' in str(
        exc_info.value
    )
    assert exc_info.value.code == 400
    assert exc_info.value.id_webhook == id_webhook


def test_consultar_webhook_erro_dados_inconsistentes(boleto_client: BoletoAPI) -> None:
    """Testa erro de dados inconsistentes (406) na consulta de webhook"""
    # Configura o mock para erro 406
    mock_response = Mock()
    mock_response.status_code = 406
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Tipo de movimento inválido', 'codigo': 'ERR002'}]
    }
    boleto_client.session.get.return_value = mock_response

    # Dados de teste
    id_webhook = 123
    codigo_tipo_movimento = 99  # Inválido
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.consultar_webhook(
            id_webhook=id_webhook,
            codigo_tipo_movimento=codigo_tipo_movimento,
            client_id=client_id,
        )

    # Verificações
    assert '[406] Falha na consulta do webhook: Tipo de movimento inválido' in str(
        exc_info.value
    )
    assert exc_info.value.code == 406
    assert exc_info.value.id_webhook == id_webhook


def test_consultar_webhook_erro_interno(boleto_client: BoletoAPI) -> None:
    """Testa erro interno (500) na consulta de webhook"""
    # Configura o mock para erro 500
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Erro interno no servidor', 'codigo': 'ERR500'}]
    }
    boleto_client.session.get.return_value = mock_response

    # Dados de teste
    id_webhook = 123
    codigo_tipo_movimento = 7
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.consultar_webhook(
            id_webhook=id_webhook,
            codigo_tipo_movimento=codigo_tipo_movimento,
            client_id=client_id,
        )

    # Verificações
    assert '[500] Falha na consulta do webhook: Erro interno no servidor' in str(
        exc_info.value
    )
    assert exc_info.value.code == 500
    assert exc_info.value.id_webhook == id_webhook


def test_consultar_webhook_erro_comunicacao(boleto_client: BoletoAPI) -> None:
    """Testa erro de comunicação na consulta de webhook"""
    # Configura o mock para erro de comunicação
    boleto_client.session.get.side_effect = requests.exceptions.RequestException(
        'Erro de conexão'
    )

    # Dados de teste
    id_webhook = 123
    codigo_tipo_movimento = 7
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.consultar_webhook(
            id_webhook=id_webhook,
            codigo_tipo_movimento=codigo_tipo_movimento,
            client_id=client_id,
        )

    # Verificações
    assert 'Falha na comunicação com API de boletos: Erro de conexão' in str(
        exc_info.value
    )
    assert exc_info.value.id_webhook == id_webhook


def test_excluir_webhook_sucesso(boleto_client: BoletoAPI) -> None:
    """Testa a exclusão de webhook com sucesso (status 204)"""
    # Configura o mock
    mock_response = Mock()
    mock_response.status_code = 204
    boleto_client.session.delete.return_value = mock_response

    # Dados de teste
    id_webhook = 123
    client_id = 'client-id-123'

    # Chama o método
    result = boleto_client.excluir_webhook(id_webhook=id_webhook, client_id=client_id)

    # Verificações
    assert result is None  # Método deve retornar None em caso de sucesso
    boleto_client.session.delete.assert_called_once()
    args, kwargs = boleto_client.session.delete.call_args
    assert f'webhooks/{id_webhook}' in args[0]
    assert kwargs['headers']['client_id'] == client_id


def test_excluir_webhook_erro_negocio(boleto_client: BoletoAPI) -> None:
    """Testa erro de negócio (400) na exclusão de webhook"""
    # Configura o mock para erro 400
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Webhook já excluído', 'codigo': 'ERR001'}]
    }
    boleto_client.session.delete.return_value = mock_response

    # Dados de teste
    id_webhook = 123
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.excluir_webhook(id_webhook=id_webhook, client_id=client_id)

    # Verificações
    assert '[400] Falha na exclusão do webhook: Webhook já excluído' in str(
        exc_info.value
    )
    assert exc_info.value.code == 400
    assert exc_info.value.id_webhook == id_webhook


def test_excluir_webhook_erro_dados_inconsistentes(boleto_client: BoletoAPI) -> None:
    """Testa erro de dados inconsistentes (406) na exclusão de webhook"""
    # Configura o mock para erro 406
    mock_response = Mock()
    mock_response.status_code = 406
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Webhook não encontrado', 'codigo': 'ERR002'}]
    }
    boleto_client.session.delete.return_value = mock_response

    # Dados de teste
    id_webhook = 999  # Não existe
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.excluir_webhook(id_webhook=id_webhook, client_id=client_id)

    # Verificações
    assert '[406] Falha na exclusão do webhook: Webhook não encontrado' in str(
        exc_info.value
    )
    assert exc_info.value.code == 406
    assert exc_info.value.id_webhook == id_webhook


def test_excluir_webhook_erro_interno(boleto_client: BoletoAPI) -> None:
    """Testa erro interno (500) na exclusão de webhook"""
    # Configura o mock para erro 500
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Erro interno no servidor', 'codigo': 'ERR500'}]
    }
    boleto_client.session.delete.return_value = mock_response

    # Dados de teste
    id_webhook = 123
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.excluir_webhook(id_webhook=id_webhook, client_id=client_id)

    # Verificações
    assert '[500] Falha na exclusão do webhook: Erro interno no servidor' in str(
        exc_info.value
    )
    assert exc_info.value.code == 500
    assert exc_info.value.id_webhook == id_webhook


def test_excluir_webhook_erro_comunicacao(boleto_client: BoletoAPI) -> None:
    """Testa erro de comunicação na exclusão de webhook"""
    # Configura o mock para erro de comunicação
    boleto_client.session.delete.side_effect = requests.exceptions.RequestException(
        'Erro de conexão'
    )

    # Dados de teste
    id_webhook = 123
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.excluir_webhook(id_webhook=id_webhook, client_id=client_id)

    # Verificações
    assert 'Falha na comunicação com API de boletos: Erro de conexão' in str(
        exc_info.value
    )
    assert exc_info.value.id_webhook == id_webhook


def test_consultar_solicitacoes_webhook_sucesso(boleto_client: BoletoAPI) -> None:
    """Testa a consulta de solicitações de webhook com sucesso"""
    # Configura o mock
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'resultado': [
            {
                'paginalAtual': 1,
                'totalPaginas': 2,
                'totalRegistros': 100,
                'webhookSolicitacoes': [
                    {
                        'codigoWebhookSituacao': 3,
                        'descricaoWebhookSituacao': 'Validado com sucesso',
                        'codigoSolicitacaoSituacao': 3,
                        'descricaoSolicitacaoSituacao': 'Enviado com sucesso',
                        'codigoTipoMovimento': 7,
                        'descricaoTipoMovimento': 'Pagamento (Baixa operacional)',
                        'codigoPeriodoMovimento': 1,
                        'descricaoPeriodoMovimento': 'Movimento atual (D0)',
                        'descricaoErroProcessamento': None,
                        'dataHoraCadastro': '2025-06-01T10:00:00.000Z',
                        'validacaoWebhook': True,
                        'webhookNotificacoes': [
                            {
                                'url': 'https://webhook.example.com',
                                'dataHoraInicio': '2025-06-01T10:05:00.000Z',
                                'dataHoraFim': '2025-06-01T10:05:01.000Z',
                                'tempoComunicao': 1,
                                'codigoStatusRequisicao': 200,
                                'descricaoMensagemRetorno': '{"message":"Webhook recebido com sucesso!"}',
                            }
                        ],
                    }
                ],
            }
        ]
    }
    boleto_client.session.get.return_value = mock_response

    # Dados de teste
    id_webhook = 123
    data_solicitacao = '2025-06-01'
    client_id = 'client-id-123'
    pagina = 1
    codigo_solicitacao_situacao = 3

    # Chama o método
    result = boleto_client.consultar_solicitacoes_webhook(
        id_webhook=id_webhook,
        data_solicitacao=data_solicitacao,
        client_id=client_id,
        pagina=pagina,
        codigo_solicitacao_situacao=codigo_solicitacao_situacao,
    )

    # Verificações
    assert 'resultado' in result
    assert len(result['resultado']) == 1
    assert (
        result['resultado'][0]['webhookSolicitacoes'][0]['codigoSolicitacaoSituacao']
        == 3
    )
    boleto_client.session.get.assert_called_once()
    args, kwargs = boleto_client.session.get.call_args
    assert f'webhooks/{id_webhook}/solicitacoes' in args[0]
    assert kwargs['params']['dataSolicitacao'] == data_solicitacao
    assert kwargs['params']['pagina'] == pagina
    assert kwargs['params']['codigoSolicitacaoSituacao'] == codigo_solicitacao_situacao
    assert kwargs['headers']['client_id'] == client_id


def test_consultar_solicitacoes_webhook_erro_negocio(boleto_client: BoletoAPI) -> None:
    """Testa erro de negócio (400) na consulta de solicitações de webhook"""
    # Configura o mock para erro 400
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Data de solicitação inválida', 'codigo': 'ERR001'}]
    }
    boleto_client.session.get.return_value = mock_response

    # Dados de teste
    id_webhook = 123
    data_solicitacao = 'data-invalida'
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.consultar_solicitacoes_webhook(
            id_webhook=id_webhook,
            data_solicitacao=data_solicitacao,
            client_id=client_id,
        )

    # Verificações
    assert (
        '[400] Falha na consulta das solicitações do webhook: Data de solicitação inválida'
        in str(exc_info.value)
    )
    assert exc_info.value.code == 400
    assert exc_info.value.id_webhook == id_webhook


def test_consultar_solicitacoes_webhook_erro_dados_inconsistentes(
    boleto_client: BoletoAPI,
) -> None:
    """Testa erro de dados inconsistentes (406) na consulta de solicitações de webhook"""
    # Configura o mock para erro 406
    mock_response = Mock()
    mock_response.status_code = 406
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Webhook não encontrado', 'codigo': 'ERR002'}]
    }
    boleto_client.session.get.return_value = mock_response

    # Dados de teste
    id_webhook = 999  # Não existe
    data_solicitacao = '2025-06-01'
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.consultar_solicitacoes_webhook(
            id_webhook=id_webhook,
            data_solicitacao=data_solicitacao,
            client_id=client_id,
        )

    # Verificações
    assert (
        '[406] Falha na consulta das solicitações do webhook: Webhook não encontrado'
        in str(exc_info.value)
    )
    assert exc_info.value.code == 406
    assert exc_info.value.id_webhook == id_webhook


def test_consultar_solicitacoes_webhook_erro_interno(boleto_client: BoletoAPI) -> None:
    """Testa erro interno (500) na consulta de solicitações de webhook"""
    # Configura o mock para erro 500
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.json.return_value = {
        'mensagens': [{'mensagem': 'Erro interno no servidor', 'codigo': 'ERR500'}]
    }
    boleto_client.session.get.return_value = mock_response

    # Dados de teste
    id_webhook = 123
    data_solicitacao = '2025-06-01'
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.consultar_solicitacoes_webhook(
            id_webhook=id_webhook,
            data_solicitacao=data_solicitacao,
            client_id=client_id,
        )

    # Verificações
    assert (
        '[500] Falha na consulta das solicitações do webhook: Erro interno no servidor'
        in str(exc_info.value)
    )
    assert exc_info.value.code == 500
    assert exc_info.value.id_webhook == id_webhook


def test_consultar_solicitacoes_webhook_erro_comunicacao(
    boleto_client: BoletoAPI,
) -> None:
    """Testa erro de comunicação na consulta de solicitações de webhook"""
    # Configura o mock para erro de comunicação
    boleto_client.session.get.side_effect = requests.exceptions.RequestException(
        'Erro de conexão'
    )

    # Dados de teste
    id_webhook = 123
    data_solicitacao = '2025-06-01'
    client_id = 'client-id-123'

    # Verifica se exceção é levantada
    with pytest.raises(BoletoWebhookError) as exc_info:
        boleto_client.consultar_solicitacoes_webhook(
            id_webhook=id_webhook,
            data_solicitacao=data_solicitacao,
            client_id=client_id,
        )

    # Verificações
    assert 'Falha na comunicação com API de boletos: Erro de conexão' in str(
        exc_info.value
    )
    assert exc_info.value.id_webhook == id_webhook


# ============================================================================
# Testes para emitir_com_recovery() - Recovery em erro 400 de duplicação
# ============================================================================


@pytest.fixture
def dados_boleto_completo() -> dict:
    """Fixture com dados completos de boleto para testes de recovery.

    Nota: nossoNumero não incluído pois é gerado pelo Sicoob.
    O cenário de recovery em 400 ocorre quando o ERP gera um novo
    nossoNumero após timeout, então usamos seuNumero para identificação.
    """
    return {
        'numeroCliente': 123456,
        'codigoModalidade': 1,
        'numeroContaCorrente': 12345,
        'codigoEspecieDocumento': 'DM',
        'dataEmissao': '2024-01-01',
        'dataVencimento': '2024-12-31',
        'valor': 100.50,
        'seuNumero': 'SEU-123456',
        'identificacaoEmissaoBoleto': 1,
        'identificacaoDistribuicaoBoleto': 1,
        'tipoDesconto': 0,
        'tipoMulta': 0,
        'tipoJurosMora': 3,
        'numeroParcela': 1,
        'pagador': {
            'numeroCpfCnpj': '11144477735',
            'nome': 'João Silva',
            'endereco': 'Rua Teste, 123',
            'bairro': 'Centro',
            'cidade': 'São Paulo',
            'cep': '01001000',
            'uf': 'SP',
        },
    }


def test_emitir_com_recovery_sucesso_normal(
    boleto_client: BoletoAPI, dados_boleto_completo: dict
) -> None:
    """Testa emissão normal sem necessidade de recovery"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'resultado': {'nossoNumero': 789012, 'codigoBarras': '123456789'}
    }
    boleto_client.session.post.return_value = mock_response

    result = boleto_client.emitir_com_recovery(dados_boleto_completo)

    assert 'resultado' in result
    assert '_recovery' not in result


def test_emitir_com_recovery_400_duplicacao_encontra_por_pagador(
    boleto_client: BoletoAPI, dados_boleto_completo: dict
) -> None:
    """Testa recovery em 400 de duplicação - encontra boleto por pagador + seuNumero.

    Este é o cenário principal: após timeout, ERP gera novo nossoNumero e tenta
    reemitir. O Sicoob retorna 400 "Já existe título". O recovery consulta
    boletos do pagador e filtra pelo seuNumero para encontrar o boleto original.
    """
    # Mock para emissão retornar 400 com mensagem de duplicação
    mock_post_response = Mock()
    mock_post_response.status_code = 400
    mock_post_response.json.return_value = {
        'mensagens': [{'mensagem': 'Já existe título cadastrado', 'codigo': 'ERR001'}]
    }
    boleto_client.session.post.return_value = mock_post_response

    # Mock para consulta por pagador retornar lista com o boleto
    mock_get_pagador = Mock()
    mock_get_pagador.status_code = 200
    mock_get_pagador.json.return_value = {
        'resultado': {
            'boletos': [
                {
                    'nossoNumero': 999999,
                    'seuNumero': 'OUTRO-123',
                    'codigoBarras': '111111111',
                },
                {
                    'nossoNumero': 888888,
                    'seuNumero': 'SEU-123456',
                    'codigoBarras': '222222222',
                },
            ]
        }
    }
    boleto_client.session.get.return_value = mock_get_pagador

    result = boleto_client.emitir_com_recovery(
        dados_boleto_completo, client_id='test-client-id'
    )

    assert result['_recovery'] is True
    assert result['resultado']['nossoNumero'] == 888888
    assert result['resultado']['seuNumero'] == 'SEU-123456'


def test_emitir_com_recovery_400_duplicacao_com_nosso_numero(
    boleto_client: BoletoAPI, dados_boleto_completo: dict
) -> None:
    """Testa recovery em 400 com nossoNumero - tenta primeiro por nossoNumero."""
    # Adiciona nossoNumero ao dados_boleto para este teste
    dados_com_nosso_numero = {**dados_boleto_completo, 'nossoNumero': 789012}

    # Mock para emissão retornar 400 com mensagem de duplicação
    mock_post_response = Mock()
    mock_post_response.status_code = 400
    mock_post_response.json.return_value = {
        'mensagens': [{'mensagem': 'Título duplicado no sistema', 'codigo': 'ERR002'}]
    }
    boleto_client.session.post.return_value = mock_post_response

    # Mock para consulta por nossoNumero retornar o boleto
    # consultar_boleto retorna {'resultado': {...}}, então o recovery
    # retorna {'resultado': {'resultado': {...}}, '_recovery': True}
    mock_get_response = Mock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {
        'resultado': {
            'nossoNumero': 789012,
            'seuNumero': 'SEU-123456',
            'codigoBarras': '123456789',
        }
    }
    boleto_client.session.get.return_value = mock_get_response

    result = boleto_client.emitir_com_recovery(dados_com_nosso_numero)

    assert result['_recovery'] is True
    # consultar_boleto retorna dict com 'resultado', então o recovery
    # aninha: {'resultado': <retorno de consultar_boleto>}
    assert result['resultado']['resultado']['nossoNumero'] == 789012


def test_emitir_com_recovery_400_duplicacao_nao_encontra(
    boleto_client: BoletoAPI, dados_boleto_completo: dict
) -> None:
    """Testa recovery em 400 de duplicação - não encontra boleto"""
    # Mock para emissão retornar 400 com mensagem de duplicação
    mock_post_response = Mock()
    mock_post_response.status_code = 400
    mock_post_response.json.return_value = {
        'mensagens': [{'mensagem': 'Já existe título', 'codigo': 'ERR001'}]
    }
    boleto_client.session.post.return_value = mock_post_response

    # Mock para consulta por pagador retornar lista vazia
    mock_get_pagador = Mock()
    mock_get_pagador.status_code = 200
    mock_get_pagador.json.return_value = {'resultado': {'boletos': []}}
    boleto_client.session.get.return_value = mock_get_pagador

    with pytest.raises(BoletoEmissaoError) as exc_info:
        boleto_client.emitir_com_recovery(
            dados_boleto_completo, client_id='test-client-id'
        )

    assert exc_info.value.code == 400


def test_emitir_com_recovery_400_sem_duplicacao_nao_faz_recovery(
    boleto_client: BoletoAPI, dados_boleto_completo: dict
) -> None:
    """Testa que erro 400 sem mensagem de duplicação não tenta recovery"""
    # Mock para emissão retornar 400 com mensagem genérica
    mock_post_response = Mock()
    mock_post_response.status_code = 400
    mock_post_response.json.return_value = {
        'mensagens': [{'mensagem': 'Campo inválido', 'codigo': 'ERR003'}]
    }
    boleto_client.session.post.return_value = mock_post_response

    with pytest.raises(BoletoEmissaoError) as exc_info:
        boleto_client.emitir_com_recovery(dados_boleto_completo)

    assert exc_info.value.code == 400
    # Verifica que não tentou consultar (GET não foi chamado)
    boleto_client.session.get.assert_not_called()


def test_emitir_com_recovery_400_desabilitado(
    boleto_client: BoletoAPI, dados_boleto_completo: dict
) -> None:
    """Testa que tentar_recovery_em_400=False desabilita o recovery"""
    # Mock para emissão retornar 400 com mensagem de duplicação
    mock_post_response = Mock()
    mock_post_response.status_code = 400
    mock_post_response.json.return_value = {
        'mensagens': [{'mensagem': 'Já existe título', 'codigo': 'ERR001'}]
    }
    boleto_client.session.post.return_value = mock_post_response

    with pytest.raises(BoletoEmissaoError) as exc_info:
        boleto_client.emitir_com_recovery(
            dados_boleto_completo, tentar_recovery_em_400=False
        )

    assert exc_info.value.code == 400
    # Verifica que não tentou consultar
    boleto_client.session.get.assert_not_called()


def test_is_erro_duplicacao_mensagem_principal(boleto_client: BoletoAPI) -> None:
    """Testa detecção de duplicação na mensagem principal"""
    erro = BoletoEmissaoError(
        message='Já existe título cadastrado', code=400, dados_boleto={}
    )
    assert boleto_client._is_erro_duplicacao(erro) is True


def test_is_erro_duplicacao_lista_mensagens(boleto_client: BoletoAPI) -> None:
    """Testa detecção de duplicação na lista de mensagens"""
    erro = BoletoEmissaoError(
        message='Erro na emissão',
        code=400,
        dados_boleto={},
        mensagens=[{'mensagem': 'Título duplicado', 'codigo': 'ERR001'}],
    )
    assert boleto_client._is_erro_duplicacao(erro) is True


def test_is_erro_duplicacao_sem_duplicacao(boleto_client: BoletoAPI) -> None:
    """Testa que erros genéricos não são detectados como duplicação"""
    erro = BoletoEmissaoError(
        message='Campo obrigatório não informado',
        code=400,
        dados_boleto={},
        mensagens=[{'mensagem': 'Valor inválido', 'codigo': 'ERR002'}],
    )
    assert boleto_client._is_erro_duplicacao(erro) is False


def test_tentar_recovery_por_pagador_sem_client_id(
    boleto_client: BoletoAPI, dados_boleto_completo: dict
) -> None:
    """Testa que recovery por pagador sem client_id retorna None"""
    result = boleto_client._tentar_recovery_por_pagador(
        dados_boleto_completo, client_id=None
    )
    assert result is None


def test_tentar_recovery_por_pagador_sem_dados_suficientes(
    boleto_client: BoletoAPI,
) -> None:
    """Testa que recovery por pagador sem dados suficientes retorna None"""
    dados_incompletos = {
        'numeroCliente': 123456,
        # Faltando pagador e seuNumero
    }
    result = boleto_client._tentar_recovery_por_pagador(
        dados_incompletos, client_id='test-client'
    )
    assert result is None
