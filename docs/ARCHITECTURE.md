# Arquitetura do Sicoob SDK

## Visão Geral

O **Sicoob SDK** é uma biblioteca Python para integração com as APIs do Banco Sicoob, seguindo uma arquitetura modular com separação clara de responsabilidades.

## Separação de Responsabilidades

### 1. PIX (pypix-api)
- **Biblioteca**: `pypix-api` (dependência externa)
- **Responsabilidade**: Implementação completa do padrão PIX do BACEN
- **Escopo**: Genérico, reutilizável por qualquer banco
- **Mantida por**: Mesma empresa, mas como projeto independente

### 2. Sicoob SDK
- **Biblioteca**: `sicoob-sdk` (este projeto)
- **Responsabilidade**: Funcionalidades específicas do Banco Sicoob
- **Escopo**: 
  - Boletos bancários (específico Sicoob)
  - Conta corrente (específico Sicoob)
  - Autenticação OAuth2 (específico Sicoob)
  - Wrapper PIX (integração com pypix-api)

## Arquitetura de Componentes

```
sicoob-sdk/
│
├── sicoob/
│   ├── client.py           # Cliente principal do SDK
│   ├── auth/
│   │   └── oauth.py        # Autenticação OAuth2 específica Sicoob
│   ├── boleto.py          # API de Boletos (específico Sicoob)
│   ├── conta_corrente.py  # API Conta Corrente (específico Sicoob)
│   ├── pix.py            # Thin wrapper sobre pypix-api
│   └── cobranca.py       # Agregador de Boleto + PIX
│
└── pypix-api (dependência)
    └── Implementação completa PIX BACEN
```

## Design Patterns Utilizados

### 1. Facade Pattern (pix.py)
```python
class PixAPI:
    """Facade para simplificar acesso à pypix-api"""
    
    def __init__(self, oauth_client, session, sandbox_mode):
        self._pix_api = SicoobPixAPI(...)
    
    def __getattr__(self, name):
        # Proxy transparente para pypix-api
        return getattr(self._pix_api, name)
```

### 2. Adapter Pattern (SicoobPixAPICustom)
```python
class SicoobPixAPICustom(SicoobPixAPI):
    """Adapta erros genéricos para domínio Sicoob"""
    
    def _handle_error_response(self, response):
        # Mapeia erros HTTP para exceções específicas
        if status == 404:
            raise CobrancaPixNaoEncontradaError(...)
```

### 3. Aggregator Pattern (CobrancaAPI)
```python
class CobrancaAPI:
    """Agrega serviços de cobrança em interface única"""
    
    def __init__(self):
        self.boleto = BoletoAPI(...)
        self.pix = PixAPI(...)
```

## Fluxo de Dados

### Operação PIX
```
Usuario → Sicoob.cobranca.pix → PixAPI → pypix-api → API Sicoob
                                    ↓
                            Tratamento de erros
                                    ↓
                            Exceções do domínio
```

### Operação Boleto
```
Usuario → Sicoob.cobranca.boleto → BoletoAPI → API Sicoob
                                        ↓
                                Tratamento interno
```

## Vantagens da Arquitetura

### 1. Manutenibilidade
- **PIX genérico**: Atualizações do padrão BACEN em um só lugar
- **Sicoob específico**: Mudanças isoladas não afetam PIX

### 2. Reutilização
- **pypix-api**: Pode ser usada por outros bancos
- **Padrões**: Mesma estrutura pode ser aplicada a outros bancos

### 3. Testabilidade
- **Mocks isolados**: Testes unitários por componente
- **Integração controlada**: Wrapper permite interceptar chamadas

### 4. Escalabilidade
- **Novos bancos**: Criam apenas suas especificidades
- **Novas funcionalidades PIX**: Automaticamente disponíveis

## Decisões de Design

### Por que um Thin Wrapper?

1. **Evita duplicação**: Não reimplementa o que pypix-api já faz
2. **Proxy transparente**: Novos métodos automaticamente disponíveis
3. **Tratamento centralizado**: Erros convertidos uma vez só
4. **Interface consistente**: Mantém padrões do SDK Sicoob

### Por que separar PIX do SDK?

1. **Padrão BACEN**: PIX é igual para todos os bancos
2. **Evolução independente**: PIX evolui sem breaking changes no SDK
3. **Especialização**: Cada biblioteca foca em sua expertise

## Exemplo de Uso

```python
from sicoob import Sicoob

# Cliente unificado
sicoob = Sicoob(
    client_id="...",
    certificado="...",
    chave_privada="..."
)

# PIX via pypix-api
pix = sicoob.cobranca.pix.criar_cob(txid, dados)

# Boleto específico Sicoob
boleto = sicoob.cobranca.boleto.emitir_boleto(dados)

# Conta corrente específica Sicoob
saldo = sicoob.conta_corrente.saldo()
```

## Roadmap

### Curto Prazo
- ✅ Integração pypix-api como thin wrapper
- ✅ Documentação da arquitetura
- 🔄 Exemplos de uso completos

### Médio Prazo
- 📋 Suporte a novos endpoints do Sicoob
- 📋 Cache inteligente de consultas
- 📋 Retry automático com backoff

### Longo Prazo
- 📋 SDK assíncrono (asyncio)
- 📋 Suporte a webhooks nativos
- 📋 Métricas e observabilidade

## Contribuindo

Para adicionar novas funcionalidades:

1. **PIX**: Contribua no [pypix-api](https://github.com/laddertech/pypix-api)
2. **Sicoob específico**: Contribua neste repositório
3. **Testes**: Sempre adicione testes unitários e de integração