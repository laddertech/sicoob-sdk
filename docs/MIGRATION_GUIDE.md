# Guia de Migração: Sync para Async

Este guia fornece instruções detalhadas para migrar código síncrono do Sicoob SDK para a versão assíncrona, maximizando performance em operações em lote.

## Índice

- [Por que migrar para Async?](#por-que-migrar-para-async)
- [Principais Diferenças](#principais-diferenças)
- [Migração Passo a Passo](#migração-passo-a-passo)
- [Exemplos de Migração](#exemplos-de-migração)
- [Tabela de Equivalências](#tabela-de-equivalências)
- [Boas Práticas](#boas-práticas)
- [Troubleshooting](#troubleshooting)

## Por que migrar para Async?

### Vantagens do Código Assíncrono

1. **Performance em Lote**: Processe centenas de boletos simultaneamente
2. **Eficiência de I/O**: Não bloqueie enquanto aguarda respostas da API
3. **Escalabilidade**: Melhor utilização de recursos do sistema
4. **Throughput**: Até 10x mais rápido em operações em massa

### Quando usar cada versão?

| Cenário | Versão Recomendada |
|---------|-------------------|
| Scripts simples, poucos boletos | **Sync** |
| Operações em lote (>10 boletos) | **Async** |
| Integração com frameworks async (FastAPI, aiohttp) | **Async** |
| Aplicações legadas síncronas | **Sync** |
| Alta concorrência necessária | **Async** |

## Principais Diferenças

### 1. Imports

```python
# Sync
from sicoob import Sicoob

# Async
from sicoob.async_client import AsyncSicoob
import asyncio
```

### 2. Instanciação

```python
# Sync - Context manager direto
with Sicoob(client_id=client_id, ...) as client:
    resultado = client.cobranca.boleto.emitir_boleto(dados)

# Async - Requer async with
async with AsyncSicoob(client_id=client_id, ...) as client:
    resultado = await client.cobranca.boleto.emitir_boleto(dados)
```

### 3. Chamadas de Métodos

```python
# Sync
resultado = client.cobranca.boleto.emitir_boleto(dados)
boleto = client.cobranca.boleto.consultar_boleto(nosso_numero)

# Async - Adicionar await
resultado = await client.cobranca.boleto.emitir_boleto(dados)
boleto = await client.cobranca.boleto.consultar_boleto(nosso_numero)
```

### 4. Funções Container

```python
# Sync
def processar_boletos():
    with Sicoob(...) as client:
        return client.cobranca.boleto.emitir_boleto(dados)

# Async
async def processar_boletos():
    async with AsyncSicoob(...) as client:
        return await client.cobranca.boleto.emitir_boleto(dados)
```

### 5. Execução

```python
# Sync - Execução direta
resultado = processar_boletos()

# Async - Usar asyncio.run()
resultado = asyncio.run(processar_boletos())
```

## Migração Passo a Passo

### Passo 1: Adaptar Imports

```python
# Antes
from sicoob import Sicoob

# Depois
from sicoob.async_client import AsyncSicoob
import asyncio
```

### Passo 2: Converter Função para Async

```python
# Antes
def emitir_boleto_exemplo():
    with Sicoob(client_id=client_id) as client:
        resultado = client.cobranca.boleto.emitir_boleto(dados)
        return resultado

# Depois
async def emitir_boleto_exemplo():
    async with AsyncSicoob(client_id=client_id) as client:
        resultado = await client.cobranca.boleto.emitir_boleto(dados)
        return resultado
```

### Passo 3: Adicionar await nas Chamadas

Adicione `await` antes de **todas** as chamadas à API:

```python
# Antes
boleto = client.cobranca.boleto.emitir_boleto(dados)
consulta = client.cobranca.boleto.consultar_boleto(nosso_numero)
lista = client.cobranca.boleto.listar_boletos()

# Depois
boleto = await client.cobranca.boleto.emitir_boleto(dados)
consulta = await client.cobranca.boleto.consultar_boleto(nosso_numero)
lista = await client.cobranca.boleto.listar_boletos()
```

### Passo 4: Adaptar Execução Principal

```python
# Antes
if __name__ == '__main__':
    resultado = emitir_boleto_exemplo()
    print(resultado)

# Depois
if __name__ == '__main__':
    resultado = asyncio.run(emitir_boleto_exemplo())
    print(resultado)
```

### Passo 5: Aproveitar Concorrência (Opcional mas Recomendado)

Se você processa múltiplos boletos, aproveite para paralelizar:

```python
# Antes - Sequencial (lento)
resultados = []
with Sicoob(client_id=client_id) as client:
    for dados in lista_dados:
        resultado = client.cobranca.boleto.emitir_boleto(dados)
        resultados.append(resultado)

# Depois - Paralelo (rápido)
async with AsyncSicoob(client_id=client_id) as client:
    tasks = [
        client.cobranca.boleto.emitir_boleto(dados)
        for dados in lista_dados
    ]
    resultados = await asyncio.gather(*tasks)
```

## Exemplos de Migração

### Exemplo 1: Emissão Simples

#### Versão Sync (Antes)

```python
import os
from datetime import datetime, timedelta
from sicoob import Sicoob

def emitir_boleto_simples():
    client_id = os.getenv('SICOOB_CLIENT_ID')
    certificado = os.getenv('SICOOB_CERT_PFX')
    senha = os.getenv('SICOOB_SENHA_PFX')

    dados = {
        'numeroCliente': 123456,
        'dataEmissao': datetime.now().strftime('%Y-%m-%d'),
        'dataVencimento': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
        'valor': 150.00,
        'seuNumero': 'MENSALIDADE-2024-001',
        'pagador': {
            'numeroCpfCnpj': '12345678901',
            'nome': 'João Silva',
            'endereco': 'Rua Exemplo, 123',
            'bairro': 'Centro',
            'cidade': 'São Paulo',
            'cep': '01001000',
            'uf': 'SP',
        },
    }

    with Sicoob(
        client_id=client_id,
        certificado_pfx=certificado,
        senha_pfx=senha,
    ) as client:
        resultado = client.cobranca.boleto.emitir_boleto(dados)
        print(f"Boleto emitido: {resultado['resultado']['nossoNumero']}")
        return resultado

if __name__ == '__main__':
    emitir_boleto_simples()
```

#### Versão Async (Depois)

```python
import os
import asyncio
from datetime import datetime, timedelta
from sicoob.async_client import AsyncSicoob

async def emitir_boleto_simples():
    client_id = os.getenv('SICOOB_CLIENT_ID')
    certificado = os.getenv('SICOOB_CERT_PFX')
    senha = os.getenv('SICOOB_SENHA_PFX')

    dados = {
        'numeroCliente': 123456,
        'dataEmissao': datetime.now().strftime('%Y-%m-%d'),
        'dataVencimento': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
        'valor': 150.00,
        'seuNumero': 'MENSALIDADE-2024-001',
        'pagador': {
            'numeroCpfCnpj': '12345678901',
            'nome': 'João Silva',
            'endereco': 'Rua Exemplo, 123',
            'bairro': 'Centro',
            'cidade': 'São Paulo',
            'cep': '01001000',
            'uf': 'SP',
        },
    }

    async with AsyncSicoob(
        client_id=client_id,
        certificado_pfx=certificado,
        senha_pfx=senha,
    ) as client:
        resultado = await client.cobranca.boleto.emitir_boleto(dados)
        print(f"Boleto emitido: {resultado['resultado']['nossoNumero']}")
        return resultado

if __name__ == '__main__':
    asyncio.run(emitir_boleto_simples())
```

**Mudanças aplicadas:**
1. ✅ Import de `AsyncSicoob` e `asyncio`
2. ✅ Função convertida para `async def`
3. ✅ `with` → `async with`
4. ✅ Adicionado `await` na chamada
5. ✅ Execução com `asyncio.run()`

### Exemplo 2: Processamento em Lote

#### Versão Sync (Antes)

```python
from sicoob import Sicoob

def emitir_lote_sync():
    lista_dados = [
        {'valor': 100.00, 'seuNumero': f'BOL-{i:03d}', ...}
        for i in range(1, 51)
    ]

    resultados = []
    with Sicoob(client_id=client_id, ...) as client:
        for dados in lista_dados:
            try:
                resultado = client.cobranca.boleto.emitir_boleto(dados)
                resultados.append(resultado)
                print(f"✅ Boleto {dados['seuNumero']} emitido")
            except Exception as e:
                print(f"❌ Erro em {dados['seuNumero']}: {e}")

    return resultados

# Tempo estimado: 50 boletos × ~500ms = ~25 segundos
```

#### Versão Async (Depois)

```python
import asyncio
from asyncio import Semaphore
from sicoob.async_client import AsyncSicoob

async def emitir_lote_async():
    lista_dados = [
        {'valor': 100.00, 'seuNumero': f'BOL-{i:03d}', ...}
        for i in range(1, 51)
    ]

    async with AsyncSicoob(
        client_id=client_id,
        max_concurrent_requests=5,  # Rate limiting
    ) as client:
        limiter = Semaphore(5)
        delay_entre_requests = 1 / 4.5  # ~220ms para respeitar API

        async def emitir_com_rate_limit(dados):
            async with limiter:
                await asyncio.sleep(delay_entre_requests)
                try:
                    resultado = await client.cobranca.boleto.emitir_boleto(dados)
                    print(f"✅ Boleto {dados['seuNumero']} emitido")
                    return {'status': 'sucesso', 'dados': resultado}
                except Exception as e:
                    print(f"❌ Erro em {dados['seuNumero']}: {e}")
                    return {'status': 'erro', 'erro': str(e)}

        # Processa todos em paralelo
        tasks = [emitir_com_rate_limit(dados) for dados in lista_dados]
        resultados = await asyncio.gather(*tasks, return_exceptions=True)

    return resultados

# Tempo estimado: ~11 segundos (5 concorrentes × ~220ms)
# Performance: ~2.3x mais rápido!
```

**Ganho de Performance:**
- Sync: ~25 segundos
- Async: ~11 segundos
- **Speedup: 2.3x**

### Exemplo 3: Consulta com Retry

#### Versão Sync (Antes)

```python
import time
from sicoob import Sicoob
from sicoob.exceptions import BoletoNaoEncontradoError

def consultar_com_retry_sync(nosso_numero, max_tentativas=3):
    with Sicoob(client_id=client_id, ...) as client:
        for tentativa in range(max_tentativas):
            try:
                boleto = client.cobranca.boleto.consultar_boleto(nosso_numero)
                return boleto
            except BoletoNaoEncontradoError:
                if tentativa < max_tentativas - 1:
                    time.sleep(2 ** tentativa)  # Backoff exponencial
                else:
                    raise
```

#### Versão Async (Depois)

```python
import asyncio
from sicoob.async_client import AsyncSicoob
from sicoob.exceptions import BoletoNaoEncontradoError

async def consultar_com_retry_async(nosso_numero, max_tentativas=3):
    async with AsyncSicoob(client_id=client_id, ...) as client:
        for tentativa in range(max_tentativas):
            try:
                boleto = await client.cobranca.boleto.consultar_boleto(nosso_numero)
                return boleto
            except BoletoNaoEncontradoError:
                if tentativa < max_tentativas - 1:
                    await asyncio.sleep(2 ** tentativa)  # Backoff exponencial
                else:
                    raise
```

**Mudanças aplicadas:**
1. ✅ `time.sleep()` → `asyncio.sleep()`
2. ✅ Adicionado `await` nas chamadas

## Tabela de Equivalências

### Métodos de Boleto

| Operação | Sync | Async |
|----------|------|-------|
| **Emitir** | `client.cobranca.boleto.emitir_boleto(dados)` | `await client.cobranca.boleto.emitir_boleto(dados)` |
| **Emitir com Verificação** | `client.cobranca.boleto.emitir_e_verificar_boleto(dados)` | `await client.cobranca.boleto.emitir_e_verificar_boleto(dados)` |
| **Emitir com Recovery** | `client.cobranca.boleto.emitir_com_recovery(dados)` | `await client.cobranca.boleto.emitir_com_recovery(dados)` |
| **Consultar** | `client.cobranca.boleto.consultar_boleto(nosso_numero)` | `await client.cobranca.boleto.consultar_boleto(nosso_numero)` |
| **Listar** | `client.cobranca.boleto.listar_boletos(...)` | `await client.cobranca.boleto.listar_boletos(...)` |
| **Alterar** | `client.cobranca.boleto.alterar_boleto(nosso_numero, dados)` | `await client.cobranca.boleto.alterar_boleto(nosso_numero, dados)` |
| **Baixar** | `client.cobranca.boleto.baixar_boleto(nosso_numero, dados)` | `await client.cobranca.boleto.baixar_boleto(nosso_numero, dados)` |

### Métodos de Lote (Exclusivos Async)

| Operação | Async |
|----------|-------|
| **Emitir Lote** | `await client.cobranca.boleto.emitir_boletos_lote(lista_dados, max_concorrencia=10)` |
| **Consultar Lote** | `await client.cobranca.boleto.consultar_boletos_lote(lista_nossos_numeros, max_concorrencia=10)` |

### Utilitários

| Operação | Sync | Async |
|----------|------|-------|
| **Sleep** | `time.sleep(segundos)` | `await asyncio.sleep(segundos)` |
| **Parallel Execution** | Loops sequenciais | `await asyncio.gather(*tasks)` |

## Boas Práticas

### 1. Rate Limiting

Sempre respeite os limites da API Sicoob (~4.5 req/s):

```python
from asyncio import Semaphore

async with AsyncSicoob(
    client_id=client_id,
    max_concurrent_requests=5,
) as client:
    limiter = Semaphore(5)
    delay = 1 / 4.5  # ~220ms

    async def processar_com_limite(dados):
        async with limiter:
            await asyncio.sleep(delay)
            return await client.cobranca.boleto.emitir_boleto(dados)
```

### 2. Tratamento de Erros

Capture exceções individualmente em operações paralelas:

```python
async def emitir_seguro(dados):
    try:
        return await client.cobranca.boleto.emitir_boleto(dados)
    except Exception as e:
        return {'erro': str(e), 'dados': dados}

tasks = [emitir_seguro(d) for d in lista_dados]
resultados = await asyncio.gather(*tasks)  # Não falha no primeiro erro
```

### 3. Logging Estruturado

```python
import logging

logger = logging.getLogger(__name__)

async def emitir_com_log(dados, indice):
    logger.info(f"[{indice:03d}] Emitindo boleto {dados['seuNumero']}")
    try:
        resultado = await client.cobranca.boleto.emitir_boleto(dados)
        logger.info(f"[{indice:03d}] ✅ Sucesso: {resultado['resultado']['nossoNumero']}")
        return resultado
    except Exception as e:
        logger.error(f"[{indice:03d}] ❌ Erro: {e}")
        raise
```

### 4. Context Managers

Sempre use `async with` para garantir limpeza de recursos:

```python
# ✅ Correto
async with AsyncSicoob(...) as client:
    resultado = await client.cobranca.boleto.emitir_boleto(dados)

# ❌ Incorreto - recursos podem não ser liberados
client = AsyncSicoob(...)
resultado = await client.cobranca.boleto.emitir_boleto(dados)
```

### 5. Reuso de Cliente

Reutilize o cliente async para múltiplas operações:

```python
# ✅ Eficiente - um cliente, múltiplas operações
async with AsyncSicoob(...) as client:
    boleto1 = await client.cobranca.boleto.emitir_boleto(dados1)
    boleto2 = await client.cobranca.boleto.emitir_boleto(dados2)
    consulta = await client.cobranca.boleto.consultar_boleto(nosso_numero)

# ❌ Ineficiente - reconexão a cada operação
async with AsyncSicoob(...) as client:
    boleto1 = await client.cobranca.boleto.emitir_boleto(dados1)
async with AsyncSicoob(...) as client:
    boleto2 = await client.cobranca.boleto.emitir_boleto(dados2)
```

### 6. Retry Automático Global (Novo!)

A versão async suporta retry automático para erros de infraestrutura:

```python
# Configuração de retry para erros transitórios
async with AsyncSicoob(
    client_id="...",
    retry_config={
        'max_tentativas': 3,           # Máximo de tentativas
        'delay_inicial': 1.0,          # Delay inicial (exponencial)
        'backoff_exponencial': True,   # Usar backoff exponencial
        'codigos_retry': [500, 502, 503, 504, 429],  # Códigos HTTP para retry
    }
) as client:
    # Todas as operações têm retry automático
    resultado = await client.cobranca.boleto.emitir_boleto(dados)
```

**Quando usar:**
- ✅ Ambientes com instabilidade de rede
- ✅ APIs com rate limiting (429)
- ✅ Servidores com erros transitórios (500, 503)
- ❌ Não é necessário para erros de validação (4xx)

**Diferença entre retry global e métodos especializados:**

| Recurso | Retry Global | emitir_e_verificar_boleto() |
|---------|--------------|----------------------------|
| **Propósito** | Erros de infraestrutura | Delay de propagação DDA |
| **Quando retenta** | 500, 502, 503, 504, 429 | Após emissão bem-sucedida |
| **Configuração** | retry_config no construtor | max_tentativas no método |
| **Pode combinar** | ✅ Sim | ✅ Sim |

**Exemplo combinando ambos:**

```python
# Retry global + verificação DDA
async with AsyncSicoob(
    client_id="...",
    retry_config={'max_tentativas': 3}  # Retry em erros 500/503
) as client:
    # Também verifica propagação DDA
    resultado = await client.cobranca.boleto.emitir_e_verificar_boleto(
        dados,
        max_tentativas=2  # Retry de verificação
    )

    # Resultado:
    # - Se servidor retornar 503, tenta 3x (retry global)
    # - Se emissão suceder, verifica DDA 2x (método especializado)
```

**Migração de retry manual para retry global:**

```python
# ❌ Antes - Retry manual
async def emitir_com_retry_manual(dados):
    for tentativa in range(3):
        try:
            return await client.cobranca.boleto.emitir_boleto(dados)
        except SicoobError as e:
            if e.code in [500, 503] and tentativa < 2:
                await asyncio.sleep(2 ** tentativa)
                continue
            raise

# ✅ Depois - Retry automático
async with AsyncSicoob(
    client_id="...",
    retry_config={'max_tentativas': 3, 'delay_inicial': 1.0}
) as client:
    # Retry automático, menos código boilerplate
    resultado = await client.cobranca.boleto.emitir_boleto(dados)
```

## Troubleshooting

### Erro: "RuntimeError: asyncio.run() cannot be called from a running event loop"

**Causa:** Tentando executar `asyncio.run()` dentro de um contexto já async.

```python
# ❌ Incorreto
async def minha_funcao():
    resultado = asyncio.run(emitir_boleto())  # ERRO!

# ✅ Correto
async def minha_funcao():
    resultado = await emitir_boleto()
```

### Erro: "object dict can't be used in 'await' expression"

**Causa:** Esqueceu de adicionar `await` em uma chamada async.

```python
# ❌ Incorreto
resultado = client.cobranca.boleto.emitir_boleto(dados)

# ✅ Correto
resultado = await client.cobranca.boleto.emitir_boleto(dados)
```

### Erro: "SyntaxError: 'await' outside function"

**Causa:** Usando `await` em função não-async.

```python
# ❌ Incorreto
def minha_funcao():
    resultado = await client.cobranca.boleto.emitir_boleto(dados)

# ✅ Correto
async def minha_funcao():
    resultado = await client.cobranca.boleto.emitir_boleto(dados)
```

### Performance não melhorou após migração

**Causa:** Não está aproveitando concorrência.

```python
# ❌ Ainda sequencial
async with AsyncSicoob(...) as client:
    for dados in lista_dados:
        resultado = await client.cobranca.boleto.emitir_boleto(dados)

# ✅ Paralelo
async with AsyncSicoob(...) as client:
    tasks = [client.cobranca.boleto.emitir_boleto(d) for d in lista_dados]
    resultados = await asyncio.gather(*tasks)
```

### Muitos erros de rate limiting

**Causa:** Concorrência muito alta.

```python
# ✅ Adicionar rate limiting
from asyncio import Semaphore

limiter = Semaphore(5)  # Max 5 concurrent
delay = 1 / 4.5  # ~220ms entre requests

async def processar(dados):
    async with limiter:
        await asyncio.sleep(delay)
        return await client.cobranca.boleto.emitir_boleto(dados)
```

## Recursos Adicionais

- [Documentação asyncio](https://docs.python.org/3/library/asyncio.html)
- [Exemplos práticos](../examples/)
- [Troubleshooting geral](../README.md#troubleshooting)

## Próximos Passos

1. Teste sua migração em ambiente de sandbox primeiro
2. Monitore logs para identificar gargalos
3. Ajuste `max_concurrent_requests` conforme necessário
4. Implemente retry e circuit breaker para resiliência

**Dúvidas?** Consulte os [exemplos práticos](../examples/) ou abra uma issue no GitHub.
