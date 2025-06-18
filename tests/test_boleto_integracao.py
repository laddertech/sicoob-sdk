import os
import pytest
from dotenv import load_dotenv

from sicoob.client import Sicoob

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()


@pytest.fixture
def sicoob_client():
    """Fixture que retorna um cliente Sicoob configurado para sandbox"""
    client_id = os.getenv('SICOOB_CLIENT_ID')
    if not client_id:
        pytest.skip('SICOOB_CLIENT_ID não configurado no ambiente')

    return Sicoob(
        client_id=client_id,
        sandbox_mode=True,  # Modo sandbox não requer certificado
    )


def test_emitir_boleto_integracao_real(sicoob_client):
    """Teste de integração real com API de boletos do Sicoob (sandbox)"""
    # Dados do boleto (mesmos do teste anterior)
    dados_boleto = {
        'numeroCliente': 25546454,
        'codigoModalidade': 1,
        'numeroContaCorrente': 0,
        'codigoEspecieDocumento': 'DM',
        'dataEmissao': '2018-09-20',
        'nossoNumero': 2588658,
        'seuNumero': '1235512',
        'identificacaoBoletoEmpresa': '4562',
        'identificacaoEmissaoBoleto': 1,
        'identificacaoDistribuicaoBoleto': 1,
        'valor': 156.23,
        'dataVencimento': '2018-09-20',
        'dataLimitePagamento': '2018-09-20',
        'valorAbatimento': 1,
        'tipoDesconto': 1,
        'dataPrimeiroDesconto': '2018-09-20',
        'valorPrimeiroDesconto': 1,
        'dataSegundoDesconto': '2018-09-20',
        'valorSegundoDesconto': 0,
        'dataTerceiroDesconto': '2018-09-20',
        'valorTerceiroDesconto': 0,
        'tipoMulta': 1,
        'dataMulta': '2018-09-20',
        'valorMulta': 5,
        'tipoJurosMora': 1,
        'dataJurosMora': '2018-09-20',
        'valorJurosMora': 4,
        'numeroParcela': 1,
        'aceite': True,
        'codigoNegativacao': 2,
        'numeroDiasNegativacao': 60,
        'codigoProtesto': 1,
        'numeroDiasProtesto': 30,
        'pagador': {
            'numeroCpfCnpj': '98765432185',
            'nome': 'Marcelo dos Santos',
            'endereco': 'Rua 87 Quadra 1 Lote 1 casa 1',
            'bairro': 'Santa Rosa',
            'cidade': 'Luziânia',
            'cep': '72320000',
            'uf': 'DF',
            'email': 'pagador@dominio.com.br',
        },
        'beneficiarioFinal': {'numeroCpfCnpj': '98784978699', 'nome': 'Lucas de Lima'},
        'mensagensInstrucao': [
            'Descrição da Instrução 1',
            'Descrição da Instrução 2',
            'Descrição da Instrução 3',
            'Descrição da Instrução 4',
            'Descrição da Instrução 5',
        ],
        'gerarPdf': True,
        'rateioCreditos': [
            {
                'numeroBanco': 756,
                'numeroAgencia': 4027,
                'numeroContaCorrente': 0,
                'contaPrincipal': True,
                'codigoTipoValorRateio': 1,
                'valorRateio': 100,
                'codigoTipoCalculoRateio': 1,
                'numeroCpfCnpjTitular': '98765432185',
                'nomeTitular': 'Marcelo dos Santos',
                'codigoFinalidadeTed': 10,
                'codigoTipoContaDestinoTed': 'CC',
                'quantidadeDiasFloat': 1,
                'dataFloatCredito': '2020-12-30',
            }
        ],
        'codigoCadastrarPIX': 1,
        'numeroContratoCobranca': 1,
    }

    # Chama a API real (sem mocks)
    try:
        resultado = sicoob_client.cobranca.boleto.emitir_boleto(dados_boleto)

        # Verificações básicas da resposta
        assert 'resultado' in resultado
        assert 'nossoNumero' in resultado['resultado']
        assert 'codigoBarras' in resultado['resultado']
        assert 'linhaDigitavel' in resultado['resultado']

    except Exception as e:
        print(
            f'\nResposta completa da API: {e.response.text if hasattr(e, "response") else str(e)}'
        )
