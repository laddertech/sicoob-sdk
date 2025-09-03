# Sistema de Logging do Sicoob SDK

O Sicoob SDK inclui um sistema robusto de logging configurável para facilitar o troubleshooting e monitoramento de integrações.

## 🎯 Funcionalidades

### ✅ **Configuração Flexível**
- Múltiplos níveis de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Formatos personalizáveis (custom, JSON, simple)
- Saída para console e/ou arquivo
- Configuração via variáveis de ambiente ou código

### ✅ **Segurança**
- Filtragem automática de dados sensíveis
- Mascaramento de tokens, senhas e certificados
- Logs estruturados para auditoria

### ✅ **Performance**
- Logging assíncrono de HTTP (opcional)
- Rotação automática de arquivos
- Configuração granular por componente

### ✅ **Troubleshooting**
- Correlação de requests via request_id
- Métricas de tempo de resposta
- Stack traces detalhados para erros

## 🚀 Configuração Rápida

### Via Variáveis de Ambiente (Recomendado)
```bash
# Configuração básica
export SICOOB_LOG_LEVEL=INFO
export SICOOB_LOG_FORMAT=json
export SICOOB_LOG_FILE=/var/log/sicoob-sdk/app.log

# Logging HTTP (para debug)
export SICOOB_LOG_REQUESTS=true
export SICOOB_LOG_RESPONSES=true
```

### Via Código
```python
from sicoob.logging_config import SicoobLogger

# Configuração personalizada
SicoobLogger.configure(
    level='DEBUG',
    format_type='json',
    log_file='sicoob-debug.log',
    log_requests=True,
    log_responses=True
)
```

### Uso Básico
```python
from sicoob import Sicoob
from sicoob.logging_config import get_logger

# Logger personalizado
logger = get_logger(__name__)
logger.info("Iniciando integração Sicoob")

# Cliente com logging automático
sicoob = Sicoob(client_id='...', sandbox_mode=True)
```

## 📋 Configurações por Ambiente

### 🔧 Desenvolvimento
```python
SicoobLogger.configure(
    level='DEBUG',
    format_type='custom',
    log_requests=True,
    log_responses=True
)
```

### 🚀 Produção
```bash
export SICOOB_LOG_LEVEL=INFO
export SICOOB_LOG_FORMAT=json
export SICOOB_LOG_FILE=/var/log/sicoob-sdk/production.log
export SICOOB_LOG_REQUESTS=false  # Performance
export SICOOB_LOG_RESPONSES=false
```

### 🧪 Testes
```python
SicoobLogger.configure(
    level='WARNING',
    format_type='simple',
    log_requests=False,
    log_responses=False
)
```

### 🔍 Debug de Integração
```python
SicoobLogger.configure(
    level='DEBUG',
    format_type='json',
    log_file='debug-integracao.log',
    log_requests=True,
    log_responses=True
)
```

## 📊 Formatos de Log

### Custom (Desenvolvimento)
```
2024-01-15 10:30:45 | INFO     | sicoob.client | __init__:52 | Cliente Sicoob inicializado com sucesso
2024-01-15 10:30:46 | DEBUG    | sicoob.auth.oauth | get_access_token:92 | Token válido encontrado no cache
```

### JSON (Produção)
```json
{
  "timestamp": "2024-01-15 10:30:45",
  "level": "INFO",
  "logger": "sicoob.client",
  "message": "Cliente Sicoob inicializado com sucesso",
  "module": "client",
  "function": "__init__",
  "line": 52,
  "operation": "client_init_complete"
}
```

### Simple (Testes)
```
INFO: Cliente Sicoob inicializado com sucesso
WARNING: Token expirado, renovando...
ERROR: Falha na requisição HTTP
```

## 🔒 Segurança e Dados Sensíveis

O sistema automaticamente filtra dados sensíveis:

```python
# ❌ Antes (dados expostos)
logger.info('Auth data: {"password": "secret123", "token": "abc456"}')

# ✅ Depois (dados mascarados)  
# Auth data: {"password": "***", "token": "***"}
```

### Campos Sensíveis Protegidos
- `password`, `senha`
- `token`, `access_token`, `refresh_token`
- `authorization`, `bearer`
- `certificate`, `certificado`
- `private_key`, `chave_privada`
- `client_secret`
- `cpf`, `cnpj`

## 🌐 Logging HTTP

