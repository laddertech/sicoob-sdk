# Sistema de Configuração por Ambiente - Sicoob SDK

O Sicoob SDK agora possui um sistema robusto de configuração por ambiente que substitui o sistema anterior baseado apenas em `sandbox_mode`.

## 🎯 Visão Geral

### ✅ **Antes** (Sistema Limitado)
```python
# Apenas 2 opções: sandbox ou produção
sicoob = Sicoob(client_id="...", sandbox_mode=True)  # sandbox
sicoob = Sicoob(client_id="...", sandbox_mode=False) # produção
```

### ✅ **Agora** (Sistema Flexível)
```python
# Múltiplos ambientes com configurações específicas
sicoob = Sicoob(client_id="...", environment="development")
sicoob = Sicoob(client_id="...", environment="test")  
sicoob = Sicoob(client_id="...", environment="staging")
sicoob = Sicoob(client_id="...", environment="production")
sicoob = Sicoob(client_id="...", environment="sandbox")

# Ou via variável de ambiente
os.environ['SICOOB_ENVIRONMENT'] = 'development'
sicoob = Sicoob(client_id="...")
```

## 🏗️ Ambientes Suportados

### 🔧 **Development** 
- **URL**: `https://sandbox.sicoob.com.br/sicoob/sandbox`
- **Certificado**: Não requerido
- **Logging**: DEBUG, formato custom, HTTP logging habilitado
- **Timeout**: 60 segundos
- **Debug Mode**: Habilitado

### 🧪 **Test**
- **URL**: `https://sandbox.sicoob.com.br/sicoob/sandbox`
- **Certificado**: Não requerido
- **Logging**: WARNING, formato simple, HTTP logging desabilitado
- **Timeout**: 30 segundos
- **Debug Mode**: Desabilitado

### 🚀 **Staging**
- **URL**: `https://api.sicoob.com.br`
- **Certificado**: Requerido
- **Logging**: INFO, formato JSON, HTTP logging habilitado
- **Timeout**: 30 segundos
- **Debug Mode**: Desabilitado

### 🏭 **Production**
- **URL**: `https://api.sicoob.com.br`
- **Certificado**: Requerido
- **Logging**: INFO, formato JSON, HTTP logging desabilitado
- **Timeout**: 30 segundos
- **Max Retries**: 5 (otimizado para produção)
- **Debug Mode**: Desabilitado

### 📦 **Sandbox**
- **URL**: `https://sandbox.sicoob.com.br/sicoob/sandbox`
- **Certificado**: Não requerido
- **Logging**: DEBUG, formato custom, HTTP logging habilitado
- **Timeout**: 45 segundos
- **Debug Mode**: Habilitado

## 📝 Configuração via Variáveis de Ambiente

### Arquivo `.env`
```bash
# === CONFIGURAÇÃO DE AMBIENTE ===
SICOOB_ENVIRONMENT=production

# === CREDENCIAIS ===
SICOOB_CLIENT_ID=seu_client_id
SICOOB_CERTIFICADO_PFX=caminho/para/certificado.pfx
SICOOB_SENHA_PFX=senha_do_certificado

# === CONFIGURAÇÕES AVANÇADAS (OPCIONAL) ===
# Sobrescrever URLs
SICOOB_BASE_URL=https://api.custom.com
SICOOB_AUTH_URL=https://auth.custom.com/token

# Configurações de rede
SICOOB_TIMEOUT=45
SICOOB_MAX_RETRIES=3

# Configurações de logging
SICOOB_LOG_LEVEL=DEBUG
SICOOB_LOG_FORMAT=json
SICOOB_LOG_REQUESTS=true
SICOOB_LOG_RESPONSES=true

# Configurações de segurança
SICOOB_DEBUG_MODE=false
SICOOB_VERIFY_SSL=true
```

## 💻 Exemplos de Uso

### Configuração por Código
```python
from sicoob import Sicoob
from sicoob.config import Environment

# === MÉTODO 1: Via parâmetro string ===
client = Sicoob(
    client_id="seu_client_id",
    environment="development"
)

# === MÉTODO 2: Via enum Environment ===
client = Sicoob(
    client_id="seu_client_id",
    environment=Environment.DEVELOPMENT
)

# === MÉTODO 3: Via variável de ambiente ===
import os
os.environ['SICOOB_ENVIRONMENT'] = 'development'
client = Sicoob(client_id="seu_client_id")
```

