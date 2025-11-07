# Sicoob SDK Python

SDK Python para integração com a API do Banco Sicoob

## Instalação

```bash
pip install -r requirements.txt
# ou
pip install -e .
```

## Configuração

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```ini
SICOOB_CLIENT_ID=seu_client_id
SICOOB_CERTIFICADO=caminho/para/certificado.pem
SICOOB_CHAVE_PRIVADA=caminho/para/chave_privada.key
```

## Uso Básico

```python
from sicoob import Sicoob

# Inicializa o cliente (usando certificado PEM)
# É obrigatório fornecer ou certificado+chave ou PFX+senha em ambiente de produção, mas opcional em ambiente de testes
cliente = Sicoob(
    client_id="seu_client_id",  # Obrigatório
    certificado="caminho/para/certificado.pem",  # Obrigatório se não usar PFX [E em produção]
    chave_privada="caminho/para/chave_privada.key",  # Obrigatório se não usar PFX [E em produção]
    sandbox_mode=False  # Opcional, default False
)

# Alternativa usando certificado PFX
cliente_pfx = Sicoob(
    client_id="seu_client_id",  # Obrigatório
    certificado_pfx="caminho/para/certificado.pfx",  # Obrigatório (pode ser path, bytes ou arquivo aberto) [E em produção]
    senha_pfx="senha_do_pfx",  # Obrigatório se usar PFX [E em produção]
    sandbox_mode=True  # Opcional para ambiente de testes
)

# Exemplo: consulta de extratos
extrato = cliente.conta_corrente.extrato(
    mes=1,  # Obrigatório (1-12)
    ano=2023,  # Obrigatório
    dia_inicial=1,  # Obrigatório (1-31)
    dia_final=31,  # Obrigatório (1-31)
    numero_conta_corrente="12345",  # Obrigatório
    agrupar_cnab=False  # Opcional
)
```

## API de Cobrança

### Boletos Bancários

A classe `BoletoAPI` oferece operações completas para gerenciamento de boletos:

```python
from sicoob import Sicoob
from sicoob.exceptions import BoletoError, BoletoNaoEncontradoError

# Inicializa o cliente
cliente = Sicoob(
    client_id="seu_client_id",
    certificado="caminho/para/certificado.pem",
    chave_privada="caminho/para/chave_privada.key"
)

# Operações com boletos
boleto_api = cliente.cobranca.boleto()

try:
    # Emissão
    boleto = boleto_api.emitir_boleto({
        "numeroCliente": 123456,
        "codigoModalidade": 1,
        "numeroContaCorrente": 12345,
        "codigoEspecieDocumento": "DM",
        "dataEmissao": "2024-01-01",
        "nossoNumero": 123456789,
        "seuNumero": "1235512",
        "identificacaoBoletoEmpresa": "4562",
        "identificacaoEmissaoBoleto": 1,
        "identificacaoDistribuicaoBoleto": 1,
        "valor": 156.23,
        "dataVencimento": "2024-12-31",
        "dataLimitePagamento": "2024-12-31",
        "valorAbatimento": 1.0,
        "tipoDesconto": 1,
        "dataPrimeiroDesconto": "2024-06-01",
        "valorPrimeiroDesconto": 1.0,
        "dataSegundoDesconto": "2024-06-15",
        "valorSegundoDesconto": 0.0,
        "dataTerceiroDesconto": "2024-06-30",
        "valorTerceiroDesconto": 0.0,
        "tipoMulta": 1,
        "dataMulta": "2025-01-01",
        "valorMulta": 5.0,
        "tipoJurosMora": 1,
        "dataJurosMora": "2025-01-01",
        "valorJurosMora": 4.0,
        "numeroParcela": 1,
        "aceite": True,
        "codigoNegativacao": 2,
        "numeroDiasNegativacao": 60,
        "codigoProtesto": 1,
        "numeroDiasProtesto": 30,
        "pagador": {
            "numeroCpfCnpj": "98765432185",
            "nome": "Marcelo dos Santos",
            "endereco": "Rua 87 Quadra 1 Lote 1 casa 1",
            "bairro": "Santa Rosa",
            "cidade": "Luziânia",
            "cep": "72320000",
            "uf": "DF",
            "email": "pagador@dominio.com.br"
        },
        "beneficiarioFinal": {
            "numeroCpfCnpj": "98784978699",
            "nome": "Lucas de Lima"
        },
        "mensagensInstrucao": [
            "Descrição da Instrução 1",
            "Descrição da Instrução 2",
            "Descrição da Instrução 3",
            "Descrição da Instrução 4",
            "Descrição da Instrução 5"
        ],
        "gerarPdf": False,
        "rateioCreditos": [
            {
                "numeroBanco": 756,
                "numeroAgencia": 4027,
                "numeroContaCorrente": "987654",
                "contaPrincipal": true,
                "codigoTipoValorRateio": 1,
                "valorRateio": 100,
                "codigoTipoCalculoRateio": 1,
                "numeroCpfCnpjTitular": "98765432185",
                "nomeTitular": "Marcelo dos Santos",
                "codigoFinalidadeTed": 10,
                "codigoTipoContaDestinoTed": "CC",
                "quantidadeDiasFloat": 1,
                "dataFloatCredito": "2020-12-30"
            }
        ],
        "codigoCadastrarPIX": 1,
        "numeroContratoCobranca": 1
    })

    # Consultas
    boleto_consultado = boleto_api.consultar_boleto(
        numero_cliente=123456,  # Obrigatório
        codigo_modalidade=1,  # Obrigatório
        nosso_numero="123456789"  # Obrigatório (ou linha_digitavel ou codigo_barras)
    )
    
    boletos_pagador = boleto_api.consultar_boletos_por_pagador(
        numero_cpf_cnpj="12345678901",  # Obrigatório
        numero_cliente=123456,  # Obrigatório
        client_id="seu_client_id"  # Obrigatório
    )
    
    faixas = boleto_api.consultar_faixas_nosso_numero(
        numero_cliente=123456,  # Obrigatório
        codigo_modalidade=1,  # Obrigatório
        quantidade=10,  # Obrigatório
        client_id="seu_client_id"  # Obrigatório
    )

    # Webhooks
    boleto_api.cadastrar_webhook(
        webhook={
            "url": "https://meusite.com/webhook",  # Obrigatório
            "codigoTipoMovimento": 7,  # Obrigatório (7-Pagamento)
            "codigoPeriodoMovimento": 1  # Obrigatório
        },
        client_id="seu_client_id"  # Obrigatório
    )
    
    webhook = boleto_api.consultar_webhook(
        id_webhook=1,  # Obrigatório
        codigo_tipo_movimento=7,  # Obrigatório
        client_id="seu_client_id"  # Obrigatório
    )

except BoletoNaoEncontradoError:
    print("Boleto não encontrado")
except BoletoError as e:
    print(f"Erro na API de boletos: {e}")
```

### PIX

A classe `PixAPI` implementa todas as operações PIX disponíveis:

```python
from sicoob.exceptions import (
    CobrancaPixError, CobrancaPixNaoEncontradaError,
    CobrancaPixVencimentoError, WebhookPixError,
    LoteCobrancaPixError, QrCodePixError
)

# Operações PIX
pix_api = cliente.cobranca.pix()

try:
    # Cobranças imediatas
    cobranca = pix_api.criar_cobranca_pix(
        txid="tx123",  # Obrigatório (máx 35 caracteres)
        dados_cobranca={  # Obrigatório
            "valor": {"original": "100.50"},  # Obrigatório
            "chave": "123e4567-e89b-12d3-a456-426614174000",  # Obrigatório
            "solicitacaoPagador": "Pagamento do pedido 123"  # Opcional
        }
    )

    # Cobranças com vencimento
    cobranca_venc = pix_api.criar_cobranca_pix_com_vencimento(
        txid="tx456",  # Obrigatório
        dados_cobranca={  # Obrigatório
            "valor": {"original": "200.00"},  # Obrigatório
            "calendario": {"dataDeVencimento": "2025-12-31"},  # Obrigatório
            "chave": "123e4567-e89b-12d3-a456-426614174000"  # Obrigatório
        }
    )

    # Consulta cobrança
    cobranca_consultada = pix_api.consultar_cobranca_pix(txid="tx123")
    
    # Cancelamento
    pix_api.cancelar_cobranca_pix(txid="tx123")
    
    # QR Code
    qrcode = pix_api.obter_qrcode_pix(txid="tx123")

    # Webhooks PIX
    pix_api.configurar_webhook_pix(
        chave="123e4567-e89b-12d3-a456-426614174000",  # Obrigatório
        webhook_url="https://meusite.com/pix-webhook"  # Obrigatório
    )
    
    # Consulta webhook
    webhook = pix_api.consultar_webhook_pix(
        chave="123e4567-e89b-12d3-a456-426614174000"
    )
    
    # Exclusão webhook
    pix_api.excluir_webhook_pix(
        chave="123e4567-e89b-12d3-a456-426614174000"
    )

    # Lotes de cobrança
    lote = pix_api.criar_lote_cobranca_pix_com_vencimento(
        id_lote="lote001",
        cobrancas=[{
            "txid": "tx789",
            "valor": {"original": "300.00"},
            "calendario": {"dataDeVencimento": "2025-12-31"},
            "chave": "123e4567-e89b-12d3-a456-426614174000"
        }]
    )
    
    lote_consultado = pix_api.consultar_lote_cobranca_pix_com_vencimento("lote001")

except CobrancaPixNaoEncontradaError:
    print("Cobrança PIX não encontrada")
except CobrancaPixVencimentoError:
    print("Erro em cobrança PIX com vencimento")
except WebhookPixError:
    print("Erro em operação de webhook PIX")
except LoteCobrancaPixError:
    print("Erro em operação com lote de cobranças PIX")
except QrCodePixError:
    print("Erro em operação com QR Code PIX")
except CobrancaPixError as e:
    print(f"Erro na API PIX: {e}")
```

### Tratamento de Erros

O SDK possui exceções específicas para cada tipo de operação:

```python
from sicoob.exceptions import (
    BoletoError, BoletoNaoEncontradoError,
    PixError, CobrancaPixNaoEncontradaError,
    CobrancaPixVencimentoError, WebhookPixError,
    LoteCobrancaPixError, QrCodePixError,
    ContaCorrenteError, TransferenciaError
)

try:
    boleto = boleto_api.consultar_boleto("123456")
except BoletoNaoEncontradoError:
    print("Boleto não encontrado")
except BoletoError as e:
    print(f"Erro na API de boletos: {e}")

try:
    pix_api.criar_cobranca_pix("tx123", dados)
except CobrancaPixError as e:
    print(f"Erro na API PIX: {e}")
```

## Serviços de Conta Corrente

A classe `ContaCorrenteAPI` oferece operações bancárias:

```python
conta_api = cliente.conta_corrente()

# Consultas
extrato = conta_api.extrato(
    mes=6, 
    ano=2025,
    dia_inicial=1,
    dia_final=30,
    numero_conta_corrente="123456"
)

saldo = conta_api.saldo("123456")

# Transferências
transferencia = conta_api.transferencia(
    valor=1000.00,  # Obrigatório
    conta_destino="654321",  # Obrigatório
    tipo_transferencia="TED",  # Opcional (TED/DOC/PIX)
    descricao="Transferência entre contas",  # Opcional
    numero_conta="123456"  # Opcional se já configurado no cliente
)
```

## Versionamento e Deploy