### Habilitando Logging HTTP
```python
SicoobLogger.configure(
    log_requests=True,
    log_responses=True
)
```

### Exemplo de Request Log
```json
{
  "timestamp": "2024-01-15 10:30:46",
  "level": "INFO",
  "logger": "sicoob.http",
  "message": "HTTP Request: POST https://api.sicoob.com.br/pix/api/v2/cob/test123",
  "operation": "http_request",
  "request_id": "req_a1b2c3d4",
  "method": "POST",
  "url": "https://api.sicoob.com.br/pix/api/v2/cob/test123",
  "headers": {
    "Authorization": "***",
    "Content-Type": "application/json"
  }
}
```

### Exemplo de Response Log
```json
{
  "timestamp": "2024-01-15 10:30:46",
  "level": "INFO", 
  "logger": "sicoob.http",
  "message": "HTTP Response: 201 from https://api.sicoob.com.br/pix/api/v2/cob/test123 (245.67ms)",
  "operation": "http_response",
  "request_id": "req_a1b2c3d4",
  "status_code": 201,
  "duration_ms": 245.67
}
```

## 📁 Gestão de Arquivos

### Rotação Automática
```python
SicoobLogger.configure(
    log_file='/var/log/sicoob-sdk/app.log'
    # Rotação automática:
    # - Máximo: 10MB por arquivo
    # - Backup: 5 arquivos
    # - Compressão automática
)
```

### Estrutura de Arquivos
```
/var/log/sicoob-sdk/
├── app.log          # Arquivo atual
├── app.log.1        # Backup mais recente
├── app.log.2        # Backup anterior
├── app.log.3        # ...
├── app.log.4        # ...
└── app.log.5        # Backup mais antigo
```

## 🔧 Configuração Granular

### Por Componente
```python
import logging

# Configuração específica por módulo
logging.getLogger('sicoob.auth.oauth').setLevel(logging.DEBUG)
logging.getLogger('sicoob.http').setLevel(logging.WARNING)
logging.getLogger('sicoob.pix').setLevel(logging.INFO)

# Bibliotecas externas
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)
logging.getLogger('pypix_api').setLevel(logging.INFO)
```

### Campos Extras Personalizados
```python
logger = get_logger(__name__)

logger.info(
    "Operação concluída",
    extra={
        'operation': 'create_pix_charge',
        'user_id': 'user123',
        'amount': 150.00,
        'duration_ms': 234,
        'status_code': 201
    }
)
```

## 📊 Monitoramento e Métricas

### Integração com ELK Stack
```bash
# Configuração otimizada para Elasticsearch
export SICOOB_LOG_FORMAT=json
export SICOOB_LOG_FILE=/var/log/sicoob-sdk/elasticsearch.log
export SICOOB_LOG_REQUESTS=true
export SICOOB_LOG_RESPONSES=true
```

### Queries Úteis (Elasticsearch)
```json
// Erros nas últimas 24h
{
  "query": {
    "bool": {
      "must": [
        {"term": {"level": "ERROR"}},
        {"range": {"@timestamp": {"gte": "now-24h"}}}
      ]
    }
  }
}

// Performance por operação
{
  "aggs": {
    "operations": {
      "terms": {"field": "operation"},
      "aggs": {
        "avg_duration": {"avg": {"field": "duration_ms"}}
      }
    }
  }
}
```

### Alertas Sugeridos
```yaml
# Alertmanager / Grafana
- alert: SicoobSDKHighErrorRate
  expr: rate(sicoob_errors_total[5m]) > 0.1
  
- alert: SicoobSDKSlowResponse  
  expr: sicoob_response_time_p95 > 5000

- alert: SicoobSDKTokenFailure
  expr: increase(sicoob_token_errors[1h]) > 5
```

## 🛠️ Troubleshooting

### Problemas Comuns

#### 1. **Logs Não Aparecem**
```python
# Verifique o nível de log
logger = get_logger('sicoob.test')
logger.setLevel(logging.DEBUG)
logger.debug("Mensagem de teste")
```

#### 2. **Arquivo de Log Não Criado**
```python
# Verifique permissões do diretório
import os
log_dir = '/var/log/sicoob-sdk'
os.makedirs(log_dir, exist_ok=True)
```

#### 3. **Logs HTTP Não Aparecem**
```python
# Verifique configuração
SicoobLogger.configure(
    log_requests=True,
    log_responses=True,
    force_reconfigure=True  # Força reconfiguração
)
```

