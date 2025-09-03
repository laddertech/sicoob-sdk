"""Exemplo de uso do sistema de paginação do Sicoob SDK"""

from datetime import datetime, timedelta

from sicoob import Sicoob
from sicoob.pagination import PaginationConfig


def example_basic_pagination():
    """Exemplo básico de paginação automática"""
    print("=== Exemplo 1: Paginação básica ===")
    
    cliente = Sicoob(
        client_id="seu_client_id",
        certificate_path="/path/to/certificate.pem",
        private_key_path="/path/to/private_key.key",
        sandbox_mode=True
    )
    
    # Período de 30 dias
    fim = datetime.now()
    inicio = fim - timedelta(days=30)
    
    # Lista todas as cobranças automaticamente, página por página
    cobranca_count = 0
    for cobranca in cliente.pix.listar_cobrancas_paginado(
        inicio=inicio.isoformat() + "Z",
        fim=fim.isoformat() + "Z"
    ):
        cobranca_count += 1
        print(f"Cobrança {cobranca_count}: TXID {cobranca['txid']}")
        
        # Para demonstração, para após 10 cobranças
        if cobranca_count >= 10:
            break
    
    print(f"Total processado: {cobranca_count} cobranças")


def example_custom_pagination_config():
    """Exemplo com configuração personalizada"""
    print("\n=== Exemplo 2: Configuração personalizada ===")
    
    cliente = Sicoob(
        client_id="seu_client_id",
        certificate_path="/path/to/certificate.pem", 
        private_key_path="/path/to/private_key.key",
        sandbox_mode=True
    )
    
    # Configuração personalizada
    config = PaginationConfig(
        page_size=50,           # 50 items por página
        max_pages=5,            # Máximo 5 páginas (250 items total)
        auto_retry=True,        # Retry automático
        max_retries=2,          # Máximo 2 tentativas
        retry_delay=0.5         # 500ms entre tentativas
    )
    
    fim = datetime.now()
    inicio = fim - timedelta(days=7)  # Última semana
    
    try:
        for cobranca in cliente.pix.listar_cobrancas_paginado(
            inicio=inicio.isoformat() + "Z",
            fim=fim.isoformat() + "Z",
            pagination=config,
            status="ATIVA"  # Apenas cobranças ativas
        ):
            print(f"TXID: {cobranca['txid']}, Valor: {cobranca['valor']['original']}")
            
    except Exception as e:
        print(f"Erro durante paginação: {e}")


def example_page_by_page():
    """Exemplo processando página por página com metadados"""
    print("\n=== Exemplo 3: Página por página ===")
    
    cliente = Sicoob(
        client_id="seu_client_id",
        certificate_path="/path/to/certificate.pem",
        private_key_path="/path/to/private_key.key",
        sandbox_mode=True
    )
    
    config = PaginationConfig(page_size=25, max_pages=3)
    
    fim = datetime.now()
    inicio = fim - timedelta(days=15)
    
    total_items = 0
    total_value = 0.0
    
    for page in cliente.pix.listar_cobrancas_por_paginas(
        inicio=inicio.isoformat() + "Z",
        fim=fim.isoformat() + "Z",
        pagination=config
    ):
        print(f"\n--- Página {page.page_info.current_page} ---")
        print(f"Items nesta página: {len(page)}")
        print(f"Tempo da requisição: {page.request_duration:.2f}s")
        print(f"Primeira página: {page.page_info.is_first_page}")
        print(f"Última página: {page.page_info.is_last_page}")
        
        # Processa items da página
        page_value = 0.0
        for cobranca in page.items:
            valor = float(cobranca['valor']['original'])
            page_value += valor
            total_items += 1
        
        total_value += page_value
        print(f"Valor total da página: R$ {page_value:.2f}")
    
    print(f"\n=== Resumo Final ===")
    print(f"Total de cobranças: {total_items}")
    print(f"Valor total: R$ {total_value:.2f}")


