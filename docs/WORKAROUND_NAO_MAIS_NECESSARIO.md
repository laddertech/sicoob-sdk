# ✅ Workaround de Certificado NÃO É MAIS NECESSÁRIO

## 🎉 Bug Corrigido Upstream!

O bug crítico do certificado ausente no `AsyncAPIClient` foi **corrigido diretamente na biblioteca sicoob-sdk v0.2.6+**.

### O que mudou?

**ANTES (v0.2.5 - com bug):**
```python
# Era necessário um workaround manual
ssl_context = _create_ssl_context_from_pfx(cert_data, cert_password)

async with AsyncSicoob(...) as sicoob:
    await sicoob._api_client._ensure_session()

    # Recriar sessão manualmente com SSL context
    if sicoob._api_client._session:
        await sicoob._api_client._session.close()
        connector = TCPConnector(ssl=ssl_context, ...)
        sicoob._api_client._session = ClientSession(connector=connector, ...)
```

**DEPOIS (v0.2.6+ - corrigido):**
```python
# Funciona automaticamente, sem workaround! ✅
async with AsyncSicoob(
    client_id="seu_client_id",
    certificado_pfx="caminho/para/certificado.pfx",
    senha_pfx="sua_senha"
) as sicoob:
    # O certificado é carregado automaticamente
    boleto = await sicoob.cobranca.boleto.emitir_boleto(dados)
```

---

## 🔧 O que foi implementado na biblioteca

### 1. Novo método `_load_pfx_certificate()`
**Arquivo:** `sicoob/async_client.py` (linhas 117-188)

```python
def _load_pfx_certificate(
    self, ssl_context: ssl.SSLContext, pfx_path_or_data: str | bytes, password: str
) -> None:
    """Carrega certificado PFX/PKCS12 no contexto SSL."""
    # Extrai certificado e chave privada usando cryptography
    from cryptography.hazmat.primitives.serialization import pkcs12

    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        pfx_data, password_bytes, default_backend()
    )

    # Converte para PEM temporário
    # Carrega no SSL context
    ssl_context.load_cert_chain(cert_path, key_path)
```

### 2. Carregamento automático em `_ensure_session()`
**Arquivo:** `sicoob/async_client.py` (linhas 190-248)

```python
async def _ensure_session(self) -> None:
    ssl_context = ssl.create_default_context()

    # ✅ NOVO: Carrega certificado se fornecido
    if config.require_certificate:
        oauth_client = self.oauth_client

        # Prioriza PFX
        if hasattr(oauth_client, 'certificado_pfx') and oauth_client.certificado_pfx:
            self._load_pfx_certificate(
                ssl_context,
                oauth_client.certificado_pfx,
                oauth_client.senha_pfx,
            )
        # Fallback para PEM
        elif hasattr(oauth_client, 'certificado') and oauth_client.certificado:
            ssl_context.load_cert_chain(
                oauth_client.certificado, oauth_client.chave_privada
            )

    connector = TCPConnector(ssl=ssl_context, ...)
    self._session = ClientSession(connector=connector, ...)
```

### 3. Cleanup automático de arquivos temporários
**Arquivo:** `sicoob/async_client.py` (linhas 106-115)

```python
def _cleanup_temp_cert_files(self) -> None:
    """Limpa arquivos temporários de certificado."""
    for filepath in self._temp_cert_files:
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except Exception as e:
            logger.warning(f'Falha ao remover arquivo temporário: {e}')
```

### 4. Nova dependência
**Arquivo:** `pyproject.toml`

```toml
dependencies = [
    # ... outras dependências
    "cryptography>=41.0.0",  # ✅ NOVA
]
```

---

## 🧪 Testes Implementados

**Arquivo:** `tests/test_async_client_certificate.py`

7 novos testes cobrindo:
- ✅ Carregamento de certificado PFX
- ✅ Carregamento de certificado PEM
- ✅ Warning quando certificado não é fornecido
- ✅ Cleanup de arquivos temporários
- ✅ Context manager limpa certificados ao sair
- ✅ Suporte a PFX como path ou bytes
- ✅ Tratamento de erros em certificados inválidos

**Todos os 7 testes passaram! ✅**

---

## 📝 Instruções de Migração