#### 4. **Performance Impactada**
```python
# Configure logging menos verboso
SicoobLogger.configure(
    level='WARNING',      # Apenas warnings e erros
    log_requests=False,   # Desabilita HTTP logging
    log_responses=False
)
```

### Debug de Integrações

#### Ativando Logs Máximos
```bash
export SICOOB_LOG_LEVEL=DEBUG
export SICOOB_LOG_FORMAT=json
export SICOOB_LOG_FILE=debug.log
export SICOOB_LOG_REQUESTS=true
export SICOOB_LOG_RESPONSES=true
```

#### Analisando Requests Específicos
```python
# Use request_id para correlacionar logs
# Request: req_a1b2c3d4 -> Response: req_a1b2c3d4

# Grep por request_id específico
# tail -f debug.log | grep "req_a1b2c3d4"
```

## 🔗 Integração com Aplicações

### Django
```python
# settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'sicoob': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'sicoob': {
            'handlers': ['sicoob'],
            'level': 'INFO',
        },
    },
}

# Configure Sicoob SDK
from sicoob.logging_config import SicoobLogger
SicoobLogger.configure(level='INFO', format_type='custom')
```

### Flask
```python
from flask import Flask
from sicoob.logging_config import SicoobLogger

app = Flask(__name__)

# Configura logging antes das rotas
SicoobLogger.configure(
    level='INFO',
    format_type='json' if app.config.get('ENV') == 'production' else 'custom'
)
```

### FastAPI
```python
from fastapi import FastAPI
from sicoob.logging_config import SicoobLogger
import logging

app = FastAPI()

# Configura logging
SicoobLogger.configure(level='INFO')

# Middleware de logging
@app.middleware("http")
async def log_requests(request, call_next):
    logger = logging.getLogger("app")
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    return response
```

## 📚 Referência da API

### SicoobLogger
```python
class SicoobLogger:
    @classmethod
    def configure(
        level: str = 'INFO',           # DEBUG, INFO, WARNING, ERROR, CRITICAL
        format_type: str = 'custom',   # custom, json, simple  
        log_file: str = None,          # Caminho para arquivo
        log_requests: bool = False,    # Log requisições HTTP
        log_responses: bool = False,   # Log respostas HTTP
        force_reconfigure: bool = False # Força reconfiguração
    ) -> None
    
    @classmethod
    def get_logger(name: str) -> logging.Logger
    
    @classmethod
    def log_http_request(method, url, headers, body, request_id) -> None
    
    @classmethod  
    def log_http_response(status_code, url, duration_ms, response_body, request_id) -> None
```

### Função de Conveniência
```python
def get_logger(name: str) -> logging.Logger:
    """Obtém logger configurado"""
    return SicoobLogger.get_logger(name)
```

### Variáveis de Ambiente
```bash
SICOOB_LOG_LEVEL      # DEBUG, INFO, WARNING, ERROR, CRITICAL
SICOOB_LOG_FORMAT     # custom, json, simple
SICOOB_LOG_FILE       # /path/to/logfile.log
SICOOB_LOG_REQUESTS   # true, false
SICOOB_LOG_RESPONSES  # true, false
```

## 💡 Melhores Práticas

### ✅ **Do**
- Use `get_logger(__name__)` em cada módulo
- Configure uma vez no início da aplicação
- Use formato JSON em produção
- Filtre logs por nível conforme ambiente
- Monitore logs de erro ativamente
- Use `extra` para campos estruturados

### ❌ **Don't**
- Não logue dados sensíveis manualmente
- Não use nível DEBUG em produção
- Não ignore erros de configuração de logs
- Não misture formatos de log na mesma aplicação

### 🎯 **Recomendações**
1. **Desenvolvimento**: DEBUG + custom format + HTTP logging
2. **Testes**: WARNING + simple format + sem HTTP logging  
3. **Produção**: INFO + JSON format + arquivo rotativo
4. **Debug**: DEBUG + JSON format + arquivo + HTTP logging completo

## 🆘 Suporte

Para problemas relacionados ao sistema de logging:

1. **Verifique a configuração**: Use `force_reconfigure=True`
2. **Teste isoladamente**: Configure apenas um logger por vez
3. **Verifique permissões**: Para arquivos de log
4. **Use request_id**: Para correlacionar requests/responses
5. **Monitore performance**: Logging verbose impacta performance

Exemplos completos disponíveis em: `docs/logging/logging_examples.py`