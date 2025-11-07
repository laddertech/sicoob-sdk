"""Exemplo de emissão em lote de boletos com processamento assíncrono.

Este exemplo demonstra como emitir múltiplos boletos de forma eficiente
usando a versão assíncrona da biblioteca, com rate limiting e tratamento
robusto de erros.

Características:
- Processamento concorrente
- Rate limiting para respeitar limites da API
- Retry automático com emitir_e_verificar_boleto()
- Tratamento de erros individual por boleto
- Estatísticas de processamento
"""

import asyncio
import os
from asyncio import Semaphore
from datetime import datetime, timedelta

from sicoob.async_client import AsyncSicoob


async def emitir_lote_boletos_exemplo():
    """Exemplo completo de emissão em lote de boletos."""

    # Configuração do cliente
    client_id = os.getenv('SICOOB_CLIENT_ID')
    certificado_pfx = os.getenv('SICOOB_CERT_PFX')
    senha_pfx = os.getenv('SICOOB_SENHA_PFX')

    # Dados de exemplo para emissão em lote
    # (substitua pelos seus dados reais)
    dados_base = {
        'numeroCliente': 123456,
        'codigoModalidade': 1,
        'numeroContaCorrente': 12345,
        'codigoEspecieDocumento': 'DM',
        'identificacaoEmissaoBoleto': 1,
        'identificacaoDistribuicaoBoleto': 1,
        'tipoDesconto': 0,
        'tipoMulta': 0,
        'tipoJurosMora': 3,
        'numeroParcela': 1,
    }

    # Gera lista de boletos a emitir (exemplo: 50 boletos)
    lista_boletos = []
    data_vencimento = datetime.now() + timedelta(days=30)

    for i in range(1, 51):  # 50 boletos
        boleto = {
            **dados_base,
            'dataEmissao': datetime.now().strftime('%Y-%m-%d'),
            'dataVencimento': data_vencimento.strftime('%Y-%m-%d'),
            'valor': 100.00 + i,  # Valores diferentes
            'seuNumero': f'MENSALIDADE-2024-{i:03d}',
            'pagador': {
                'numeroCpfCnpj': f'11144477{i:03d}',
                'nome': f'Cliente {i}',
                'endereco': 'Rua Teste, 123',
                'bairro': 'Centro',
                'cidade': 'São Paulo',
                'cep': '01001000',
                'uf': 'SP',
            },
        }
        lista_boletos.append(boleto)

    # Estatísticas
    stats = {
        'total': len(lista_boletos),
        'sucesso': 0,
        'erro': 0,
        'tempo_inicio': datetime.now(),
        'erros_detalhados': [],
    }

    async with AsyncSicoob(
        client_id=client_id,
        certificado_pfx=certificado_pfx,
        senha_pfx=senha_pfx,
        max_concurrent_requests=5,  # Limite de requisições concorrentes
    ) as client:
        # Rate limiter: ~4.5 req/s (limite da API Sicoob)
        limiter = Semaphore(5)  # Max 5 concurrent
        delay_entre_requests = 1 / 4.5  # ~220ms entre requests

        async def emitir_com_rate_limit(dados, indice):
            """Emite um boleto respeitando rate limit."""
            async with limiter:
                try:
                    # Delay para respeitar rate limit
                    await asyncio.sleep(delay_entre_requests)

                    # Usa emitir_e_verificar_boleto para maior robustez
                    resultado = (
                        await client.cobranca.boleto.emitir_e_verificar_boleto(
                            dados, max_tentativas=2, delay_inicial=0.5
                        )
                    )

                    stats['sucesso'] += 1
                    print(
                        f"✅ [{indice:03d}] Boleto emitido: "
                        f"{resultado.get('resultado', {}).get('nossoNumero', 'N/A')}"
                    )

                    return {'status': 'sucesso', 'indice': indice, 'dados': resultado}

                except Exception as e:
                    stats['erro'] += 1
                    erro_detalhado = {
                        'indice': indice,
                        'seu_numero': dados.get('seuNumero'),
                        'erro': str(e),
                    }
                    stats['erros_detalhados'].append(erro_detalhado)

                    print(f"❌ [{indice:03d}] Erro: {e}")

                    return {'status': 'erro', 'indice': indice, 'erro': str(e)}

        # Processa todos os boletos em paralelo (com rate limiting)
        print(f'\n🚀 Iniciando emissão de {len(lista_boletos)} boletos...\n')

        tasks = [
            emitir_com_rate_limit(boleto, i)
            for i, boleto in enumerate(lista_boletos, 1)
        ]

        resultados = await asyncio.gather(*tasks, return_exceptions=True)

        # Calcula tempo total
        stats['tempo_fim'] = datetime.now()
        stats['duracao_segundos'] = (
            stats['tempo_fim'] - stats['tempo_inicio']
        ).total_seconds()

        # Exibe estatísticas
        print('\n' + '=' * 60)
        print('📊 ESTATÍSTICAS DE PROCESSAMENTO')
        print('=' * 60)
        print(f"Total de boletos: {stats['total']}")
        print(f"✅ Sucessos: {stats['sucesso']}")
        print(f"❌ Erros: {stats['erro']}")
        print(f"⏱️  Tempo total: {stats['duracao_segundos']:.2f}s")
        print(
            f"📈 Taxa média: {stats['total'] / stats['duracao_segundos']:.2f} boletos/s"
        )

        if stats['erros_detalhados']:
            print('\n❌ ERROS DETALHADOS:')
            for erro in stats['erros_detalhados'][:10]:  # Mostra apenas primeiros 10
                print(f"  - [{erro['indice']:03d}] {erro['seu_numero']}: {erro['erro']}")

            if len(stats['erros_detalhados']) > 10:
                print(f"  ... e mais {len(stats['erros_detalhados']) - 10} erros")

        print('=' * 60)

        return resultados, stats


if __name__ == '__main__':
    # Executa o exemplo
    resultados, stats = asyncio.run(emitir_lote_boletos_exemplo())

    # Pode processar resultados adicionalmente aqui
    # Ex: salvar em banco de dados, gerar relatório, etc.