O projeto segue [Semantic Versioning](https://semver.org/). Para criar um novo release:

1. Atualize a versão em:
   - `setup.py`
   - `pyproject.toml`
   - `sicoob/__init__.py`

2. Execute os testes:
```bash
make test
```

3. Crie um novo release no GitHub:
   - Acesse "Releases" no repositório
   - Clique em "Draft a new release"
   - Defina a tag no formato `vX.Y.Z` (ex: `v0.1.3`)
   - O GitHub Actions irá automaticamente:
     - Construir o pacote (`make build`)
     - Publicar no PyPI (`make publish`)

### Comandos Úteis
```bash
# Construir pacote
make build

# Executar testes
make test

# Publicar no PyPI (requer TWINE_USERNAME e TWINE_PASSWORD)
make publish

# Incrementar versão (patch, minor ou major)
make bump-patch   # Incrementa patch version (0.1.2 → 0.1.3)
make bump-minor   # Incrementa minor version (0.1.2 → 0.2.0)
make bump-major   # Incrementa major version (0.1.2 → 1.0.0)
```

### Como Incrementar a Versão
1. Execute o comando apropriado:
```bash
make bump-patch   # Para correções de bugs
make bump-minor   # Para novas funcionalidades compatíveis
make bump-major   # Para mudanças incompatíveis
```

2. Execute os testes para garantir a qualidade:
```bash
make test
```

3. Verifique as alterações nos arquivos:
```bash
git diff
```

4. Commit e push das alterações:
```bash
git add .
git commit -m "Bump version to X.Y.Z"
git push
```

5. Crie um novo release no GitHub para disparar a publicação automática no PyPI

## Links Úteis

- [Documentação API Sicoob](https://developers.sicoob.com.br)
- [Portal de Desenvolvedores](https://developers.sicoob.com.br/portal)

## Documentação Técnica

### Visão Geral
Biblioteca Python para integração com a API do Banco Sicoob, incluindo:
- Autenticação OAuth2
- Cobrança (Boletos e PIX)
- Conta Corrente
- Operações bancárias

### Índice
1. [Classe Principal](#classe-sicoob)
2. [Autenticação](#autenticação-oauth2)
3. [Serviços](#serviços)
   - [Cobrança](#api-de-cobrança)
     - [Boletos](#boletos-bancários)
     - [PIX](#pix)
   - [Conta Corrente](#serviços-de-conta-corrente)
4. [Classe Base](#classe-base)
5. [Tratamento de Erros](#tratamento-de-erros)
6. [Diagrama de Relacionamentos](#diagrama-de-relacionamentos)
7. [Exemplos de Uso](#exemplos-de-uso)

---

### Classe Sicoob
Cliente principal que fornece acesso a todos os serviços.

**Arquivo:** `sicoob/client.py`

#### Métodos:
- `__init__(client_id=None, certificado=None, chave_privada=None, certificado_pfx=None, senha_pfx=None, sandbox_mode=False)`
  - Inicializa o cliente com credenciais
  - Parâmetros:
    - `client_id`: Client ID fornecido pelo Sicoob
    - `certificado`: Caminho para o certificado .pem
    - `chave_privada`: Caminho para a chave privada .key
    - `certificado_pfx`: Caminho (str), bytes ou arquivo aberto (BinaryIO) do certificado PFX (opcional)
    - `sandbox_mode`: Se True, usa ambiente sandbox (default: False)

#### Propriedades:
- `cobranca`: Acesso às APIs de Cobrança (Boleto e PIX)
- `conta_corrente`: Acesso à API de Conta Corrente

---

### Autenticação OAuth2
**Arquivo:** `sicoob/auth/oauth.py`

#### Classe: OAuth2Client
Gerencia tokens de acesso com escopos específicos.

#### Métodos:
- `get_access_token(scope=None)`: Obtém token para o escopo especificado
- `_is_token_expired(scope)`: Verifica se token expirou (método interno)

#### Escopos Comuns:
- **Boletos**: `"boletos_inclusao boletos_consulta..."`
- **Conta Corrente**: `"cco_consulta cco_transferencias..."`
- **PIX**: `"cob.write cob.read..."`

---

### Serviços

#### API de Boletos
**Arquivo:** `sicoob/boleto.py`

#### Classe: BoletoAPI
Operações com boletos bancários.

#### Métodos:
- `emitir_boleto(dados_boleto)`: Emite novo boleto
- `emitir_segunda_via()`: Emite segunda via de um boleto existente
- `consultar_boleto(nosso_numero)`: Consulta boleto existente
- `consultar_boletos_por_pagador()`: Consulta lista de boletos por pagador
- `consultar_faixas_nosso_numero()`: Consulta faixas de nosso número disponíveis
- `alterar_boleto()`: Altera dados de um boleto existente
- `alterar_pagador()`: Altera informações do cadastro do pagador
- `baixar_boleto()`: Comanda a baixa de um boleto existente
- `cadastrar_webhook()`: Cadastra um webhook para receber notificações
- `consultar_webhook()`: Consulta os detalhes de um webhook cadastrado
- `atualizar_webhook()`: Atualiza um webhook cadastrado
- `excluir_webhook()`: Remove permanentemente um webhook cadastrado
- `consultar_solicitacoes_webhook()`: Consulta as solicitações de notificação

#### API de PIX
**Arquivo:** `sicoob/pix.py`

#### Classe: PixAPI
Operações com PIX.

#### Métodos Principais:
- `criar_cobranca_pix(txid, dados)`: Cria cobrança imediata
- `consultar_cobranca_pix(txid)`: Consulta cobrança
- `configurar_webhook(chave, url)`: Configura webhook

#### API de Conta Corrente
**Arquivo:** `sicoob/conta_corrente.py`

#### Classe: ContaCorrenteAPI
Operações bancárias.

#### Métodos:
- `extrato()`: Obtém extrato por período
- `saldo()`: Consulta saldo
- `transferencia()`: Realiza transferência

---

### Classe Base
**Arquivo:** `sicoob/api_client.py`

#### Classe: APIClientBase
Fornece funcionalidades comuns a todas as APIs.

#### Métodos:
- `_get_base_url()`: Retorna URL conforme sandbox/produção
- `_get_headers(scope)`: Retorna headers com autenticação

---

### Diagrama de Relacionamentos

```mermaid
classDiagram
    class Sicoob {
        +cobranca
        +conta_corrente
    }
    
    class OAuth2Client {
        +get_access_token()
    }
    
    class APIClientBase {
        <<abstract>>
        +_get_base_url()
        +_get_headers()
    }
    
    class BoletoAPI {
        +emitir_boleto()
        +consultar_boleto()
    }
    
    class PixAPI {
        +criar_cobranca_pix()
        +consultar_cobranca_pix()
    }
    
    class ContaCorrenteAPI {
        +extrato()
        +saldo()
    }
    
    Sicoob --> OAuth2Client
    Sicoob --> BoletoAPI
    Sicoob --> PixAPI
    Sicoob --> ContaCorrenteAPI
    BoletoAPI --|> APIClientBase
    PixAPI --|> APIClientBase
    ContaCorrenteAPI --|> APIClientBase
    APIClientBase --> OAuth2Client
```

---

### Exemplos de Uso

```python
from sicoob import Sicoob
from sicoob.auth import OAuth2Client
import requests

# Configuração
oauth = OAuth2Client(client_id, certificado, chave)
session = requests.Session()
sicoob = Sicoob(oauth_client=oauth, session=session)

# Uso dos serviços
extrato = sicoob.conta_corrente.extrato(
    mes=6, ano=2025, dia_inicial=1, dia_final=30, 
    numero_conta_corrente=123456
)

boleto = sicoob.cobranca.boleto.emitir_boleto({
    "numeroCliente": 123456,
    "codigoModalidade": 1,
    "numeroContaCorrente": 12345,
    "codigoEspecieDocumento": "DM",
    "dataEmissao": "2024-01-01",
    "dataVencimento": "2024-12-31",
    "valor": 100.50,
    "seuNumero": "123456789",
    "identificacaoEmissaoBoleto": 1,
    "identificacaoDistribuicaoBoleto": 1,
    "tipoDesconto": 0,
    "tipoMulta": 0,
    "tipoJurosMora": 3,
    "numeroParcela": 1,
    "pagador": {
        "numeroCpfCnpj": "11122233300",
        "nome": "João Silva",
        "endereco": "Rua Teste, 123",
        "bairro": "Centro",
        "cidade": "São Paulo",
        "cep": "01001000",
        "uf": "SP"
    }
})

pix = sicoob.cobranca.pix.criar_cobranca_pix(
    "tx123",
    {"valor": {"original": "100.50"}}
)
```

---

## 🔧 Troubleshooting

### Erro 404 mesmo com boleto criado

**Sintoma:** API retorna 404 mas o boleto existe no banco e aparece no DDA

**Causa:** Comportamento não-padrão da API Sicoob em alguns cenários. A API pode retornar status 404 mas incluir os dados do boleto no corpo da resposta.

**Solução:**
- A biblioteca **já trata isso automaticamente** desde v0.1.34
- Use `emitir_e_verificar_boleto()` para maior robustez com retry automático
- Use `emitir_com_recovery()` para idempotência em reprocessamentos

```python
# Método 1: Com verificação e retry automático
resultado = client.cobranca.boleto.emitir_e_verificar_boleto(
    dados_boleto,
    max_tentativas=3,  # Tenta verificar até 3 vezes
    delay_inicial=1.0  # Delays: 1s, 2s, 4s
)

# Método 2: Com recovery automático (ideal para retries)
resultado = client.cobranca.boleto.emitir_com_recovery(
    dados_boleto,
    tentar_consulta_em_404=True  # Tenta recuperar se já existe
)
```

---

### Delay de propagação no DDA

**Sintoma:** Boleto emitido com sucesso mas não aparece em consulta imediatamente

**Causa:** Delay de propagação entre sistemas internos do Sicoob. O boleto é registrado mas leva alguns segundos para estar disponível via API de consulta.

**Solução:** Use `emitir_e_verificar_boleto()` que implementa retry com exponential backoff

```python
# Aguarda propagação automaticamente
resultado = client.cobranca.boleto.emitir_e_verificar_boleto(
    dados_boleto,
    max_tentativas=3,  # 3 tentativas de verificação
    delay_inicial=1.0  # Delays exponenciais: 1s, 2s, 4s
)
```

---

### Diferenças entre métodos de emissão

**Quando usar cada método:**

| Método | Caso de Uso | Retry | Recovery |
|--------|-------------|-------|----------|
| `emitir_boleto()` | Emissão simples, sem retry | ❌ | ❌ |
| `emitir_e_verificar_boleto()` | Delay de propagação DDA | ✅ | ❌ |
| `emitir_com_recovery()` | Reprocessamento, idempotência | ❌ | ✅ |

**Exemplo de escolha:**

```python
# Caso 1: Emissão normal (primeira vez)
boleto = client.cobranca.boleto.emitir_boleto(dados)

# Caso 2: Emissão com verificação (produção, alto volume)
boleto = client.cobranca.boleto.emitir_e_verificar_boleto(
    dados,
    max_tentativas=2
)

# Caso 3: Reprocessamento de falhas (sistema de retry)
for boleto_pendente in obter_boletos_com_erro():
    try:
        # Tenta emitir, mas se já existe, apenas recupera
        resultado = client.cobranca.boleto.emitir_com_recovery(
            boleto_pendente.dados
        )
        if resultado.get('_recovery'):
            print(f"Boleto recuperado: {resultado['resultado']['nossoNumero']}")
    except BoletoEmissaoError:
        marcar_erro_definitivo(boleto_pendente)
```

---

### Versão Async vs Sync

**Diferenças principais:**

| Aspecto | Sync (`Sicoob`) | Async (`AsyncSicoob`) |
|---------|-----------------|------------------------|
| Uso | `with Sicoob(...) as client` | `async with AsyncSicoob(...) as client` |
| Chamadas | `client.cobranca.boleto.emitir_boleto(...)` | `await client.cobranca.boleto.emitir_boleto(...)` |
| Performance | Sequential | Concurrent |
| Melhor para | Scripts simples, CLI | Processamento em lote, APIs |

**Métodos disponíveis:**

✅ Ambas versões têm paridade completa:
- `emitir_boleto()` / `async emitir_boleto()`
- `emitir_e_verificar_boleto()` / `async emitir_e_verificar_boleto()`
- `emitir_com_recovery()` / `async emitir_com_recovery()`
- `consultar_boleto()` / `async consultar_boleto()`

**Exemplo de migração:**

```python
# Sync (antes)
with Sicoob(client_id="...") as client:
    resultado = client.cobranca.boleto.emitir_e_verificar_boleto(dados)

# Async (depois)
async with AsyncSicoob(client_id="...") as client:
    resultado = await client.cobranca.boleto.emitir_e_verificar_boleto(dados)
```

---

### Rate Limiting

**Limites conhecidos:**
- API Sicoob: ~4.5 requisições/segundo
- Recomendado: Implementar rate limiting no lado do cliente

**Exemplo com versão async:**

```python
import asyncio
from asyncio import Semaphore

async def emitir_lote_com_rate_limit(boletos):
    limiter = Semaphore(5)  # Max 5 concurrent

    async def emitir_com_limite(dados):
        async with limiter:
            await asyncio.sleep(1/4.5)  # Rate limit
            return await client.cobranca.boleto.emitir_boleto(dados)

    # Processa em lote respeitando rate limit
    return await asyncio.gather(
        *[emitir_com_limite(b) for b in boletos],
        return_exceptions=True
    )
```

Veja [examples/emissao_lote_async.py](examples/emissao_lote_async.py) para exemplo completo.

---

### Retry Automático Global (AsyncSicoob)

A versão assíncrona suporta **retry automático** para erros de infraestrutura e rate limiting.

**Configuração:**

```python
from sicoob.async_client import AsyncSicoob

async with AsyncSicoob(
    client_id="...",
    certificado_pfx="...",
    senha_pfx="...",
    retry_config={
        'max_tentativas': 3,           # Número máximo de tentativas
        'delay_inicial': 1.0,          # Delay inicial em segundos
        'backoff_exponencial': True,   # Usar exponential backoff
        'codigos_retry': [500, 502, 503, 504, 429],  # Códigos HTTP para retry
    }
) as client:
    # Todas as operações usarão retry automático
    resultado = await client.cobranca.boleto.emitir_boleto(dados)
```

**Comportamento:**
- **Exponential backoff**: 1s, 2s, 4s, 8s... (com jitter de ±25%)
- **Códigos padrão para retry**: 500, 502, 503, 504, 429
- **Sem retry por padrão**: Para manter compatibilidade, configure `max_tentativas > 1`

**Quando usar:**
- ✅ Erros transitórios de servidor (500, 503)
- ✅ Rate limiting (429)
- ✅ Timeouts e falhas de rede
- ❌ Erros de validação (400, 404) - não faz retry

**Exemplo com e sem retry:**

```python
# Sem retry (comportamento padrão)
async with AsyncSicoob(client_id="...") as client:
    # Falha imediatamente em erro 503
    resultado = await client.cobranca.boleto.emitir_boleto(dados)

# Com retry automático
async with AsyncSicoob(
    client_id="...",
    retry_config={'max_tentativas': 3, 'delay_inicial': 0.5}
) as client:
    # Tenta 3x com backoff antes de falhar
    resultado = await client.cobranca.boleto.emitir_boleto(dados)
```

**Combinando com métodos especializados:**

O retry global é diferente de `emitir_e_verificar_boleto()`:
- **Retry global**: Retenta em erros de infraestrutura (500, 503, 429)
- **emitir_e_verificar_boleto()**: Verifica propagação DDA após sucesso

Você pode usar ambos juntos:

```python
async with AsyncSicoob(
    client_id="...",
    retry_config={'max_tentativas': 3}  # Retry em erros de servidor
) as client:
    # Também verifica propagação DDA
    resultado = await client.cobranca.boleto.emitir_e_verificar_boleto(
        dados,
        max_tentativas=2  # Retry de verificação DDA
    )
```

---

### Logs e Debugging

**Habilitar logs detalhados:**

```python
import logging

# Configure logging antes de usar o cliente
logging.basicConfig(level=logging.DEBUG)

# Agora os logs mostrarão:
# - Requisições HTTP (URL, método, headers)
# - Respostas (status code, tempo de resposta)
# - Retries e recoveries
# - Erros com stack traces
```

**Operações logadas:**
- `boleto_emissao_request` - Antes de emitir
- `boleto_emissao_response` - Resposta da emissão
- `boleto_emissao_404` - 404 detectado
- `boleto_emissao_404_sucesso` - 404 mas com dados válidos
- `boleto_verificacao_delay` - Aguardando retry
- `boleto_verificacao_sucesso` - Verificação bem-sucedida
- `boleto_recovery` - Tentando recovery
- `boleto_recovery_sucesso` - Recovery bem-sucedido

---

## 📚 Recursos Adicionais

- **Guia de Migração Sync → Async**: [docs/MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md)
- **Exemplos Práticos**: [examples/](examples/)
- **Documentação Completa**: [docs/](docs/)
- **Issues e Sugestões**: [GitHub Issues](https://github.com/laddertech/sicoob-sdk/issues)
