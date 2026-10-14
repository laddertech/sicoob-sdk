from unittest.mock import Mock, patch

import pytest

from sicoob.auth import OAuth2Client
from sicoob.exceptions import (
    CobrancaPixNaoEncontradaError,
    PixError,
    WebhookPixNaoEncontradoError,
)
from sicoob.pagination import PaginationConfig
from sicoob.pix import PixAPI, SicoobPixAPICustom
from sicoob.validation import ValidationError


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


def test_listar_cobrancas(pix_client: PixAPI) -> None:
    """Testa a listagem de cobranças PIX em um período"""
    with patch.object(pix_client._pix_api, 'consultar_cobs') as mock_listar:
        mock_listar.return_value = {'cobs': [{'txid': '123'}, {'txid': '456'}]}

        result = pix_client.listar_cobrancas(
            '2024-01-01T00:00:00Z', '2024-01-31T23:59:59Z', status='ATIVA'
        )

        assert result == {'cobs': [{'txid': '123'}, {'txid': '456'}]}
        mock_listar.assert_called_once_with(
            '2024-01-01T00:00:00Z', '2024-01-31T23:59:59Z', status='ATIVA'
        )


def test_criar_lote_cobranca(pix_client: PixAPI) -> None:
    """Testa a criação de lote de cobranças com vencimento"""
    with patch.object(pix_client._pix_api, 'criar_lote_cobv') as mock_criar:
        mock_criar.return_value = {'id': 1}
        dados = {'descricao': 'Lote 1', 'cobsv': []}

        result = pix_client.criar_lote_cobranca(1, dados)

        assert result == {'id': 1}
        mock_criar.assert_called_once_with(1, dados)


def test_consultar_lote_cobranca(pix_client: PixAPI) -> None:
    """Testa a consulta de lote de cobranças"""
    with patch.object(pix_client._pix_api, 'consultar_lote_cobv') as mock_consultar:
        mock_consultar.return_value = {'id': 1, 'cobsv': []}

        result = pix_client.consultar_lote_cobranca(1)

        assert result == {'id': 1, 'cobsv': []}
        mock_consultar.assert_called_once_with(1)


def test_cadastrar_webhook(pix_client: PixAPI) -> None:
    """Testa o cadastro de webhook PIX"""
    with patch.object(pix_client._pix_api, 'configurar_webhook') as mock_configurar:
        mock_configurar.return_value = {'webhookUrl': 'https://example.com/webhook'}

        result = pix_client.cadastrar_webhook(
            ' 12345678901 ', 'https://example.com/webhook'
        )

        assert result == {'webhookUrl': 'https://example.com/webhook'}
        # A chave deve chegar sem espaços em branco nas extremidades
        mock_configurar.assert_called_once_with(
            '12345678901', 'https://example.com/webhook'
        )


@pytest.mark.parametrize('chave', ['', '   ', None, 123])
def test_cadastrar_webhook_chave_invalida(pix_client: PixAPI, chave: object) -> None:
    """Testa que chave PIX inválida é rejeitada antes da chamada à API"""
    with pytest.raises(ValidationError) as exc_info:
        pix_client.cadastrar_webhook(chave, 'https://example.com/webhook')  # type: ignore[arg-type]

    assert 'chave' in str(exc_info.value).lower()


def test_cadastrar_webhook_url_invalida(pix_client: PixAPI) -> None:
    """Testa que URL de webhook inválida é rejeitada"""
    with pytest.raises(ValidationError):
        pix_client.cadastrar_webhook('12345678901', 'nao-e-uma-url')


def test_criar_cobranca_imediata_txid_invalido(pix_client: PixAPI) -> None:
    """Testa que TXID fora do padrão é rejeitado antes da chamada à API"""
    dados = {
        'calendario': {'expiracao': 3600},
        'valor': {'original': '100.50'},
        'chave': '12345678901',
    }

    with pytest.raises(ValidationError) as exc_info:
        pix_client.criar_cobranca_imediata('curto', dados)

    assert 'txid' in str(exc_info.value).lower()


def test_proxy_converte_erro_generico_em_pix_error(pix_client: PixAPI) -> None:
    """Testa que o proxy encapsula erros genéricos da pypix-api em PixError"""
    with patch.object(pix_client._pix_api, 'consultar_cob') as mock_consultar:
        mock_consultar.side_effect = RuntimeError('falha inesperada')

        with pytest.raises(PixError) as exc_info:
            pix_client.consultar_cobranca_imediata('abcd1234567890123456789012345')

        assert 'falha inesperada' in str(exc_info.value)


def test_proxy_atributo_nao_callable(pix_client: PixAPI) -> None:
    """Testa que atributos (não métodos) são delegados sem encapsulamento"""
    assert pix_client.BASE_URL == pix_client._pix_api.BASE_URL


