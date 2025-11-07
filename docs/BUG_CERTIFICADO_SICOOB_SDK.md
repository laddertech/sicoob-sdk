# Bug: Certificado Client não configurado no AsyncAPIClient (sicoob-sdk v0.2.5)

## ✅ STATUS: CORRIGIDO (2025-01-07)

**Este bug foi corrigido na versão 0.2.6+** 🎉

### Solução Implementada

Implementado carregamento automático de certificados PFX/PKCS12 no `AsyncAPIClient`:

- **Arquivo:** `sicoob/async_client.py`
- **Novo método:** `_load_pfx_certificate()` (linhas 117-188)
- **Modificações em:** `_ensure_session()` (linhas 190-248)
- **Nova dependência:** `cryptography>=41.0.0`

**Como funciona:**
1. Extrai certificado e chave privada do arquivo PFX usando `cryptography.hazmat.primitives.serialization.pkcs12`
2. Converte para formato PEM em arquivos temporários
3. Carrega no `ssl.SSLContext` usando `load_cert_chain()`
4. Arquivos temporários são automaticamente limpos ao fechar a sessão

**Nenhuma mudança necessária no código do usuário!** O certificado é carregado automaticamente quando você passa `certificado_pfx`:

```python
async with AsyncSicoob(
    client_id="seu_client_id",
    certificado_pfx="caminho/para/certificado.pfx",
    senha_pfx="sua_senha"
) as client:
    # Agora funciona! ✅
    boleto = await client.cobranca.boleto.emitir_boleto(dados)
```

**Testes:** 7 novos testes criados em `tests/test_async_client_certificate.py` cobrindo:
- Carregamento de PFX e PEM
- Cleanup de arquivos temporários
- Context manager
- Tratamento de erros

---

## 🔴 PROBLEMA CRÍTICO (HISTÓRICO - CORRIGIDO)

O `sicoob-sdk` versão 0.2.5 possui um **bug crítico** na implementação assíncrona que impede o uso do certificado digital nas requisições HTTP:

### Sintoma
```json
{
  "httpCode": "400",
  "httpMessage": "Bad Request",
  "moreInformation": "Client certificate is missing"
}
```

### Causa Raiz

A biblioteca tem duas implementações de clientes HTTP:

#### 1. **OAuth2Client (Síncrono)** ✅ FUNCIONA
- Arquivo: `sicoob/auth/oauth.py`
- Usa: `requests` com `requests_pkcs12.Pkcs12Adapter`
- Configura corretamente o certificado client para requisições OAuth (token)

```python
# sicoob/auth/oauth.py:50-59
pkcs12_adapter = requests_pkcs12.Pkcs12Adapter(
    pkcs12_data=self.certificado_pfx if isinstance(self.certificado_pfx, bytes) else None,
    pkcs12_filename=self.certificado_pfx if isinstance(self.certificado_pfx, str) else None,
    pkcs12_password=self.senha_pfx,
)
self.session.mount('https://', pkcs12_adapter)
```

#### 2. **AsyncAPIClient (Assíncrono)** ❌ BUG
- Arquivo: `sicoob/async_client.py`
- Usa: `aiohttp.ClientSession`
- **NÃO configura o certificado client no SSL context**

```python
# sicoob/async_client.py:97-122
async def _ensure_session(self) -> None:
    if self._session is None:
        # Cria SSL context básico SEM certificado client
        ssl_context = ssl.create_default_context()

        connector = TCPConnector(
            ssl=ssl_context,  # ❌ SSL context sem certificado!
            ...
        )

        self._session = ClientSession(
            connector=connector,
            ...
        )
```

### Impacto

- ✅ Requisições OAuth funcionam (síncronas, com certificado)
- ❌ Requisições de API falham (assíncronas, sem certificado)
- ❌ Impossível usar `AsyncBoletoAPI.emitir_boleto()`
- ❌ Impossível usar `AsyncSicoob` para qualquer operação de API

## 🔧 WORKAROUND IMPLEMENTADO

### Localização
`project/apps/bank_api/services/async_bank_slip_service.py`

### Solução

1. **Função auxiliar `_create_ssl_context_from_pfx()`**
   - Extrai certificado e chave privada do PKCS12
   - Converte para formato PEM
   - Cria arquivos temporários
   - Configura `ssl.SSLContext` com `load_cert_chain()`

2. **Reconfiguração da sessão aiohttp**
   - Após criar `AsyncSicoob`, recria a sessão com SSL context correto
   - Fecha sessão antiga sem certificado
   - Cria nova sessão com `TCPConnector` configurado com o SSL context

### Código do Workaround

