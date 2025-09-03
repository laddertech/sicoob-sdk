"""
Exemplo de integração completa do Sicoob SDK

Este exemplo demonstra a arquitetura do SDK onde:
- PIX é delegado para pypix-api (biblioteca genérica)
- Boleto e Conta Corrente são específicos do Sicoob
"""

import os
from datetime import datetime, timedelta
from decimal import Decimal

from sicoob import Sicoob


def exemplo_completo():
    """Demonstra uso completo do SDK com todas as funcionalidades"""

    # 1. Inicialização do cliente
    print('=' * 50)
    print('INICIALIZANDO SICOOB SDK')
    print('=' * 50)

    sicoob = Sicoob(
        client_id=os.getenv('SICOOB_CLIENT_ID'),
        certificado=os.getenv('SICOOB_CERTIFICADO'),
        chave_privada=os.getenv('SICOOB_CHAVE_PRIVADA'),
        sandbox_mode=True,  # Use False para produção
    )

    print('✅ Cliente inicializado')
    print(f'   - Modo: {"Sandbox" if sicoob.sandbox_mode else "Produção"}')
    print()

    # =========================================================
    # PIX - Delegado para pypix-api
    # =========================================================
    print('=' * 50)
    print('OPERAÇÕES PIX (via pypix-api)')
    print('=' * 50)

    # 2.1 Criar cobrança PIX imediata
    print('\n📱 Criando cobrança PIX imediata...')

    txid = f'SICOOB{datetime.now().strftime("%Y%m%d%H%M%S")}'
    cobranca_pix = sicoob.cobranca.pix.criar_cobranca_imediata(
        txid=txid,
        dados={
            'calendario': {
                'expiracao': 3600  # 1 hora
            },
            'valor': {'original': '150.00'},
            'chave': 'sua-chave-pix@sicoob.com.br',
            'solicitacaoPagador': 'Pagamento de serviço',
        },
    )

    print(f'✅ Cobrança PIX criada!')
    print(f'   - TxID: {cobranca_pix.get("txid")}')
    print(f'   - Status: {cobranca_pix.get("status")}')
    print(f'   - QR Code: {cobranca_pix.get("pixCopiaECola", "")[:50]}...')

    # 2.2 Consultar cobrança PIX
    print('\n🔍 Consultando cobrança PIX...')

    consulta = sicoob.cobranca.pix.consultar_cobranca_imediata(txid)
    print(f'✅ Status atual: {consulta.get("status")}')

    # 2.3 Listar cobranças PIX
    print('\n📋 Listando cobranças PIX do período...')

    inicio = (datetime.now() - timedelta(days=7)).isoformat() + 'Z'
    fim = datetime.now().isoformat() + 'Z'

    lista = sicoob.cobranca.pix.listar_cobrancas(inicio=inicio, fim=fim, status='ATIVA')

    print(f'✅ Encontradas {len(lista.get("cobs", []))} cobranças ativas')

    # 2.4 Configurar webhook PIX
    print('\n🔔 Configurando webhook PIX...')

    try:
        webhook = sicoob.cobranca.pix.cadastrar_webhook(
            chave='sua-chave-pix@sicoob.com.br',
            url='https://seu-dominio.com/webhook/pix',
        )
        print(f'✅ Webhook configurado: {webhook.get("webhookUrl")}')
    except Exception as e:
        print(f'⚠️  Webhook já configurado ou erro: {e}')

    # =========================================================
    # BOLETOS - Específico Sicoob
    # =========================================================
    print('\n' + '=' * 50)
    print('OPERAÇÕES BOLETO (específico Sicoob)')
    print('=' * 50)

    # 3.1 Emitir boleto
    print('\n📄 Emitindo boleto bancário...')

    boleto = sicoob.cobranca.boleto.emitir_boleto(
        {
            'numeroContrato': 123456,
            'modalidade': 1,
            'numeroContaCorrente': 654321,
            'especieDocumento': 'DM',
            'dataEmissao': datetime.now().isoformat(),
            'nossoNumero': 1234567,
            'valor': Decimal('250.00'),
            'dataVencimento': (datetime.now() + timedelta(days=30)).isoformat(),
            'pagador': {
                'cpfCnpj': '12345678901',
                'nome': 'João da Silva',
                'endereco': {
                    'logradouro': 'Rua das Flores, 123',
                    'cep': '01234567',
                    'cidade': 'São Paulo',
                    'uf': 'SP',
                },
            },
        }
    )

    print(f'✅ Boleto emitido!')
    print(f'   - Nosso Número: {boleto.get("nossoNumero")}')
    print(f'   - Linha Digitável: {boleto.get("linhaDigitavel", "")[:20]}...')

    # 3.2 Consultar boleto
    print('\n🔍 Consultando boleto...')

    consulta_boleto = sicoob.cobranca.boleto.consultar_boleto(
        numero_cliente=123456, linha_digitavel=boleto.get('linhaDigitavel')
    )

    print(f'✅ Situação: {consulta_boleto.get("situacao")}')

    # =========================================================
    # CONTA CORRENTE - Específico Sicoob
    # =========================================================
    print('\n' + '=' * 50)
    print('OPERAÇÕES CONTA CORRENTE (específico Sicoob)')
    print('=' * 50)

    # 4.1 Consultar saldo
    print('\n💰 Consultando saldo...')

    try:
        saldo = sicoob.conta_corrente.saldo(numero_conta=654321)
        print(f'✅ Saldo disponível: R$ {saldo.get("saldoDisponivel", 0):.2f}')
    except Exception as e:
        print(f'⚠️  Erro ao consultar saldo: {e}')

    # 4.2 Consultar extrato
    print('\n📊 Consultando extrato...')

    try:
        extrato = sicoob.conta_corrente.extrato(
            numero_conta=654321,
            data_inicio=datetime.now() - timedelta(days=30),
            data_fim=datetime.now(),
        )

        transacoes = extrato.get('transacoes', [])
        print(f'✅ Encontradas {len(transacoes)} transações no período')

        for transacao in transacoes[:3]:  # Primeiras 3 transações
            print(f'   - {transacao.get("data")}: R$ {transacao.get("valor"):.2f}')

    except Exception as e:
        print(f'⚠️  Erro ao consultar extrato: {e}')

    # =========================================================
    # ARQUITETURA DO SDK
    # =========================================================
    print('\n' + '=' * 50)
    print('ARQUITETURA DO SDK')
    print('=' * 50)

    print("""
    Sicoob SDK
    ├── PIX (pypix-api)
    │   ├── Cobranças imediatas (COB)
    │   ├── Cobranças com vencimento (COBV)
    │   ├── Webhooks
    │   └── QR Codes
    │
    ├── Boletos (específico Sicoob)
    │   ├── Emissão
    │   ├── Consulta
    │   ├── Baixa
    │   └── Alteração
    │
    └── Conta Corrente (específico Sicoob)
        ├── Saldo
        ├── Extrato
        └── Transferências
    
    ✨ PIX usa pypix-api (genérica para todos os bancos)
    ✨ Boleto e Conta Corrente são específicos do Sicoob
    """)

    print('\n✅ Exemplo completo executado com sucesso!')


