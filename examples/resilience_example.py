"""Exemplo de uso do sistema de resiliência do Sicoob SDK"""

import requests
from sicoob import Sicoob
from sicoob.resilience import (
    RetryConfig,
    create_resilient_session,
    resilient_request
)


def example_basic_resilience():
    """Exemplo básico usando resiliência automática"""
    print("=== Exemplo 1: Resiliência automática ===")
    
    # Cliente com resiliência habilitada por padrão
    cliente = Sicoob(
        client_id="seu_client_id",
        certificate_path="/path/to/certificate.pem",
        private_key_path="/path/to/private_key.key",
        sandbox_mode=True
    )
    
    try:
        # Operações PIX usam timeout específico (45s)
        cobranca = cliente.pix.criar_cobranca_imediata(
            txid="abcd1234567890123456789012345",
            dados={
                "calendario": {"expiracao": 3600},
                "valor": {"original": "100.00"},
                "chave": "usuario@exemplo.com"
            }
        )
        print(f"Cobrança PIX criada: {cobranca['txid']}")
        
    except Exception as e:
        print(f"Erro após todas as tentativas: {e}")


def example_custom_retry_config():
    """Exemplo com configuração personalizada de retry"""
    print("\n=== Exemplo 2: Configuração personalizada ===")
    
    # Configuração de retry personalizada
    retry_config = RetryConfig(
        max_retries=5,          # Máximo 5 tentativas
        base_delay=0.5,         # Delay inicial de 500ms
        max_delay=10.0,         # Delay máximo de 10s
        backoff_factor=1.5,     # Backoff menos agressivo
        jitter=True             # Com aleatoriedade
    )
    
    cliente = Sicoob(
        client_id="seu_client_id",
        certificate_path="/path/to/certificate.pem",
        private_key_path="/path/to/private_key.key",
        sandbox_mode=True,
        enable_resilience=True,
        retry_config=retry_config
    )
    
    try:
        # Emissão de boleto com retry personalizado
        boleto = cliente.boleto.emitir_boleto({
            "numeroConvenio": "123456",
            "valor": "250.00",
            "dataVencimento": "2024-12-31",
            "pagador": {
                "nome": "João Silva",
                "documento": "12345678901"
            }
        })
        print(f"Boleto emitido: {boleto['nossoNumero']}")
        
    except Exception as e:
        print(f"Erro após 5 tentativas: {e}")


def example_disable_resilience():
    """Exemplo desabilitando resiliência"""
    print("\n=== Exemplo 3: Sem resiliência ===")
    
    cliente = Sicoob(
        client_id="seu_client_id", 
        certificate_path="/path/to/certificate.pem",
        private_key_path="/path/to/private_key.key",
        sandbox_mode=True,
        enable_resilience=False  # Desabilita retry e circuit breaker
    )
    
    try:
        saldo = cliente.conta_corrente.consultar_saldo(
            agencia="1234",
            conta="567890"
        )
        print(f"Saldo: R$ {saldo['saldoAtual']}")
        
    except Exception as e:
        print(f"Erro na primeira tentativa: {e}")


def example_resilient_session():
    """Exemplo criando sessão resiliente manualmente"""
    print("\n=== Exemplo 4: Sessão resiliente manual ===")
    
    # Configura retry específico
    retry_config = RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        backoff_factor=2.0
    )
    
    # Cria sessão resiliente
    session = create_resilient_session(
        retry_config=retry_config,
        timeout=(5, 20)  # 5s conexão, 20s leitura
    )
    
    try:
        # Usa sessão resiliente diretamente
        response = session.get(
            "https://api.exemplo.com/dados",
            headers={"Authorization": "Bearer token"}
        )
        print(f"Resposta: {response.status_code}")
        
    except Exception as e:
        print(f"Erro após retries: {e}")


@resilient_request(max_retries=2, circuit_breaker_enabled=True)
def operacao_com_circuit_breaker():
    """Exemplo de função com circuit breaker"""
    import random
    
    # Simula falha em 60% das chamadas
    if random.random() < 0.6:
        raise requests.exceptions.ConnectionError("Falha simulada")
    
    return "Operação bem-sucedida!"


def example_circuit_breaker():
    """Exemplo de circuit breaker em ação"""
    print("\n=== Exemplo 5: Circuit breaker ===")
    
    # Faz várias chamadas para demonstrar circuit breaker
    for i in range(10):
        try:
            resultado = operacao_com_circuit_breaker()
            print(f"Tentativa {i+1}: {resultado}")
        except Exception as e:
            print(f"Tentativa {i+1}: Erro - {e}")


def example_monitoring_metrics():
    """Exemplo de monitoramento de métricas"""
    print("\n=== Exemplo 6: Métricas de resiliência ===")
    
    from sicoob.resilience import _circuit_breakers
    
    # Simula algumas operações
    for _ in range(5):
        try:
            operacao_com_circuit_breaker()
        except Exception:
            pass
    
    # Mostra métricas dos circuit breakers
    for endpoint, cb in _circuit_breakers.items():
        print(f"Circuit breaker '{endpoint}':")
        print(f"  Estado: {cb.state.value}")
        print(f"  Falhas consecutivas: {cb.failure_count}")
        if cb.last_failure_time:
            import time
            tempo_desde_falha = time.time() - cb.last_failure_time
            print(f"  Tempo desde última falha: {tempo_desde_falha:.2f}s")


def main():
    """Executa todos os exemplos"""
    print("Exemplos do Sistema de Resiliência - Sicoob SDK")
    print("=" * 50)
    
    try:
        example_basic_resilience()
        example_custom_retry_config() 
        example_disable_resilience()
        example_resilient_session()
        example_circuit_breaker()
        example_monitoring_metrics()
        
    except Exception as e:
        print(f"Erro geral: {e}")


if __name__ == "__main__":
    main()