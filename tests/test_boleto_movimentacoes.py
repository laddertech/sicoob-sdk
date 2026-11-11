"""Testes das movimentações da carteira de cobrança (POST/GET /movimentacoes)."""

import base64
import io
import json
import zipfile
from datetime import date
from unittest.mock import Mock, patch

import pytest
import requests

from sicoob.boleto import (
    ESCOPO_MOVIMENTACAO,
    MOVIMENTO_LIQUIDACAO,
    SITUACAO_MOVIMENTACAO_PROCESSANDO,
    SITUACAO_MOVIMENTACAO_PRONTA,
    SITUACAO_MOVIMENTACAO_SEM_REGISTROS,
    BoletoAPI,
)
from sicoob.exceptions import BoletoMovimentacaoError
from sicoob.validation import ValidationError

NUMERO_CLIENTE = 3122794

# Registro real de liquidação (código de barras mascarado)
REGISTRO_LIQUIDACAO = {
    'siglaMovimento': 'LIQUI',
    'dataInicioMovimento': '2026-11-10T00:00:00-03:00',
    'dataFimMovimento': '2026-11-11T00:00:00-03:00',
    'numeroCliente': NUMERO_CLIENTE,
    'numeroContrato': NUMERO_CLIENTE,
    'modalidade': 1,
    'numeroTitulo': 2107731,
    'seuNumero': '32661',
    'dataVencimentoTitulo': '2026-11-05T00:00:00-03:00',
    'valorTitulo': 180.0,
    'codigoBarras': '0' * 44,
    'numeroContaCorrente': 3002756,
    'valorTarifaMovimento': 1.94,
    'valorAbatimento': 0.0,
    'dataMovimentoLiquidacao': '2026-11-10T00:00:00-03:00',
    'dataLiquidacao': '2026-11-10T00:00:00-03:00',
    'dataPrevisaoCredito': '2026-11-11T00:00:00-03:00',
    'numeroBancoRecebedor': 21,
    'numeroAgenciaRecebedora': 133,
    'idTipoOpFinanceira': 58,
    'tipoOpFinanceira': '04 - Via Compensação',
    'valorDesconto': 0.0,
    'valorMora': 22.96,
    'valorLiquido': 202.96,
    'numeroContratoCobranca': 23125,
    'tipoCarteiraOpCredito': 'COBRANÇA',
}


def _zip_b64(arquivos: dict[str, object]) -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        for nome, conteudo in arquivos.items():
            zf.writestr(nome, json.dumps(conteudo, ensure_ascii=False))
    return base64.b64encode(buffer.getvalue()).decode()


def _resposta(status: int, corpo: object | None = None) -> Mock:
    resp = Mock()
    resp.status_code = status
    if corpo is None:
        resp.json.side_effect = ValueError('sem corpo')
    else:
        resp.json.return_value = corpo
    return resp


def _erro_5002(mensagem: str) -> Mock:
    return _resposta(400, {'mensagens': [{'mensagem': mensagem, 'codigo': '5002'}]})


PROCESSANDO = 'Solicitação ainda em processamento.'
SEM_REGISTROS = 'Solicitação não retornou nenhum registro.'


@pytest.fixture
def api(mock_oauth_client: Mock) -> BoletoAPI:
    return BoletoAPI(mock_oauth_client, Mock())


# --- solicitar_movimentacao -------------------------------------------------


@patch('sicoob.api_client.SicoobConfig.is_sandbox', return_value=False)
def test_solicitar_envia_payload_e_escopo(_sandbox: Mock, api: BoletoAPI) -> None:
    api.session.post.return_value = _resposta(
        200, {'resultado': {'mensagem': 'ok', 'codigoSolicitacao': 223330453}}
    )

    codigo = api.solicitar_movimentacao(
        NUMERO_CLIENTE, MOVIMENTO_LIQUIDACAO, date(2026, 11, 9), '2026-11-10'
    )

    assert codigo == 223330453
    _, kwargs = api.session.post.call_args
    assert api.session.post.call_args[0][0].endswith(
        '/cobranca-bancaria/v3/boletos/movimentacoes'
    )
    assert kwargs['json'] == {
        'numeroCliente': NUMERO_CLIENTE,
        'tipoMovimento': MOVIMENTO_LIQUIDACAO,
        'dataInicial': '2026-11-09',
        'dataFinal': '2026-11-10',
    }
    api.oauth_client.get_access_token.assert_called_with(ESCOPO_MOVIMENTACAO)


