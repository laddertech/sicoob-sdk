"""Exemplos de configuração de logging para diferentes ambientes

Este arquivo demonstra como configurar o sistema de logging do Sicoob SDK
para diferentes cenários de uso: desenvolvimento, testes, produção, etc.
"""

import os
from sicoob import Sicoob
from sicoob.logging_config import SicoobLogger


def exemplo_desenvolvimento():
    """Configuração para ambiente de desenvolvimento

    - Logs verbosos (DEBUG)
    - Formato legível
    - Logs de requisições HTTP habilitados
    - Output no console
    """
    print('🔧 CONFIGURANDO LOGGING PARA DESENVOLVIMENTO')
    print('=' * 50)

    # Configuração manual
    SicoobLogger.configure(
        level='DEBUG',
        format_type='custom',
        log_requests=True,
        log_responses=True,
        force_reconfigure=True,
    )

    # Exemplo de uso
    sicoob = Sicoob(client_id='test-client', sandbox_mode=True)
    print('✅ Cliente configurado com logs DEBUG')
    print('✅ Todas as requisições HTTP serão logadas')
    print('✅ Formato legível para debugging')


def exemplo_producao():
    """Configuração para ambiente de produção

    - Logs essenciais (INFO/WARNING/ERROR)
    - Formato JSON estruturado
    - Arquivo de log rotativo
    - Dados sensíveis filtrados
    """
    print('🚀 CONFIGURANDO LOGGING PARA PRODUÇÃO')
    print('=' * 50)

    # Configuração via variáveis de ambiente (recomendado)
    os.environ.update(
        {
            'SICOOB_LOG_LEVEL': 'INFO',
            'SICOOB_LOG_FORMAT': 'json',
            'SICOOB_LOG_FILE': '/var/log/sicoob-sdk/sicoob.log',
            'SICOOB_LOG_REQUESTS': 'false',  # Desabilitado por performance
            'SICOOB_LOG_RESPONSES': 'false',
        }
    )

    # A configuração será aplicada automaticamente
    SicoobLogger.configure(force_reconfigure=True)

    sicoob = Sicoob(client_id='prod-client', sandbox_mode=False)
    print('✅ Cliente configurado com logs estruturados')
    print('✅ Logs salvos em arquivo rotativo')
    print('✅ Dados sensíveis automaticamente filtrados')


def exemplo_testes():
    """Configuração para ambiente de testes

    - Logs mínimos (WARNING/ERROR apenas)
    - Formato simples
    - Sem logging de HTTP para performance
    """
    print('🧪 CONFIGURANDO LOGGING PARA TESTES')
    print('=' * 50)

    SicoobLogger.configure(
        level='WARNING',
        format_type='simple',
        log_requests=False,
        log_responses=False,
        force_reconfigure=True,
    )

    sicoob = Sicoob(client_id='test-client', sandbox_mode=True)
    print('✅ Logs mínimos para testes rápidos')
    print('✅ Apenas warnings e erros são mostrados')


def exemplo_debug_integracao():
    """Configuração para debug de problemas de integração

    - Logs máximos (DEBUG)
    - Formato JSON para análise
    - Todos os HTTPs logados
    - Arquivo específico para análise
    """
    print('🔍 CONFIGURANDO LOGGING PARA DEBUG DE INTEGRAÇÃO')
    print('=' * 50)

    SicoobLogger.configure(
        level='DEBUG',
        format_type='json',
        log_file='debug_integracao.log',
        log_requests=True,
        log_responses=True,
        force_reconfigure=True,
    )

    # Exemplo de operação com logging detalhado
    sicoob = Sicoob(client_id='debug-client', sandbox_mode=True)

    try:
        # Estas operações terão logs detalhados
        cobranca = sicoob.cobranca.pix.criar_cobranca_imediata(
            'test-txid-123',
            {
                'calendario': {'expiracao': 3600},
                'valor': {'original': '100.00'},
                'chave': 'test@example.com',
            },
        )
        print(f'✅ Cobrança criada: {cobranca.get("status", "N/A")}')
    except Exception as e:
        print(f'❌ Erro capturado e logado: {e}')

    print("✅ Logs detalhados salvos em 'debug_integracao.log'")
    print('✅ Análise completa de requests/responses disponível')