```python
# 1. Cria SSL context com certificado
ssl_context = _create_ssl_context_from_pfx(cert_data, cert_password)

# 2. Inicializa AsyncSicoob normalmente
async with AsyncSicoob(...) as sicoob:
    # 3. Força inicialização da sessão
    await sicoob._api_client._ensure_session()

    # 4. Recria sessão com SSL context correto
    if sicoob._api_client._session:
        await sicoob._api_client._session.close()

        connector = TCPConnector(
            ssl=ssl_context,  # ✅ SSL context COM certificado
            ...
        )

        sicoob._api_client._session = ClientSession(
            connector=connector,
            ...
        )
```

## 📋 HISTÓRICO DE DEBUGGING

### Erro 1: HTTP 404 (Endpoint incorreto)
- **Versão:** sicoob-sdk v0.2.0
- **Causa:** Endpoint estava como `/cobranca-bancaria/boleto` ao invés de `/v3/boletos`
- **Solução:** Atualização para v0.2.1 corrigiu o endpoint

### Erro 2: HTTP 400 (Payload inválido)
- **Causa:** Campos opcionais vazios sendo enviados
  - Email: `""` (string vazia) ao invés de omitir o campo
  - tipoJurosMora: `0` ao invés de `3` (isento)
  - Campos data/valor de multa/juros enviados mesmo quando `tipo=0`
- **Solução:** Ajustes no `map_boleto_to_api_data()` em `gerar.py`

### Erro 3: HTTP 400 (Certificado ausente) ← **ERRO REAL**
- **Versão:** sicoob-sdk v0.2.5
- **Causa:** AsyncAPIClient não configura certificado no aiohttp
- **Solução:** Workaround documentado acima

## 🚀 PRÓXIMOS PASSOS

### 1. Reportar Bug ao sicoob-sdk
Criar issue no repositório da biblioteca com:
- Descrição do problema
- Evidências (erro "Client certificate is missing")
- Análise do código (comparação OAuth2Client vs AsyncAPIClient)
- Sugestão de fix: Configurar SSL context no `_ensure_session()`

### 2. Fix Sugerido para a Biblioteca

```python
# sicoob/async_client.py
async def _ensure_session(self) -> None:
    if self._session is None:
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

        # Configura certificado client se fornecido
        if hasattr(self.oauth_client, 'certificado_pfx') and self.oauth_client.certificado_pfx:
            # Extrai cert/key do PKCS12 e configura SSL context
            ssl_context = self._configure_client_certificate(ssl_context)

        connector = TCPConnector(
            ssl=ssl_context,  # ✅ SSL context configurado
            ...
        )

        self._session = ClientSession(connector=connector, ...)
```

### 3. Monitorar Versões Futuras
- Testar sicoob-sdk >= 0.3.0 quando disponível
- Remover workaround quando bug for corrigido upstream

## 📚 REFERÊNCIAS

- **Postman Sicoob API:** https://d1zet1fng6kfaw.cloudfront.net/postman-collections/...
- **aiohttp SSL:** https://docs.aiohttp.org/en/stable/client_advanced.html#ssl-control-for-tcp-sockets
- **requests-pkcs12:** https://github.com/m-click/requests_pkcs12

## 📝 LOGS DE EVIDÊNCIA

```
INFO:bank_api.services.async_bank_slip_service:📤 PAYLOAD COMPLETO boleto 30191: {...}
INFO:bank_api.services.async_bank_slip_service:🔍 Chamando emitir_com_recovery(tentar_consulta_em_404=True)
INFO:bank_api.services.async_bank_slip_service:🌐 URL de emissão: POST https://api.sicoob.com.br/cobranca-bancaria/v3/boletos
ERROR:bank_api.services.async_bank_slip_service:🔍 ERRO 400 INTERCEPTADO: [400] HTTP 400
ERROR:bank_api.services.async_bank_slip_service:🔍 Dados do erro 400: {
  "httpCode": "400",
  "httpMessage": "Bad Request",
  "moreInformation": "Client certificate is missing"
}
```

## ⚠️ OBSERVAÇÕES IMPORTANTES

1. **Temporário:** Este workaround deve ser removido quando a biblioteca corrigir o bug
2. **Performance:** A recriação da sessão tem overhead mínimo (apenas na inicialização)
3. **Arquivos temporários:** Os arquivos PEM criados não são removidos automaticamente (ficam em /tmp)
4. **Thread-safe:** O workaround é seguro para uso com múltiplas tasks concorrentes
5. **Compatibilidade:** Testado apenas com sicoob-sdk v0.2.5 e aiohttp 3.x

---

**Data:** 2025-01-07
**Autor:** Claude Code
**Status:** Workaround ativo, aguardando fix upstream