def test_solicitar_codigo_como_string(api: BoletoAPI) -> None:
    api.session.post.return_value = _resposta(
        200, {'resultado': {'codigoSolicitacao': '132'}}
    )
    assert (
        api.solicitar_movimentacao(NUMERO_CLIENTE, 5, '2026-11-09', '2026-11-09') == 132
    )


@pytest.mark.parametrize(
    ('tipo', 'inicio', 'fim'),
    [
        (0, '2026-11-09', '2026-11-10'),
        (8, '2026-11-09', '2026-11-10'),
        (5, '2026-11-10', '2026-11-09'),  # fim antes do início
        (5, '2026-11-09', '2026-11-11'),  # 3 dias: acima do limite
        (5, '09/11/2026', '2026-11-10'),  # formato inválido
    ],
)
def test_solicitar_valida_parametros(
    api: BoletoAPI, tipo: int, inicio: str, fim: str
) -> None:
    with pytest.raises(ValidationError):
        api.solicitar_movimentacao(NUMERO_CLIENTE, tipo, inicio, fim)
    api.session.post.assert_not_called()


def test_solicitar_erro_401_vira_excecao(api: BoletoAPI) -> None:
    api.session.post.return_value = _resposta(
        401, {'httpCode': '401', 'moreInformation': 'Cannot pass the security'}
    )
    with pytest.raises(BoletoMovimentacaoError) as exc:
        api.solicitar_movimentacao(NUMERO_CLIENTE, 5, '2026-11-09', '2026-11-10')
    assert exc.value.code == 401


def test_solicitar_erro_400_preserva_mensagens(api: BoletoAPI) -> None:
    api.session.post.return_value = _resposta(
        400, {'mensagens': [{'mensagem': 'Período inválido', 'codigo': '1'}]}
    )
    with pytest.raises(BoletoMovimentacaoError) as exc:
        api.solicitar_movimentacao(NUMERO_CLIENTE, 5, '2026-11-09', '2026-11-10')
    assert 'Período inválido' in str(exc.value)
    assert exc.value.mensagens == [{'mensagem': 'Período inválido', 'codigo': '1'}]


def test_solicitar_sem_codigo(api: BoletoAPI) -> None:
    api.session.post.return_value = _resposta(200, {'resultado': {}})
    with pytest.raises(BoletoMovimentacaoError, match='codigoSolicitacao'):
        api.solicitar_movimentacao(NUMERO_CLIENTE, 5, '2026-11-09', '2026-11-10')


def test_solicitar_falha_de_rede(api: BoletoAPI) -> None:
    api.session.post.side_effect = requests.exceptions.ConnectionError('caiu')
    with pytest.raises(BoletoMovimentacaoError, match='comunicação'):
        api.solicitar_movimentacao(NUMERO_CLIENTE, 5, '2026-11-09', '2026-11-10')


# --- consultar_situacao_movimentacao ----------------------------------------


def test_situacao_pronta(api: BoletoAPI) -> None:
    api.session.get.return_value = _resposta(
        200,
        {
            'resultado': {
                'quantidadeTotalRegistros': 9,
                'quantidadeArquivo': 1,
                'idArquivos': [99809720],
            }
        },
    )
    situacao = api.consultar_situacao_movimentacao(NUMERO_CLIENTE, 223330453)
    assert situacao == {
        'situacao': SITUACAO_MOVIMENTACAO_PRONTA,
        'id_arquivos': [99809720],
        'quantidade_total_registros': 9,
    }
    _, kwargs = api.session.get.call_args
    assert kwargs['params'] == {
        'numeroCliente': NUMERO_CLIENTE,
        'codigoSolicitacao': 223330453,
    }


