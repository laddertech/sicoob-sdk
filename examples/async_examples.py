"""Exemplos práticos de uso das funcionalidades assíncronas do Sicoob SDK.

Este arquivo demonstra como usar async/await para melhorar significativamente
a performance em cenários de high-throughput, processamento em lote e
operações concorrentes.

Exemplos incluídos:
- Processamento paralelo de cobranças PIX
- Consulta concorrente de extratos
- Monitoramento em tempo real
- Cache assíncrono para otimização
- Processamento de grandes volumes de dados
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

from sicoob.async_client import AsyncSicoob, gather_with_concurrency, async_batch_processor
from sicoob.async_cache import AsyncCacheManager, async_cached
from sicoob.cache import CacheConfig


async def exemplo_basico_async():
    """Exemplo básico de uso assíncrono vs síncrono."""
    print("=== Exemplo 1: Comparação Async vs Sync ===")
    
    # Configuração
    client_config = {
        'client_id': 'seu_client_id',
        'certificado_pfx': '/path/to/certificate.pfx',
        'senha_pfx': 'sua_senha_pfx',
        'sandbox_mode': True,
        'max_concurrent_requests': 10
    }
    
    txids = [f"txid_exemplo_{i:03d}" for i in range(20)]
    
    print(f"Consultando {len(txids)} cobranças PIX...")
    
    # Versão assíncrona
    async with AsyncSicoob(**client_config) as client:
        start_time = time.time()
        
        # Consulta todas as cobranças em paralelo
        tasks = [
            client.cobranca.consultar_cobranca_pix(txid)
            for txid in txids
        ]
        
        try:
            results_async = await asyncio.gather(*tasks, return_exceptions=True)
            async_duration = time.time() - start_time
            
            # Conta sucessos e erros
            sucessos = sum(1 for r in results_async if not isinstance(r, Exception))
            erros = len(results_async) - sucessos
            
            print(f"Async: {len(txids)} consultas em {async_duration:.2f}s")
            print(f"  Sucessos: {sucessos}, Erros: {erros}")
            print(f"  Throughput: {len(txids)/async_duration:.1f} req/s")
            
        except Exception as e:
            print(f"Erro na versão assíncrona: {e}")
    
    print(f"Comparação: Async foi ~{20 * 0.5 / async_duration:.1f}x mais rápido")
    print()


async def exemplo_processamento_lote_pix():
    """Processamento eficiente de lote de cobranças PIX."""
    print("=== Exemplo 2: Processamento em Lote PIX ===")
    
    async with AsyncSicoob(
        client_id='seu_client_id',
        sandbox_mode=True,
        max_concurrent_requests=15
    ) as client:
        
        # Dados para criar cobranças em lote
        dados_cobrancas = []
        for i in range(50):
            dados_cobrancas.append((
                f"txid_lote_{i:04d}_{int(time.time())}",
                {
                    "calendario": {"expiracao": 3600},
                    "valor": {"original": f"{(i + 1) * 10.50:.2f}"},
                    "chave": "usuario@exemplo.com",
                    "solicitacaoPagador": f"Cobrança #{i+1} - Lote de exemplo"
                }
            ))
        
        print(f"Criando {len(dados_cobrancas)} cobranças PIX em lote...")
        
        start_time = time.time()
        
        # Processa em lotes menores para não sobrecarregar a API
        batch_size = 10
        total_sucessos = 0
        total_erros = 0
        
        for i in range(0, len(dados_cobrancas), batch_size):
            batch = dados_cobrancas[i:i + batch_size]
            print(f"  Processando lote {i//batch_size + 1}/{(len(dados_cobrancas)-1)//batch_size + 1}...")
            
            try:
                # Cria cobranças do lote em paralelo
                tasks = [
                    client.cobranca.criar_cobranca_pix(txid, dados)
                    for txid, dados in batch
                ]
                
                results = await gather_with_concurrency(tasks, max_concurrency=5)
                
                # Conta resultados
                batch_sucessos = sum(1 for r in results if r.get('status') in ['ATIVA', 'CRIADA'])
                batch_erros = len(batch) - batch_sucessos
                
                total_sucessos += batch_sucessos
                total_erros += batch_erros
                
                print(f"    Lote: {batch_sucessos} sucessos, {batch_erros} erros")
                
                # Pausa curta entre lotes para respeitar rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"    Erro no lote: {e}")
                total_erros += len(batch)
        
        duration = time.time() - start_time
        
        print(f"\nResultados finais:")
        print(f"  Total: {len(dados_cobrancas)} cobranças")
        print(f"  Sucessos: {total_sucessos}")
        print(f"  Erros: {total_erros}")
        print(f"  Tempo: {duration:.2f}s")
        print(f"  Throughput: {len(dados_cobrancas)/duration:.1f} cobranças/s")
    print()


async def exemplo_monitoramento_tempo_real():
    """Monitoramento de cobranças PIX em tempo real."""
    print("=== Exemplo 3: Monitoramento Tempo Real ===")
    
    async with AsyncSicoob(client_id='seu_client_id', sandbox_mode=True) as client:
        
        # Lista de chaves PIX para monitorar
        chaves_monitorar = [
            "usuario@exemplo.com",
            "11999999999",  # Telefone
            "+5511999999999"  # Telefone internacional
        ]
        
        print(f"Iniciando monitoramento de {len(chaves_monitorar)} chaves PIX...")
        print("(Pressione Ctrl+C para interromper)")
        
        # Callback para processar novas cobranças
        async def processar_nova_cobranca(cobranca):
            txid = cobranca.get('txid', 'N/A')
            valor = cobranca.get('valor', {}).get('original', 'N/A')
            status = cobranca.get('status', 'N/A')
            
            print(f"  🆕 Nova cobrança: {txid}")
            print(f"    Valor: R$ {valor}")
            print(f"    Status: {status}")
            print(f"    Timestamp: {datetime.now().isoformat()}")
            
            # Aqui você pode adicionar lógica personalizada:
            # - Notificar sistema externo
            # - Atualizar banco de dados
            # - Enviar webhook
            # - etc.
        
        try:
            # Monitora por 60 segundos (ajuste conforme necessário)
            timeout = 60
            start_time = time.time()
            
            async for stats in client.cobranca.pix.monitorar_cobrancas_tempo_real(
                chaves_monitorar,
                intervalo_segundos=10,
                callback_cobranca=processar_nova_cobranca
            ):
                elapsed = time.time() - start_time
                
                print(f"⏱️  Monitoramento - {elapsed:.0f}s")
                print(f"  Chaves: {stats['chaves_monitoradas']}")
                print(f"  Cobranças encontradas: {stats['cobrancas_encontradas']}")
                print(f"  Novas nesta verificação: {stats['novas_cobrancas']}")
                
                if elapsed > timeout:
                    break
                    
        except KeyboardInterrupt:
            print("\n⏹️  Monitoramento interrompido pelo usuário")
        except Exception as e:
            print(f"❌ Erro no monitoramento: {e}")
    
    print("Monitoramento finalizado.")
    print()


async def exemplo_cache_assincrono():
    """Uso do sistema de cache assíncrono para otimização."""
    print("=== Exemplo 4: Cache Assíncrono ===")
    
    # Configuração do cache
    cache_config = CacheConfig(
        default_ttl=300,  # 5 minutos
        max_size=1000,
        enable_compression=True,
        cleanup_interval=60
    )
    
    cache = AsyncCacheManager(cache_config)
    
    async with AsyncSicoob(client_id='seu_client_id', sandbox_mode=True) as client:
        
        # Função com cache automático
        @cache.cached(ttl=600, key_prefix="cobranca_pix:", tags=["pix"])
        async def consultar_cobranca_cached(txid: str):
            print(f"  📡 Consultando API para {txid}")
            return await client.cobranca.consultar_cobranca_pix(txid)
        
        # Lista de TXIDs para teste
        txids = [f"txid_cache_test_{i}" for i in range(5)]
        
        print("Primeira execução (sem cache):")
        start_time = time.time()
        
        try:
            tasks = [consultar_cobranca_cached(txid) for txid in txids]
            results1 = await gather_with_concurrency(tasks, max_concurrency=3)
            time1 = time.time() - start_time
            
            print(f"  Tempo: {time1:.2f}s")
            
            print("\nSegunda execução (com cache):")
            start_time = time.time()
            
            tasks = [consultar_cobranca_cached(txid) for txid in txids]
            results2 = await gather_with_concurrency(tasks, max_concurrency=3)
            time2 = time.time() - start_time
            
            print(f"  Tempo: {time2:.2f}s")
            print(f"  Melhoria: {time1/time2:.1f}x mais rápido com cache")
            
            # Estatísticas do cache
            stats = await cache.get_stats()
            print(f"\nEstatísticas do cache:")
            print(f"  Hits: {stats['hits']}")
            print(f"  Misses: {stats['misses']}")
            print(f"  Hit rate: {stats['hit_rate']:.2%}")
            print(f"  Entradas: {stats['entry_count']}")
            
        except Exception as e:
            print(f"Erro no exemplo de cache: {e}")
    
    await cache.shutdown()
    print()


async def exemplo_processamento_grandes_volumes():
    """Processamento otimizado de grandes volumes de dados."""
    print("=== Exemplo 5: Grandes Volumes ===")
    
    async with AsyncSicoob(
        client_id='seu_client_id',
        sandbox_mode=True,
        max_concurrent_requests=20
    ) as client:
        
        # Simula processamento de extrato de múltiplas contas
        contas = [f"12345-{i:02d}" for i in range(10)]
        
        # Período de 30 dias
        fim = datetime.now()
        inicio = fim - timedelta(days=30)
        data_inicio = inicio.strftime('%Y-%m-%d')
        data_fim = fim.strftime('%Y-%m-%d')
        
        print(f"Processando extratos de {len(contas)} contas")
        print(f"Período: {data_inicio} a {data_fim}")
        
        async def processar_conta(numero_conta: str) -> Dict[str, Any]:
            """Processa extrato de uma conta específica."""
            try:
                extrato = await client.conta_corrente.get_extrato(
                    data_inicio, data_fim, numero_conta
                )
                
                # Simula análise dos dados
                movimentos = extrato.get('movimentos', [])
                total_credito = sum(
                    m.get('valor', 0) for m in movimentos
                    if m.get('tipo') == 'CREDITO'
                )
                total_debito = sum(
                    m.get('valor', 0) for m in movimentos
                    if m.get('tipo') == 'DEBITO'
                )
                
                return {
                    'conta': numero_conta,
                    'movimentos': len(movimentos),
                    'total_credito': total_credito,
                    'total_debito': total_debito,
                    'saldo_periodo': total_credito - total_debito,
                    'processado_em': datetime.now().isoformat()
                }
                
            except Exception as e:
                return {
                    'conta': numero_conta,
                    'erro': str(e),
                    'processado_em': datetime.now().isoformat()
                }
        
        # Processamento com controle de concorrência
        print("Iniciando processamento paralelo...")
        start_time = time.time()
        
        # Usa batch processor para otimizar o processamento
        async with async_batch_processor(
            contas,
            processar_conta,
            batch_size=5,
            max_concurrency=4
        ) as resultados:
            
            duration = time.time() - start_time
            
            # Análise dos resultados
            sucessos = [r for r in resultados if 'erro' not in r]
            erros = [r for r in resultados if 'erro' in r]
            
            print(f"\nProcessamento concluído em {duration:.2f}s")
            print(f"Sucessos: {len(sucessos)}")
            print(f"Erros: {len(erros)}")
            
            if sucessos:
                print(f"\nResumo financeiro:")
                total_movimentos = sum(r['movimentos'] for r in sucessos)
                total_credito = sum(r['total_credito'] for r in sucessos)
                total_debito = sum(r['total_debito'] for r in sucessos)
                
                print(f"  Total de movimentos: {total_movimentos:,}")
                print(f"  Total de créditos: R$ {total_credito:,.2f}")
                print(f"  Total de débitos: R$ {total_debito:,.2f}")
                print(f"  Saldo líquido: R$ {total_credito - total_debito:,.2f}")
            
            if erros:
                print(f"\nContas com erro:")
                for erro in erros:
                    print(f"  {erro['conta']}: {erro['erro']}")
    
    print()


async def exemplo_relatorio_performance():
    """Geração de relatório de performance para operações PIX."""
    print("=== Exemplo 6: Relatório de Performance ===")
    
    async with AsyncSicoob(client_id='seu_client_id', sandbox_mode=True) as client:
        
        # Lista de TXIDs para análise de performance
        txids = [f"perf_test_txid_{i:05d}" for i in range(100)]
        
        print(f"Analisando performance para {len(txids)} TXIDs...")
        
        # Testa diferentes níveis de concorrência
        concorrencias = [1, 5, 10, 15, 20]
        resultados_performance = {}
        
        for max_concorrencia in concorrencias:
            print(f"\nTestando com concorrência {max_concorrencia}:")
            
            try:
                # Gera relatório de performance
                relatorio = await client.cobranca.pix.gerar_relatorio_performance(
                    txids, max_concorrencia
                )
                
                metricas = relatorio['metricas_performance']
                resultados_performance[max_concorrencia] = metricas
                
                print(f"  Tempo total: {metricas['tempo_total_segundos']:.2f}s")
                print(f"  Throughput: {metricas['throughput_txids_por_segundo']:.1f} req/s")
                print(f"  Taxa de sucesso: {metricas['taxa_sucesso']:.1f}%")
                
            except Exception as e:
                print(f"  Erro com concorrência {max_concorrencia}: {e}")
        
        # Análise comparativa
        print(f"\n=== Análise Comparativa ===")
        
        if resultados_performance:
            melhor_throughput = max(
                resultados_performance.items(),
                key=lambda x: x[1]['throughput_txids_por_segundo']
            )
            
            print(f"Melhor throughput: {melhor_throughput[1]['throughput_txids_por_segundo']:.1f} req/s")
            print(f"  Concorrência ótima: {melhor_throughput[0]}")
            
            # Recomendações
            if melhor_throughput[0] <= 5:
                print("💡 Recomendação: API pode estar limitando rate limit")
            elif melhor_throughput[0] >= 20:
                print("💡 Recomendação: Rede/CPU podem ser o gargalo")
            else:
                print("💡 Recomendação: Concorrência está bem balanceada")
    
    print()


async def exemplo_integracao_completa():
    """Exemplo de integração completa com todas as funcionalidades."""
    print("=== Exemplo 7: Integração Completa ===")
    
    # Cache para otimização
    cache = AsyncCacheManager(CacheConfig(
        default_ttl=600,
        enable_compression=True
    ))
    
    async with AsyncSicoob(
        client_id='seu_client_id',
        sandbox_mode=True,
        max_concurrent_requests=10
    ) as client:
        
        print("🚀 Iniciando processamento integrado...")
        
        # 1. Consulta saldos de múltiplas contas
        print("\n📊 Consultando saldos...")
        contas = [f"conta_{i:03d}" for i in range(5)]
        
        @cache.cached(ttl=300, key_prefix="saldo:")
        async def get_saldo_cached(conta):
            return await client.conta_corrente.get_saldo(conta)
        
        tasks_saldo = [get_saldo_cached(conta) for conta in contas]
        saldos = await gather_with_concurrency(tasks_saldo, max_concurrency=3)
        
        print(f"✅ Consultados saldos de {len(contas)} contas")
        
        # 2. Cria cobranças PIX baseadas nos saldos
        print("\n💰 Criando cobranças PIX...")
        cobrancas_criar = []
        
        for i, (conta, saldo_info) in enumerate(zip(contas, saldos)):
            if isinstance(saldo_info, dict) and not saldo_info.get('erro'):
                valor = min(100.0, float(saldo_info.get('saldo', 0)) * 0.1)
                
                cobrancas_criar.append((
                    f"integracao_txid_{i:03d}_{int(time.time())}",
                    {
                        "calendario": {"expiracao": 7200},  # 2 horas
                        "valor": {"original": f"{valor:.2f}"},
                        "chave": "integracao@exemplo.com",
                        "solicitacaoPagador": f"Cobrança integrada - Conta {conta}"
                    }
                ))
        
        if cobrancas_criar:
            tasks_cobranca = [
                client.cobranca.criar_cobranca_pix(txid, dados)
                for txid, dados in cobrancas_criar
            ]
            
            cobrancas_criadas = await gather_with_concurrency(
                tasks_cobranca, max_concurrency=5
            )
            
            sucessos_cobranca = sum(
                1 for c in cobrancas_criadas
                if isinstance(c, dict) and c.get('status') in ['ATIVA', 'CRIADA']
            )
            
            print(f"✅ Criadas {sucessos_cobranca}/{len(cobrancas_criar)} cobranças")
        
        # 3. Monitora por período curto
        print("\n👁️  Monitoramento rápido...")
        
        chaves_monitorar = ["integracao@exemplo.com"]
        monitor_count = 0
        
        try:
            async for stats in client.cobranca.pix.monitorar_cobrancas_tempo_real(
                chaves_monitorar,
                intervalo_segundos=5
            ):
                monitor_count += 1
                print(f"  Verificação {monitor_count}: {stats['cobrancas_encontradas']} cobranças")
                
                if monitor_count >= 3:  # Apenas 3 verificações
                    break
                    
        except Exception as e:
            print(f"  Erro no monitoramento: {e}")
        
        # 4. Relatório final
        print(f"\n📈 Estatísticas finais:")
        cache_stats = await cache.get_stats()
        
        print(f"  Cache - Hits: {cache_stats['hits']}, Hit rate: {cache_stats['hit_rate']:.2%}")
        print(f"  Operações realizadas:")
        print(f"    - Consultas de saldo: {len(contas)}")
        print(f"    - Cobranças criadas: {len(cobrancas_criar) if 'cobrancas_criar' in locals() else 0}")
        print(f"    - Verificações de monitoramento: {monitor_count}")
        
        print("✨ Processamento integrado concluído!")
    
    await cache.shutdown()
    print()


async def main():
    """Executa todos os exemplos."""
    print("🔥 EXEMPLOS ASYNC/AWAIT - SICOOB SDK 🔥")
    print("=" * 50)
    
    exemplos = [
        exemplo_basico_async,
        exemplo_processamento_lote_pix,
        exemplo_monitoramento_tempo_real,
        exemplo_cache_assincrono,
        exemplo_processamento_grandes_volumes,
        exemplo_relatorio_performance,
        exemplo_integracao_completa
    ]
    
    for i, exemplo in enumerate(exemplos, 1):
        try:
            print(f"\n{'='*20} EXEMPLO {i} {'='*20}")
            await exemplo()
        except Exception as e:
            print(f"❌ Erro no exemplo {i}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*50}")
    print("🎉 Todos os exemplos concluídos!")
    print("\nBenefícios do Async/Await:")
    print("• ⚡ 5-20x mais rápido para operações em lote")
    print("• 🚀 Melhor utilização de recursos")
    print("• 📊 Throughput otimizado para high-volume")
    print("• 🔄 Processamento paralelo inteligente")
    print("• 💾 Cache assíncrono para performance")


if __name__ == "__main__":
    # Configura logging para ver detalhes
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Executa exemplos
    asyncio.run(main())