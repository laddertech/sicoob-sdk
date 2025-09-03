"""Exemplos de configuração por ambiente no Sicoob SDK"""

import os
from sicoob import Sicoob
from sicoob.config import Environment, SicoobConfig


def exemplo_desenvolvimento():
    """Exemplo de configuração para desenvolvimento local"""
    print("🔧 AMBIENTE DE DESENVOLVIMENTO")
    print("=" * 50)
    
    # Método 1: Via parâmetro environment
    client = Sicoob(
        client_id="dev_client_123",
        environment="development"
    )
    
    # Verifica configuração aplicada
    config = SicoobConfig.get_current_config()
    print(f"✅ Ambiente: {config.environment.value}")
    print(f"✅ URL Base: {config.base_url}")
    print(f"✅ Log Level: {config.log_level}")
    print(f"✅ Requer Certificado: {config.require_certificate}")
    print(f"✅ HTTP Logging: {config.log_requests}/{config.log_responses}")
    print(f"✅ Debug Mode: {config.debug_mode}")
    print()


def exemplo_testes():
    """Exemplo de configuração para testes automatizados"""
    print("🧪 AMBIENTE DE TESTES")
    print("=" * 50)
    
    client = Sicoob(
        client_id="test_client_456",
        environment=Environment.TEST
    )
    
    config = SicoobConfig.get_current_config()
    print(f"✅ Ambiente: {config.environment.value}")
    print(f"✅ Log Level: {config.log_level} (mínimo para performance)")
    print(f"✅ Log Format: {config.log_format} (simples)")
    print(f"✅ HTTP Logging: Desabilitado (performance)")
    print(f"✅ Timeout: {config.timeout}s")
    print()


def exemplo_staging():
    """Exemplo de configuração para staging/homologação"""
    print("🚀 AMBIENTE DE STAGING")
    print("=" * 50)
    
    client = Sicoob(
        client_id="staging_client_789",
        certificado_pfx="staging_cert.pfx",
        senha_pfx="staging_password",
        environment="staging"
    )
    
    config = SicoobConfig.get_current_config()
    print(f"✅ Ambiente: {config.environment.value}")
    print(f"✅ URL Base: {config.base_url} (produção)")
    print(f"✅ Log Format: {config.log_format} (estruturado)")
    print(f"✅ Certificado: Obrigatório")
    print(f"✅ HTTP Logging: Habilitado (para debug)")
    print()


def exemplo_producao():
    """Exemplo de configuração para produção"""
    print("🏭 AMBIENTE DE PRODUÇÃO")
    print("=" * 50)
    
    client = Sicoob(
        client_id="prod_client_abc",
        certificado_pfx="production_cert.pfx",
        senha_pfx="production_password",
        environment="production"
    )
    
    config = SicoobConfig.get_current_config()
    print(f"✅ Ambiente: {config.environment.value}")
    print(f"✅ URL Base: {config.base_url}")
    print(f"✅ Max Retries: {config.max_retries} (otimizado)")
    print(f"✅ Log Format: {config.log_format} (estruturado)")
    print(f"✅ HTTP Logging: Desabilitado (performance)")
    print(f"✅ SSL Verification: {config.verify_ssl}")
    print()


def exemplo_configuracao_avancada():
    """Exemplo de configuração avançada e personalizada"""
    print("⚙️ CONFIGURAÇÃO AVANÇADA")
    print("=" * 50)
    
    # Configuração base
    client = Sicoob(
        client_id="advanced_client",
        environment="development"
    )
    
    # Personalizações específicas
    SicoobConfig.update_config(
        timeout=120,                                    # Timeout personalizado
        log_level="ERROR",                             # Logs mais restritivos
        custom_headers={                               # Headers customizados
            "X-API-Version": "v3",
            "X-Environment": "custom-dev",
            "X-Request-Source": "advanced-example"
        },
        verify_ssl=True                                # SSL sempre verificado
    )
    
    config = SicoobConfig.get_current_config()
    print(f"✅ Timeout Personalizado: {config.timeout}s")
    print(f"✅ Log Level: {config.log_level}")
    print(f"✅ Headers Customizados: {len(config.custom_headers)} definidos")
    
    # Verifica headers customizados
    headers = SicoobConfig.get_custom_headers()
    for key, value in headers.items():
        print(f"   - {key}: {value}")
    print()


def exemplo_configuracao_via_ambiente():
    """Exemplo de configuração via variáveis de ambiente"""
    print("🌐 CONFIGURAÇÃO VIA VARIÁVEIS DE AMBIENTE")
    print("=" * 50)
    
    # Simula configuração via .env
    os.environ.update({
        'SICOOB_ENVIRONMENT': 'staging',
        'SICOOB_BASE_URL': 'https://custom-api.sicoob.com.br',
        'SICOOB_TIMEOUT': '45',
        'SICOOB_LOG_LEVEL': 'DEBUG',
        'SICOOB_LOG_FORMAT': 'json',
        'SICOOB_LOG_REQUESTS': 'true',
        'SICOOB_VERIFY_SSL': 'true'
    })
    
    # Força recarregamento da configuração
    SicoobConfig._instance = None
    
    client = Sicoob(client_id="env_client")
    
    config = SicoobConfig.get_current_config()
    print(f"✅ Ambiente (via ENV): {config.environment.value}")
    print(f"✅ URL Customizada: {config.base_url}")
    print(f"✅ Timeout: {config.timeout}s")
    print(f"✅ Log Level: {config.log_level}")
    print(f"✅ Log Format: {config.log_format}")
    print(f"✅ HTTP Requests: {config.log_requests}")
    print()