def test_situacao_processando(api: BoletoAPI) -> None:
    api.session.get.return_value = _erro_5002(PROCESSANDO)
    situacao = api.consultar_situacao_movimentacao(NUMERO_CLIENTE, 1)
    assert situacao['situacao'] == SITUACAO_MOVIMENTACAO_PROCESSANDO


@pytest.mark.parametrize(
    'resposta',
    [
        _erro_5002(SEM_REGISTROS),
        _resposta(200, {'resultado': {'quantidadeTotalRegistros': 0}}),
    ],
)
def test_situacao_sem_registros(api: BoletoAPI, resposta: Mock) -> None:
    api.session.get.return_value = resposta
    situacao = api.consultar_situacao_movimentacao(NUMERO_CLIENTE, 1)
    assert situacao['situacao'] == SITUACAO_MOVIMENTACAO_SEM_REGISTROS
    assert situacao['id_arquivos'] == []


def test_situacao_400_desconhecido_levanta(api: BoletoAPI) -> None:
    api.session.get.return_value = _erro_5002('Solicitação inexistente.')
    with pytest.raises(BoletoMovimentacaoError) as exc:
        api.consultar_situacao_movimentacao(NUMERO_CLIENTE, 7)
    assert exc.value.codigo_solicitacao == 7


def test_situacao_403_levanta(api: BoletoAPI) -> None:
    api.session.get.return_value = _resposta(
        403,
        {
            'mensagens': [
                {
                    'mensagem': 'Usuário não possui permissão de acesso ao recurso',
                    'codigo': '0003',
                }
            ]
        },
    )
    with pytest.raises(BoletoMovimentacaoError) as exc:
        api.consultar_situacao_movimentacao(NUMERO_CLIENTE, 7)
    assert exc.value.code == 403


# --- baixar_arquivo_movimentacao --------------------------------------------


def test_download_decodifica_zip(api: BoletoAPI) -> None:
    segundo = {**REGISTRO_LIQUIDACAO, 'numeroTitulo': 2107720}
    api.session.get.return_value = _resposta(
        200,
        {
            'resultado': {
                'arquivo': _zip_b64(
                    {
                        'LIQUI_0.json': [REGISTRO_LIQUIDACAO],
                        'LIQUI_1.json': [segundo],
                    }
                ),
                'nomeArquivo': 'LIQUI.zip',
            }
        },
    )

    registros = api.baixar_arquivo_movimentacao(NUMERO_CLIENTE, 1, 99809720)

    assert [r['numeroTitulo'] for r in registros] == [2107731, 2107720]
    assert registros[0]['valorLiquido'] == 202.96
    _, kwargs = api.session.get.call_args
    assert api.session.get.call_args[0][0].endswith('/boletos/movimentacoes/download')
    assert kwargs['params']['idArquivo'] == 99809720


def test_download_aceita_bom_utf8(api: BoletoAPI) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        zf.writestr(
            'a.json',
            '﻿' + json.dumps([REGISTRO_LIQUIDACAO], ensure_ascii=False),
        )
    api.session.get.return_value = _resposta(
        200, {'resultado': {'arquivo': base64.b64encode(buffer.getvalue()).decode()}}
    )
    assert len(api.baixar_arquivo_movimentacao(NUMERO_CLIENTE, 1, 2)) == 1


@pytest.mark.parametrize(
    'arquivo',
    [
        'não é base64!',
        base64.b64encode(b'nao e zip').decode(),
        _zip_b64({'a.json': 'texto solto'}),
        _zip_b64({'a.json': [1, 2]}),
    ],
)
def test_download_arquivo_ilegivel(api: BoletoAPI, arquivo: str) -> None:
    api.session.get.return_value = _resposta(200, {'resultado': {'arquivo': arquivo}})
    with pytest.raises(BoletoMovimentacaoError, match='ilegível') as exc:
        api.baixar_arquivo_movimentacao(NUMERO_CLIENTE, 1, 2)
    assert exc.value.id_arquivo == 2