### Configuração Dinâmica
```python
from sicoob.config import SicoobConfig, Environment

# Alterar ambiente durante execução
SicoobConfig.set_environment(Environment.STAGING)

# Atualizar configurações específicas
SicoobConfig.update_config(
    timeout=120,
    log_level="ERROR",
    custom_headers={"X-API-Version": "v2"}
)

# Verificar configurações atuais
config = SicoobConfig.get_current_config()
print(f"Ambiente: {config.environment.value}")
print(f"URL Base: {config.base_url}")
print(f"Timeout: {config.timeout}")
```

### Uso em Diferentes Ambientes

#### 🔧 **Desenvolvimento Local**
```python
# Configuração otimizada para desenvolvimento
client = Sicoob(
    client_id="dev_client_id",
    environment="development"
)

# Logs verbosos, sem necessidade de certificado
# URLs de sandbox, timeout maior para debug
```

#### 🧪 **Testes Automatizados**
```python
# Configuração otimizada para testes
client = Sicoob(
    client_id="test_client_id",
    environment="test"
)

# Logs mínimos, execução rápida
# Sem HTTP logging para performance
```

#### 🚀 **Staging/Homologação**
```python
# Configuração similar à produção
client = Sicoob(
    client_id="staging_client_id",
    certificado_pfx="staging_cert.pfx",
    senha_pfx="staging_password",
    environment="staging"
)

# URLs de produção, certificado obrigatório
# HTTP logging habilitado para debug
```

#### 🏭 **Produção**
```python
# Configuração otimizada para produção
client = Sicoob(
    client_id="prod_client_id",
    certificado_pfx="prod_cert.pfx",
    senha_pfx="prod_password",
    environment="production"
)

# Máximo de retries, logs estruturados
# HTTP logging desabilitado para performance
```

## 🔧 API de Configuração

### Métodos Utilitários
```python
from sicoob.config import SicoobConfig

# Verificar ambiente atual
SicoobConfig.is_production()      # bool
SicoobConfig.is_sandbox()         # bool
SicoobConfig.requires_certificate()  # bool

# Obter configurações
SicoobConfig.get_base_url()       # str
SicoobConfig.get_auth_url()       # str
SicoobConfig.get_timeout()        # int
SicoobConfig.get_max_retries()    # int

# Configurações de logging
SicoobConfig.should_log_requests()   # bool
SicoobConfig.should_log_responses()  # bool
SicoobConfig.get_log_level()         # str
SicoobConfig.get_log_format()        # str

# Configurações de segurança
SicoobConfig.is_debug_mode()         # bool
SicoobConfig.should_verify_ssl()     # bool
SicoobConfig.get_custom_headers()    # Dict[str, str]
```

### Configuração Programática
```python
# Atualizar configurações
SicoobConfig.update_config(
    timeout=60,
    log_level="DEBUG",
    custom_headers={"X-Custom": "value"}
)

# Resetar para padrões do ambiente
SicoobConfig.reset_to_defaults()

# Alterar ambiente
SicoobConfig.set_environment(Environment.DEVELOPMENT)
```

## 🔄 Migração do Sistema Anterior

### Compatibilidade com `sandbox_mode`
```python
# ✅ AINDA FUNCIONA (compatibilidade)
sicoob = Sicoob(client_id="...", sandbox_mode=True)   # → environment=sandbox
sicoob = Sicoob(client_id="...", sandbox_mode=False)  # → environment=production

# ✅ RECOMENDADO (nova API)
sicoob = Sicoob(client_id="...", environment="sandbox")
sicoob = Sicoob(client_id="...", environment="production")
```

### Migração Passo a Passo
1. **Substitua `sandbox_mode=True`** por `environment="sandbox"`
2. **Substitua `sandbox_mode=False`** por `environment="production"` 
3. **Configure ambiente via `.env`** com `SICOOB_ENVIRONMENT=production`
4. **Aproveite novos ambientes** como `development`, `test`, `staging`

## 🎛️ Headers Customizados por Ambiente

```python
from sicoob.config import SicoobConfig

# Configurar headers específicos por ambiente
if SicoobConfig.is_production():
    SicoobConfig.update_config(
        custom_headers={
            "X-Environment": "production",
            "X-API-Version": "v3"
        }
    )
elif SicoobConfig.get_current_config().environment.value == "staging":
    SicoobConfig.update_config(
        custom_headers={
            "X-Environment": "staging",
            "X-Debug-Mode": "true"
        }
    )
```

## ⚡ User-Agent Dinâmico

O SDK agora inclui o ambiente no User-Agent:
```
SicoobAPIClient/1.0 (production)
SicoobAPIClient/1.0 (development)  
SicoobAPIClient/1.0 (staging)
```

## 🔍 Debug e Monitoramento