def test_proxy_atributo_inexistente(pix_client: PixAPI) -> None:
    """Testa que atributo inexistente na pypix-api levanta AttributeError"""
    with pytest.raises(AttributeError):
        getattr(pix_client, 'metodo_que_nao_existe')  # noqa: B009


def test_filtros_da_pagina_traduz_chaves_de_paginacao() -> None:
    """Testa a tradução das chaves genéricas de paginação para a API PIX"""
    params = {
        'inicio': '2024-01-01T00:00:00Z',
        'fim': '2024-01-31T23:59:59Z',
        'page': 3,
        'limit': 100,
        'size': 100,
        'status': 'ATIVA',
    }

    filtros = PixAPI._filtros_da_pagina(params, page_size=50)

    assert filtros == {'status': 'ATIVA', 'pagina_atual': 3, 'itens_por_pagina': 50}


def test_filtros_da_pagina_sem_page_usa_primeira() -> None:
    """Testa que a ausência de 'page' assume a primeira página"""
    filtros = PixAPI._filtros_da_pagina({'inicio': 'a', 'fim': 'b'}, page_size=25)

    assert filtros == {'pagina_atual': 1, 'itens_por_pagina': 25}


def test_listar_cobrancas_paginado(pix_client: PixAPI) -> None:
    """Testa a iteração de cobranças PIX com paginação automática"""
    paginas = [
        {'cobs': [{'txid': '1'}, {'txid': '2'}]},
        {'cobs': [{'txid': '3'}]},
    ]

    with patch.object(pix_client._pix_api, 'consultar_cobs') as mock_listar:
        mock_listar.side_effect = paginas

        config = PaginationConfig(page_size=2, max_pages=2)
        cobrancas = list(
            pix_client.listar_cobrancas_paginado(
                '2024-01-01T00:00:00Z', '2024-01-31T23:59:59Z', pagination=config
            )
        )

        assert [c['txid'] for c in cobrancas] == ['1', '2', '3']
        # A API deve receber os nomes de paginação que ela entende
        _, kwargs = mock_listar.call_args_list[0]
        assert kwargs['pagina_atual'] == 1
        assert kwargs['itens_por_pagina'] == 2


def test_listar_cobrancas_paginado_sem_config(pix_client: PixAPI) -> None:
    """Testa que a paginação usa configuração padrão quando omitida"""
    with patch.object(pix_client._pix_api, 'consultar_cobs') as mock_listar:
        mock_listar.return_value = {'cobs': [{'txid': '1'}]}

        cobrancas = list(
            pix_client.listar_cobrancas_paginado(
                '2024-01-01T00:00:00Z', '2024-01-31T23:59:59Z'
            )
        )

        assert cobrancas == [{'txid': '1'}]
        _, kwargs = mock_listar.call_args
        assert kwargs['itens_por_pagina'] == 100


def test_listar_cobrancas_por_paginas(pix_client: PixAPI) -> None:
    """Testa a iteração por páginas completas com metadados"""
    with patch.object(pix_client._pix_api, 'consultar_cobs') as mock_listar:
        mock_listar.side_effect = [
            {'cobs': [{'txid': '1'}, {'txid': '2'}]},
            {'cobs': [{'txid': '3'}]},
        ]

        config = PaginationConfig(page_size=2)
        paginas = list(
            pix_client.listar_cobrancas_por_paginas(
                '2024-01-01T00:00:00Z', '2024-01-31T23:59:59Z', pagination=config
            )
        )

        assert len(paginas) == 2
        assert [c['txid'] for c in paginas[0].items] == ['1', '2']
        assert paginas[0].page_info.current_page == 1
        assert [c['txid'] for c in paginas[1].items] == ['3']


def test_listar_cobrancas_por_paginas_respeita_max_pages(pix_client: PixAPI) -> None:
    """Testa que max_pages interrompe a iteração de páginas"""
    with patch.object(pix_client._pix_api, 'consultar_cobs') as mock_listar:
        mock_listar.return_value = {'cobs': [{'txid': '1'}, {'txid': '2'}]}

        config = PaginationConfig(page_size=2, max_pages=1)
        paginas = list(
            pix_client.listar_cobrancas_por_paginas(
                '2024-01-01T00:00:00Z', '2024-01-31T23:59:59Z', pagination=config
            )
        )

        assert len(paginas) == 1