def test_download_sem_arquivo(api: BoletoAPI) -> None:
    api.session.get.return_value = _resposta(200, {'resultado': {}})
    with pytest.raises(BoletoMovimentacaoError, match='sem arquivo'):
        api.baixar_arquivo_movimentacao(NUMERO_CLIENTE, 1, 2)


# --- obter_movimentacoes ----------------------------------------------------


def _fluxo_get(respostas_por_codigo: dict[int, list[Mock]], downloads: dict):
    """side_effect de session.get que despacha por URL e parâmetros."""

    def _get(url: str, params: dict, headers: dict, timeout: tuple) -> Mock:
        if url.endswith('/download'):
            return downloads[params['idArquivo']]
        return respostas_por_codigo[params['codigoSolicitacao']].pop(0)

    return _get


@patch('sicoob.boleto.time.sleep')
def test_obter_divide_em_janelas_sem_sobreposicao(sleep: Mock, api: BoletoAPI) -> None:
    api.session.post.side_effect = [
        _resposta(200, {'resultado': {'codigoSolicitacao': 1}}),
        _resposta(200, {'resultado': {'codigoSolicitacao': 2}}),
        _resposta(200, {'resultado': {'codigoSolicitacao': 3}}),
        _resposta(200, {'resultado': {'codigoSolicitacao': 4}}),
    ]
    pronta = {
        'resultado': {'quantidadeTotalRegistros': 1, 'idArquivos': [10]},
    }
    api.session.get.side_effect = _fluxo_get(
        {
            1: [_erro_5002(PROCESSANDO), _resposta(200, pronta)],
            2: [_erro_5002(SEM_REGISTROS)],
            3: [_resposta(200, {'resultado': {'quantidadeTotalRegistros': 0}})],
            4: [_resposta(200, pronta)],
        },
        {
            10: _resposta(
                200,
                {'resultado': {'arquivo': _zip_b64({'a.json': [REGISTRO_LIQUIDACAO]})}},
            )
        },
    )

    registros = api.obter_movimentacoes(
        NUMERO_CLIENTE, MOVIMENTO_LIQUIDACAO, '2026-11-05', '2026-11-11'
    )

    janelas = [
        (c.kwargs['json']['dataInicial'], c.kwargs['json']['dataFinal'])
        for c in api.session.post.call_args_list
    ]
    assert janelas == [
        ('2026-11-05', '2026-11-06'),
        ('2026-11-07', '2026-11-08'),
        ('2026-11-09', '2026-11-10'),
        ('2026-11-11', '2026-11-11'),
    ]
    assert len(registros) == 2
    sleep.assert_called_once_with(5.0)


@patch('sicoob.boleto.time.sleep')
@patch('sicoob.boleto.time.monotonic')
def test_obter_tempo_limite(monotonic: Mock, sleep: Mock, api: BoletoAPI) -> None:
    monotonic.side_effect = [0.0, 10.0, 400.0]
    api.session.post.return_value = _resposta(
        200, {'resultado': {'codigoSolicitacao': 55}}
    )
    api.session.get.return_value = _erro_5002(PROCESSANDO)

    with pytest.raises(BoletoMovimentacaoError, match='não ficou pronta') as exc:
        api.obter_movimentacoes(NUMERO_CLIENTE, 5, '2026-11-09', '2026-11-09')
    assert exc.value.codigo_solicitacao == 55


def test_obter_valida_periodo_invertido(api: BoletoAPI) -> None:
    with pytest.raises(ValidationError):
        api.obter_movimentacoes(NUMERO_CLIENTE, 5, '2026-11-10', '2026-11-09')
    api.session.post.assert_not_called()


# --- achados da revisão -----------------------------------------------------


def test_requisicoes_passam_timeout(api: BoletoAPI) -> None:
    api.session.post.return_value = _resposta(
        200, {'resultado': {'codigoSolicitacao': 1}}
    )
    api.session.get.return_value = _erro_5002(PROCESSANDO)
    api.solicitar_movimentacao(NUMERO_CLIENTE, 5, '2026-11-09', '2026-11-10')
    api.consultar_situacao_movimentacao(NUMERO_CLIENTE, 1)
    assert api.session.post.call_args.kwargs['timeout']
    assert api.session.get.call_args.kwargs['timeout']