### Verificar Configuração Atual
```python
from sicoob.config import SicoobConfig

config = SicoobConfig.get_current_config()
print(f"""
Configuração Atual:
- Ambiente: {config.environment.value}
- URL Base: {config.base_url}
- Requer Certificado: {config.require_certificate}
- Log Level: {config.log_level}
- Timeout: {config.timeout}s
- Debug Mode: {config.debug_mode}
""")
```

### Logs de Configuração
```python
import logging
from sicoob.logging_config import get_logger

logger = get_logger(__name__)
logger.info("Configuração carregada", extra={
    'environment': config.environment.value,
    'base_url': config.base_url,
    'timeout': config.timeout
})
```

## 🏆 Melhores Práticas

### ✅ **Recomendações**
1. **Use variáveis de ambiente** em produção: `SICOOB_ENVIRONMENT=production`
2. **Configure por ambiente**: desenvolvimento → test → staging → produção
3. **Aproveite configurações automáticas**: cada ambiente já vem otimizado
4. **Use logging estruturado** em produção: formato JSON
5. **Monitore configurações** via logs de inicialização

### ❌ **Evite**
1. **Hardcoding ambientes** no código fonte
2. **Usar development** em produção
3. **Desabilitar SSL** em produção (`SICOOB_VERIFY_SSL=false`)
4. **Logs DEBUG** em produção sem necessidade
5. **Timeouts muito altos** em produção

## 🧪 Testes com Diferentes Ambientes

```python
import pytest
from sicoob import Sicoob
from sicoob.config import Environment, SicoobConfig

def test_development_environment():
    """Testa configuração de desenvolvimento"""
    client = Sicoob(
        client_id="test_client",
        environment="development"
    )
    
    assert SicoobConfig.is_sandbox() is True
    assert SicoobConfig.get_log_level() == "DEBUG"
    assert SicoobConfig.requires_certificate() is False

def test_production_environment():
    """Testa configuração de produção"""
    client = Sicoob(
        client_id="test_client",
        environment="production"
    )
    
    assert SicoobConfig.is_production() is True
    assert SicoobConfig.requires_certificate() is True
    assert SicoobConfig.get_max_retries() == 5
```

## 📚 Referência Completa

### Enum `Environment`
```python
Environment.DEVELOPMENT  # "development"
Environment.TEST         # "test"
Environment.STAGING      # "staging"  
Environment.PRODUCTION   # "production"
Environment.SANDBOX      # "sandbox"
```

### Classe `EnvironmentConfig`
```python
@dataclass
class EnvironmentConfig:
    environment: Environment = Environment.PRODUCTION
    base_url: str = "https://api.sicoob.com.br"
    auth_url: str = "https://auth.sicoob.com.br/..."
    timeout: int = 30
    max_retries: int = 3
    retry_backoff_factor: float = 1.0
    log_level: str = "INFO"
    log_format: str = "custom"
    log_requests: bool = False
    log_responses: bool = False
    require_certificate: bool = True
    debug_mode: bool = False
    verify_ssl: bool = True
    custom_headers: Dict[str, str] = field(default_factory=dict)
```

### Variáveis de Ambiente Suportadas
```bash
SICOOB_ENVIRONMENT      # development, test, staging, production, sandbox
SICOOB_BASE_URL         # URL base customizada
SICOOB_AUTH_URL         # URL de autenticação customizada
SICOOB_TIMEOUT          # Timeout em segundos
SICOOB_MAX_RETRIES      # Número máximo de tentativas
SICOOB_LOG_LEVEL        # DEBUG, INFO, WARNING, ERROR, CRITICAL
SICOOB_LOG_FORMAT       # custom, json, simple
SICOOB_LOG_REQUESTS     # true, false
SICOOB_LOG_RESPONSES    # true, false
SICOOB_DEBUG_MODE       # true, false
SICOOB_VERIFY_SSL       # true, false
```

## 🔗 Integração com Logging

O sistema de configuração está totalmente integrado com o [sistema de logging](LOGGING.md):

```python
from sicoob import Sicoob

# Logging configurado automaticamente baseado no ambiente
client = Sicoob(client_id="...", environment="development")
# → Log level: DEBUG, formato: custom, HTTP logging: habilitado

client = Sicoob(client_id="...", environment="production") 
# → Log level: INFO, formato: json, HTTP logging: desabilitado
```

---

## 🆘 Suporte

Para dúvidas sobre configuração:
1. **Verifique as variáveis de ambiente** definidas
2. **Use `SicoobConfig.get_current_config()`** para debug
3. **Consulte logs de inicialização** para configuração aplicada
4. **Teste diferentes ambientes** para encontrar o ideal