def exemplo_migracao_sandbox_mode():
    """Exemplo de migração do sandbox_mode antigo"""
    print("🔄 MIGRAÇÃO DO SANDBOX_MODE")
    print("=" * 50)
    
    # ✅ AINDA FUNCIONA (compatibilidade)
    print("Método antigo (ainda funciona):")
    client_old = Sicoob(
        client_id="old_client",
        sandbox_mode=True
    )
    print(f"   sandbox_mode=True → environment={client_old.environment.value}")
    
    # ✅ RECOMENDADO (nova API)
    print("\nMétodo novo (recomendado):")
    client_new = Sicoob(
        client_id="new_client",
        environment="sandbox"
    )
    print(f"   environment='sandbox' → environment={client_new.environment.value}")
    print()


def exemplo_verificacao_ambiente():
    """Exemplo de verificação do ambiente atual"""
    print("🔍 VERIFICAÇÃO DE AMBIENTE")
    print("=" * 50)
    
    # Configura diferentes ambientes e testa
    ambientes = [
        Environment.DEVELOPMENT,
        Environment.TEST,
        Environment.STAGING,
        Environment.PRODUCTION,
        Environment.SANDBOX
    ]
    
    for env in ambientes:
        SicoobConfig.set_environment(env)
        
        print(f"Ambiente: {env.value}")
        print(f"   É Produção? {SicoobConfig.is_production()}")
        print(f"   É Sandbox? {SicoobConfig.is_sandbox()}")
        print(f"   Requer Certificado? {SicoobConfig.requires_certificate()}")
        print(f"   Debug Mode? {SicoobConfig.is_debug_mode()}")
        print(f"   Base URL: {SicoobConfig.get_base_url()}")
        print()


def exemplo_integracao_logging():
    """Exemplo de integração com sistema de logging"""
    print("📊 INTEGRAÇÃO COM LOGGING")
    print("=" * 50)
    
    from sicoob.logging_config import get_logger
    
    # Logging automático baseado no ambiente
    client_dev = Sicoob(
        client_id="logging_dev",
        environment="development"
    )
    
    logger = get_logger(__name__)
    logger.info(
        "Cliente configurado para desenvolvimento",
        extra={
            'environment': SicoobConfig.get_current_config().environment.value,
            'log_level': SicoobConfig.get_log_level(),
            'http_logging': SicoobConfig.should_log_requests()
        }
    )
    
    # Mudança de ambiente altera logging
    client_prod = Sicoob(
        client_id="logging_prod", 
        environment="production"
    )
    
    logger.info(
        "Cliente reconfigurado para produção",
        extra={
            'environment': SicoobConfig.get_current_config().environment.value,
            'log_level': SicoobConfig.get_log_level(),
            'http_logging': SicoobConfig.should_log_requests()
        }
    )
    
    print("✅ Logging configurado automaticamente por ambiente")
    print("✅ Desenvolvimento: DEBUG + HTTP logging")  
    print("✅ Produção: INFO + sem HTTP logging")
    print()


def exemplo_user_agent_dinamico():
    """Exemplo de User-Agent dinâmico por ambiente"""
    print("🔖 USER-AGENT DINÂMICO")
    print("=" * 50)
    
    from sicoob.api_client import APIClientBase
    from unittest.mock import Mock
    
    # Simula diferentes ambientes
    ambientes = ['development', 'staging', 'production']
    
    for env_name in ambientes:
        client = Sicoob(
            client_id=f"{env_name}_client",
            environment=env_name
        )
        
        # Simula obtenção de headers
        api_client = APIClientBase(Mock(), Mock(), False)
        headers = api_client._get_headers("test_scope")
        
        print(f"Ambiente {env_name}:")
        print(f"   User-Agent: {headers.get('User-Agent', 'N/A')}")
    
    print()


if __name__ == "__main__":
    """Executa todos os exemplos"""
    
    exemplos = [
        exemplo_desenvolvimento,
        exemplo_testes,
        exemplo_staging,
        exemplo_producao,
        exemplo_configuracao_avancada,
        exemplo_configuracao_via_ambiente,
        exemplo_migracao_sandbox_mode,
        exemplo_verificacao_ambiente,
        exemplo_integracao_logging,
        exemplo_user_agent_dinamico,
    ]
    
    for exemplo in exemplos:
        try:
            exemplo()
            print("-" * 70)
            print()
        except Exception as e:
            print(f"❌ Erro em {exemplo.__name__}: {e}")
            print()
    
    print("🎉 TODOS OS EXEMPLOS EXECUTADOS!")
    print("\n💡 Para usar em seu código:")
    print("   1. Configure SICOOB_ENVIRONMENT no .env")
    print("   2. Use environment='staging' no Sicoob()")
    print("   3. Aproveite configuração automática por ambiente")
    print("   4. Personalize conforme necessário com SicoobConfig.update_config()")