def test_situacao_400_processamento_sem_codigo_5002_levanta(api: BoletoAPI) -> None:
    api.session.get.return_value = _resposta(
        400,
        {'mensagens': [{'mensagem': 'Erro no processamento.', 'codigo': '9999'}]},
    )
    with pytest.raises(BoletoMovimentacaoError):
        api.consultar_situacao_movimentacao(NUMERO_CLIENTE, 1)


def test_situacao_contagem_positiva_sem_arquivos_levanta(api: BoletoAPI) -> None:
    api.session.get.return_value = _resposta(
        200, {'resultado': {'quantidadeTotalRegistros': 3, 'idArquivos': []}}
    )
    with pytest.raises(BoletoMovimentacaoError, match='sem arquivos'):
        api.consultar_situacao_movimentacao(NUMERO_CLIENTE, 1)


def test_situacao_contagem_como_string(api: BoletoAPI) -> None:
    api.session.get.return_value = _resposta(
        200,
        {'resultado': {'quantidadeTotalRegistros': '1.500', 'idArquivos': [1, 2]}},
    )
    situacao = api.consultar_situacao_movimentacao(NUMERO_CLIENTE, 1)
    assert situacao['quantidade_total_registros'] == 1500


def test_obter_contagem_divergente_levanta(api: BoletoAPI) -> None:
    api.session.post.return_value = _resposta(
        200, {'resultado': {'codigoSolicitacao': 9}}
    )
    api.session.get.side_effect = _fluxo_get(
        {
            9: [
                _resposta(
                    200,
                    {'resultado': {'quantidadeTotalRegistros': 2, 'idArquivos': [10]}},
                )
            ]
        },
        {
            10: _resposta(
                200,
                {'resultado': {'arquivo': _zip_b64({'a.json': [REGISTRO_LIQUIDACAO]})}},
            )
        },
    )
    with pytest.raises(BoletoMovimentacaoError, match='informou 2') as exc:
        api.obter_movimentacoes(NUMERO_CLIENTE, 5, '2026-11-09', '2026-11-10')
    assert exc.value.codigo_solicitacao == 9


@pytest.mark.parametrize(
    'resposta',
    [
        _resposta(204),
        _resposta(200, {'resultado': {'idArquivos': [1]}}),
        _resposta(200, {'resultado': {'idArquivos': []}}),
        _resposta(200, {'resultado': {'quantidadeTotalRegistros': 'x'}}),
        _resposta(200, {'resultado': {'quantidadeTotalRegistros': -1}}),
        _resposta(
            200,
            {
                'resultado': {
                    'quantidadeTotalRegistros': 5,
                    'quantidadeArquivo': 2,
                    'idArquivos': [1],
                }
            },
        ),
    ],
)
def test_situacao_resposta_incompleta_levanta(api: BoletoAPI, resposta: Mock) -> None:
    api.session.get.return_value = resposta
    with pytest.raises(BoletoMovimentacaoError):
        api.consultar_situacao_movimentacao(NUMERO_CLIENTE, 1)


def test_download_zip_com_nomes_repetidos_le_cada_entrada(api: BoletoAPI) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        zf.writestr('a.json', json.dumps([REGISTRO_LIQUIDACAO]))
        with pytest.warns(UserWarning):
            zf.writestr(
                'a.json',
                json.dumps([{**REGISTRO_LIQUIDACAO, 'numeroTitulo': 999}]),
            )
    api.session.get.return_value = _resposta(
        200, {'resultado': {'arquivo': base64.b64encode(buffer.getvalue()).decode()}}
    )
    registros = api.baixar_arquivo_movimentacao(NUMERO_CLIENTE, 1, 2)
    assert [r['numeroTitulo'] for r in registros] == [2107731, 999]