def test_listar_cobrancas_por_paginas_interrompe_em_erro(pix_client: PixAPI) -> None:
    """Testa que um erro na busca encerra a iteração sem propagar a exceção"""
    with patch.object(pix_client._pix_api, 'consultar_cobs') as mock_listar:
        mock_listar.side_effect = [
            {'cobs': [{'txid': '1'}, {'txid': '2'}]},
            RuntimeError('API indisponível'),
        ]

        config = PaginationConfig(page_size=2)
        paginas = list(
            pix_client.listar_cobrancas_por_paginas(
                '2024-01-01T00:00:00Z', '2024-01-31T23:59:59Z', pagination=config
            )
        )

        assert len(paginas) == 1


@pytest.fixture
def pix_api_custom(mock_oauth_client: Mock) -> SicoobPixAPICustom:
    """Fixture que retorna a implementação customizada da pypix-api"""
    return SicoobPixAPICustom(oauth=mock_oauth_client, sandbox_mode=True)


def _resposta(status_code: int, payload: object) -> Mock:
    """Cria um mock de resposta HTTP"""
    resposta = Mock()
    resposta.status_code = status_code
    if isinstance(payload, Exception):
        resposta.json.side_effect = payload
    else:
        resposta.json.return_value = payload
    return resposta


def test_handle_error_ignora_resposta_de_sucesso(
    pix_api_custom: SicoobPixAPICustom,
) -> None:
    """Testa que respostas 2xx não são tratadas como erro"""
    assert pix_api_custom._handle_error_response(_resposta(200, {})) is None


def test_handle_error_404_cobranca(pix_api_custom: SicoobPixAPICustom) -> None:
    """Testa o mapeamento de 404 de cobrança para exceção de domínio"""
    resposta = _resposta(404, {'status': 404, 'detail': 'Cobrança não encontrada'})

    with pytest.raises(CobrancaPixNaoEncontradaError):
        pix_api_custom._handle_error_response(resposta)


def test_handle_error_404_webhook(pix_api_custom: SicoobPixAPICustom) -> None:
    """Testa o mapeamento de 404 de webhook para exceção de domínio"""
    resposta = _resposta(404, {'status': 404, 'title': 'Webhook não encontrado'})

    with pytest.raises(WebhookPixNaoEncontradoError):
        pix_api_custom._handle_error_response(resposta)


def test_handle_error_404_generico(pix_api_custom: SicoobPixAPICustom) -> None:
    """Testa que um 404 sem domínio identificado vira PixError"""
    resposta = _resposta(404, {'status': 404, 'detail': 'Recurso não encontrado'})

    with pytest.raises(PixError):
        pix_api_custom._handle_error_response(resposta)


def test_handle_error_corpo_nao_json(pix_api_custom: SicoobPixAPICustom) -> None:
    """Testa que corpo não-JSON não impede o tratamento do erro"""
    resposta = _resposta(500, ValueError('corpo inválido'))

    with pytest.raises(PixError) as exc_info:
        pix_api_custom._handle_error_response(resposta)

    assert '500' in str(exc_info.value)


def test_handle_error_usa_type_quando_sem_detalhe(
    pix_api_custom: SicoobPixAPICustom,
) -> None:
    """Testa a mensagem de fallback quando não há detail nem title"""
    resposta = _resposta(400, {'status': 400, 'type': 'ValidacaoErro'})

    with pytest.raises(PixError) as exc_info:
        pix_api_custom._handle_error_response(resposta)

    assert 'ValidacaoErro' in str(exc_info.value)


@pytest.mark.parametrize('payload', [None, [], ['erro']])
def test_handle_error_corpo_json_nao_objeto(
    pix_api_custom: SicoobPixAPICustom, payload: object
) -> None:
    """Testa que JSON válido que não é objeto preserva o status do erro"""
    resposta = _resposta(502, payload)

    with pytest.raises(PixError) as exc_info:
        pix_api_custom._handle_error_response(resposta)

    assert '502' in str(exc_info.value)


def test_handle_error_lista_preserva_corpo(
    pix_api_custom: SicoobPixAPICustom,
) -> None:
    """Testa que o corpo em lista aparece na mensagem de erro"""
    resposta = _resposta(400, [{'erro': 'campo valor ausente'}])

    with pytest.raises(PixError) as exc_info:
        pix_api_custom._handle_error_response(resposta)

    assert 'campo valor ausente' in str(exc_info.value)


def test_create_headers_usa_get_token_do_oauth_do_sdk() -> None:
    """Testa que a pypix-api obtém o token pelo OAuth2Client do SDK"""
    with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=False):
        oauth = OAuth2Client(client_id='test_id')

    with patch.object(
        OAuth2Client, 'get_access_token', return_value='token_real'
    ) as mock_token:
        api = SicoobPixAPICustom(oauth=oauth, sandbox_mode=False)
        headers = api._create_headers()

    assert headers['Authorization'] == 'Bearer token_real'
    mock_token.assert_called_once()