def example_large_dataset_processing():
    """Exemplo para processamento de grandes volumes"""
    print("\n=== Exemplo 4: Grandes volumes ===")
    
    cliente = Sicoob(
        client_id="seu_client_id",
        certificate_path="/path/to/certificate.pem",
        private_key_path="/path/to/private_key.key",
        sandbox_mode=True
    )
    
    # Para grandes volumes, use páginas maiores
    config = PaginationConfig(
        page_size=200,          # Páginas grandes para eficiência
        max_pages=None,         # Sem limite de páginas
        auto_retry=True,        # Importante para grandes volumes
        retry_delay=1.0         # Delay maior para evitar rate limiting
    )
    
    fim = datetime.now() 
    inicio = fim - timedelta(days=90)  # 3 meses de dados
    
    # Processa cobranças em lotes para não sobrecarregar memória
    batch_size = 1000
    processed = 0
    batch_data = []
    
    print("Processando cobranças dos últimos 3 meses...")
    
    for cobranca in cliente.pix.listar_cobrancas_paginado(
        inicio=inicio.isoformat() + "Z",
        fim=fim.isoformat() + "Z", 
        pagination=config
    ):
        batch_data.append({
            'txid': cobranca['txid'],
            'valor': cobranca['valor']['original'],
            'status': cobranca.get('status', 'N/A')
        })
        
        processed += 1
        
        # Processa lote quando atinge tamanho limite
        if len(batch_data) >= batch_size:
            print(f"Processando lote de {len(batch_data)} cobranças...")
            
            # Aqui você faria o processamento real dos dados
            # Por exemplo: salvar no banco, gerar relatório, etc.
            process_batch(batch_data)
            
            batch_data.clear()
            print(f"Total processado até agora: {processed}")
    
    # Processa último lote se houver dados restantes
    if batch_data:
        print(f"Processando último lote de {len(batch_data)} cobranças...")
        process_batch(batch_data)
    
    print(f"Processamento concluído: {processed} cobranças")


def process_batch(batch_data):
    """Simula processamento de um lote de dados"""
    total_value = sum(float(item['valor']) for item in batch_data)
    active_count = sum(1 for item in batch_data if item['status'] == 'ATIVA')
    
    print(f"  Lote processado: {len(batch_data)} items")
    print(f"  Valor total: R$ {total_value:.2f}")  
    print(f"  Cobranças ativas: {active_count}")


def example_error_handling():
    """Exemplo de tratamento de erros durante paginação"""
    print("\n=== Exemplo 5: Tratamento de erros ===")
    
    cliente = Sicoob(
        client_id="seu_client_id",
        certificate_path="/path/to/certificate.pem",
        private_key_path="/path/to/private_key.key", 
        sandbox_mode=True
    )
    
    config = PaginationConfig(
        page_size=100,
        auto_retry=True,        # Retry automático habilitado
        max_retries=3,          # Até 3 tentativas
        retry_delay=2.0         # 2s entre tentativas
    )
    
    fim = datetime.now()
    inicio = fim - timedelta(days=30)
    
    successful = 0
    failed = 0
    
    try:
        for cobranca in cliente.pix.listar_cobrancas_paginado(
            inicio=inicio.isoformat() + "Z",
            fim=fim.isoformat() + "Z",
            pagination=config
        ):
            try:
                # Simula processamento que pode falhar
                if 'valor' not in cobranca:
                    raise ValueError("Cobrança sem valor")
                
                valor = float(cobranca['valor']['original'])
                print(f"Processada: {cobranca['txid']} - R$ {valor:.2f}")
                successful += 1
                
            except Exception as e:
                print(f"Erro ao processar cobrança {cobranca.get('txid', 'N/A')}: {e}")
                failed += 1
                continue
                
    except Exception as e:
        print(f"Erro fatal na paginação: {e}")
    
    print(f"\nResultado: {successful} sucessos, {failed} falhas")


def example_filtered_pagination():
    """Exemplo com filtros específicos"""
    print("\n=== Exemplo 6: Paginação com filtros ===")
    
    cliente = Sicoob(
        client_id="seu_client_id",
        certificate_path="/path/to/certificate.pem",
        private_key_path="/path/to/private_key.key",
        sandbox_mode=True
    )
    
    config = PaginationConfig(page_size=50)
    
    fim = datetime.now()
    inicio = fim - timedelta(days=7)
    
    # Filtros específicos
    filtros = {
        'status': 'ATIVA',
        'cpf': '12345678901'  # CPF específico
    }
    
    print("Buscando cobranças ativas para CPF específico...")
    
    count = 0
    for cobranca in cliente.pix.listar_cobrancas_paginado(
        inicio=inicio.isoformat() + "Z",
        fim=fim.isoformat() + "Z",
        pagination=config,
        **filtros
    ):
        print(f"TXID: {cobranca['txid']}")
        print(f"Valor: R$ {cobranca['valor']['original']}")
        print(f"Status: {cobranca.get('status', 'N/A')}")
        print("---")
        
        count += 1
        if count >= 5:  # Limite para demonstração
            break
    
    print(f"Total encontrado: {count} cobranças")


def main():
    """Executa todos os exemplos"""
    print("Exemplos do Sistema de Paginação - Sicoob SDK")
    print("=" * 50)
    
    try:
        example_basic_pagination()
        example_custom_pagination_config()
        example_page_by_page()
        example_large_dataset_processing()
        example_error_handling()
        example_filtered_pagination()
        
    except Exception as e:
        print(f"Erro geral: {e}")


if __name__ == "__main__":
    main()