def exemplo_monitoramento():
    """Configuração para monitoramento em produção

    - Logs estruturados para ferramentas de análise
    - Métricas de performance
    - Alertas configuráveis
    """
    print('📊 CONFIGURANDO LOGGING PARA MONITORAMENTO')
    print('=' * 50)

    # Configuração otimizada para ferramentas como ELK Stack
    SicoobLogger.configure(
        level='INFO',
        format_type='json',
        log_file='/var/log/sicoob-sdk/monitoring.log',
        log_requests=True,  # Para métricas de API
        log_responses=True,  # Para análise de performance
        force_reconfigure=True,
    )

    sicoob = Sicoob(client_id='monitoring-client', sandbox_mode=False)
    print('✅ Logs estruturados para Elasticsearch/Splunk')
    print('✅ Métricas de performance de APIs')
    print('✅ Campos padronizados para alertas')


def exemplo_configuracao_por_componente():
    """Exemplo de configuração granular por componente"""
    print('⚙️  CONFIGURAÇÃO GRANULAR POR COMPONENTE')
    print('=' * 50)

    # Configuração base
    SicoobLogger.configure(level='INFO', force_reconfigure=True)

    # Configuração específica por logger
    import logging

    # OAuth mais verboso para debug de autenticação
    logging.getLogger('sicoob.auth.oauth').setLevel(logging.DEBUG)

    # HTTP menos verboso para reduzir ruído
    logging.getLogger('sicoob.http').setLevel(logging.WARNING)

    # PIX com logging médio
    logging.getLogger('sicoob.pix').setLevel(logging.INFO)

    # Bibliotecas externas silenciosas
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    logging.getLogger('requests').setLevel(logging.ERROR)

    print('✅ OAuth: DEBUG (autenticação detalhada)')
    print('✅ HTTP: WARNING (menos verboso)')
    print('✅ PIX: INFO (operações importantes)')
    print('✅ Externos: ERROR (apenas erros críticos)')


def exemplo_integracao_aplicacao():
    """Exemplo de integração com logging da aplicação"""
    print('🔗 INTEGRAÇÃO COM LOGGING DA APLICAÇÃO')
    print('=' * 50)

    import logging

    # Configura logging da aplicação
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | APP | %(levelname)s | %(name)s | %(message)s',
    )

    # Logger da aplicação
    app_logger = logging.getLogger('minha_aplicacao')
    app_logger.info('Aplicação iniciada')

    # Configura SDK com mesmo nível
    SicoobLogger.configure(level='INFO', format_type='custom', force_reconfigure=True)

    # Uso integrado
    app_logger.info('Iniciando integração com Sicoob')
    sicoob = Sicoob(client_id='app-client', sandbox_mode=True)
    app_logger.info('Integração Sicoob configurada')

    print('✅ Logs da aplicação e SDK unificados')
    print('✅ Formato consistente entre componentes')


def exemplo_analise_performance():
    """Exemplo focado em análise de performance"""
    print('⚡ CONFIGURAÇÃO PARA ANÁLISE DE PERFORMANCE')
    print('=' * 50)

    SicoobLogger.configure(
        level='INFO',
        format_type='json',
        log_requests=True,
        log_responses=True,
        force_reconfigure=True,
    )

    # Os logs incluirão automaticamente:
    # - duration_ms: tempo de resposta
    # - status_code: código HTTP
    # - operation: tipo de operação
    # - request_id: ID único para correlação

    sicoob = Sicoob(client_id='perf-client', sandbox_mode=True)

    print('✅ Métricas de tempo de resposta automáticas')
    print('✅ Correlação de request/response via request_id')
    print('✅ Dados prontos para dashboards de performance')


if __name__ == '__main__':
    """Executa exemplos baseados na variável de ambiente"""

    ambiente = os.getenv('EXEMPLO_AMBIENTE', 'desenvolvimento')

    exemplos = {
        'desenvolvimento': exemplo_desenvolvimento,
        'producao': exemplo_producao,
        'testes': exemplo_testes,
        'debug': exemplo_debug_integracao,
        'monitoramento': exemplo_monitoramento,
        'componentes': exemplo_configuracao_por_componente,
        'integracao': exemplo_integracao_aplicacao,
        'performance': exemplo_analise_performance,
    }

    if ambiente in exemplos:
        exemplos[ambiente]()
    else:
        print(f'Ambientes disponíveis: {", ".join(exemplos.keys())}')
        print(f'Execute: EXEMPLO_AMBIENTE=producao python logging_examples.py')