### Passo 1: Atualizar dependências

```bash
# Instale a versão corrigida
pip install --upgrade sicoob-sdk>=0.2.6

# Ou se estiver usando o repositório local
pip install -e ".[dev]"
```

### Passo 2: Remover workaround

**Arquivo:** `project/apps/bank_api/services/async_bank_slip_service.py`

**REMOVER:**
- ❌ Função `_create_ssl_context_from_pfx()` (linhas 24-79)
- ❌ Bloco de reconfiguração da sessão (linhas 395-439)
- ❌ Imports: `ssl`, `tempfile`

**MANTER:**
```python
# Código simplificado - funciona automaticamente agora!
async with AsyncSicoob(
    client_id=settings.SICOOB_CLIENT_ID,
    certificado_pfx=settings.SICOOB_CERT_DATA,
    senha_pfx=settings.SICOOB_CERT_PASSWORD,
) as sicoob:
    # Certificado é carregado automaticamente ✅
    resultado = await sicoob.cobranca.boleto.emitir_boleto(dados)
```

### Passo 3: Testar emissão de boletos

```bash
# Execute seus testes normalmente
pytest tests/test_bank_slip_service.py -v

# Ou teste manualmente
python -m apps.bank_api.commands.emitir_boleto --id 123
```

---

## 🎯 Benefícios da Correção

1. **Código mais limpo:** Não precisa de workaround manual
2. **Manutenção reduzida:** Não há arquivos temporários para gerenciar
3. **Performance:** Sessão é criada apenas uma vez, não recriada
4. **Segurança:** Arquivos temporários são limpos automaticamente
5. **Compatibilidade:** Funciona tanto com PFX quanto PEM

---

## 🐛 Troubleshooting

### Problema: ImportError: No module named 'cryptography'

**Solução:**
```bash
pip install cryptography>=41.0.0
```

### Problema: ValueError: Falha ao carregar certificado PFX

**Possíveis causas:**
1. Senha incorreta
2. Arquivo PFX corrompido
3. Formato não suportado

**Debug:**
```python
from sicoob import SicoobConfig

# Ativa logs detalhados
SicoobConfig.enable_debug()

# Tente inicializar
async with AsyncSicoob(...) as client:
    # Verá logs detalhados do carregamento do certificado
    pass
```

### Problema: "Client certificate is missing" ainda aparece

**Verificações:**
1. Confirme que está usando sicoob-sdk v0.2.6+
   ```python
   import sicoob
   print(sicoob.__version__)  # Deve ser >= 0.2.6
   ```

2. Confirme que o certificado está sendo passado
   ```python
   # Certifique-se de passar certificado_pfx E senha_pfx
   AsyncSicoob(
       client_id="...",
       certificado_pfx="caminho.pfx",  # ✅
       senha_pfx="senha123",           # ✅
   )
   ```

3. Verifique se está em ambiente de produção
   ```python
   from sicoob import SicoobConfig

   # Deve retornar True em produção
   print(SicoobConfig.requires_certificate())
   ```

---

## 📚 Referências

- **Bug Report Completo:** `docs/BUG_CERTIFICADO_SICOOB_SDK.md`
- **Melhorias de Logging:** `docs/MELHORIAS_LOGGING_SICOOB_SDK.md`
- **Testes:** `tests/test_async_client_certificate.py`
- **Código Fonte:** `sicoob/async_client.py`

---

## ✅ Checklist de Migração

- [ ] Atualizar sicoob-sdk para v0.2.6+
- [ ] Instalar cryptography>=41.0.0
- [ ] Remover função `_create_ssl_context_from_pfx()`
- [ ] Remover bloco de reconfiguração manual da sessão
- [ ] Simplificar código para usar AsyncSicoob diretamente
- [ ] Executar testes
- [ ] Testar emissão de boletos em staging
- [ ] Deploy para produção
- [ ] Verificar logs de erro (não deve haver "Client certificate is missing")
- [ ] Remover este documento após confirmação ✅

---

**Data da Correção:** 2025-01-07
**Versão Corrigida:** sicoob-sdk v0.2.6+
**Status:** ✅ Pronto para produção
**Workaround Anterior:** ❌ NÃO MAIS NECESSÁRIO