def exemplo_pix_detalhado():
    """Demonstra que todos os métodos da pypix-api estão disponíveis"""

    print('=' * 50)
    print('MÉTODOS PIX DISPONÍVEIS (pypix-api)')
    print('=' * 50)

    sicoob = Sicoob(
        client_id=os.getenv('SICOOB_CLIENT_ID'),
        certificado=os.getenv('SICOOB_CERTIFICADO'),
        chave_privada=os.getenv('SICOOB_CHAVE_PRIVADA'),
        sandbox_mode=True,
    )

    # O wrapper PixAPI delega TODOS os métodos para pypix-api
    # através do método __getattr__

    pix_api = sicoob.cobranca.pix

    print('\n📝 Métodos de Cobrança Imediata (COB):')
    print('   - criar_cob(txid, dados)')
    print('   - consultar_cob(txid)')
    print('   - revisar_cob(txid, dados)')
    print('   - listar_cob(inicio, fim, **filtros)')

    print('\n📅 Métodos de Cobrança com Vencimento (COBV):')
    print('   - criar_cobv(txid, dados)')
    print('   - consultar_cobv(txid, revisao)')
    print('   - listar_cobv(inicio, fim, **filtros)')
    print('   - revisar_cobv(txid, dados)')

    print('\n📦 Métodos de Lote (LOTECOBV):')
    print('   - criar_lotecobv(id, dados)')
    print('   - consultar_lotecobv(id)')
    print('   - listar_lotecobv(inicio, fim)')

    print('\n🔔 Métodos de Webhook:')
    print('   - configurar_webhook(chave, url)')
    print('   - consultar_webhook(chave)')
    print('   - excluir_webhook(chave)')
    print('   - listar_webhooks()')

    print('\n🔑 Métodos de Payload Location:')
    print('   - criar_location(tipo_cob, txid)')
    print('   - consultar_location(id)')
    print('   - desvincular_location(id)')

    print('\n💸 Métodos de PIX (pagamentos):')
    print('   - consultar_pix(e2eid)')
    print('   - listar_pix(inicio, fim, **filtros)')
    print('   - solicitar_devolucao(e2eid, id, valor)')
    print('   - consultar_devolucao(e2eid, id)')

    print('\n✨ TODOS esses métodos estão disponíveis através do proxy!')
    print(
        '✨ Novos métodos adicionados na pypix-api ficam automaticamente disponíveis!'
    )

    # Exemplo de uso direto (qualquer método da pypix-api funciona)
    try:
        # Método existe na pypix-api? Funciona automaticamente!
        resultado = pix_api.algum_metodo_novo_da_pypix_api()
    except AttributeError:
        print('\n⚠️  Método ainda não existe na pypix-api')
    except Exception as e:
        print(f'\n⚠️  Erro tratado pelo wrapper: {e}')


if __name__ == '__main__':
    # Execute o exemplo completo
    exemplo_completo()

    # Descomente para ver todos os métodos PIX disponíveis
    # exemplo_pix_detalhado()
