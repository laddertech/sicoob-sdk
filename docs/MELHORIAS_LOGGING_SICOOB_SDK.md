# Sugestões de Melhorias de Logging/Debugging para sicoob-sdk

## ✅ STATUS DE IMPLEMENTAÇÃO (2025-01-07)

**Bug Crítico do Certificado:** ✅ CORRIGIDO na v0.2.6+
- Certificado PFX agora é carregado automaticamente no AsyncAPIClient
- Veja `BUG_CERTIFICADO_SICOOB_SDK.md` para detalhes

**Melhorias Implementadas:**
- ✅ Item 1: Preservar response body em exceções (implementado)
- ✅ Item 2: Enriquecer classes de exceção (implementado)
- ✅ Item 3: Logger estruturado (implementado)
- ✅ Item 4: Mensagens de erro melhoradas (implementado)
- ✅ Item 5: Modo debug global (implementado)
- ✅ Item 6: Context manager para debug (implementado - NOVO!)
- ⏳ Item 7: CLI para testes (não implementado - opcional)

---

## Contexto

Durante a implementação de emissão de boletos via API Sicoob, identificamos dificuldades significativas em debugar erros HTTP 400/404 devido à falta de detalhes nas exceções e logs. Este documento propõe melhorias específicas para facilitar o diagnóstico de problemas.

---

## 1. 🔴 CRÍTICO: Preservar Response Body em Exceções HTTP

### Problema Atual

**Arquivo:** `sicoob/async_client.py`
**Linhas:** 229, 264-270

```python
# Linha 229: Lê o corpo da resposta
response_text = await response.text()

# Linha 264-270: Tenta fazer JSON novamente, mas corpo já foi consumido
try:
    error_data = await response.json()  # ❌ FALHA - corpo já lido linha 229
    error_msg = error_data.get('message', f'HTTP {response.status}')
except Exception:
    error_msg = f'HTTP {response.status}: {response_text}'

raise SicoobError(error_msg)  # ❌ Perde detalhes estruturados do erro
```

**Impacto:**
- Desenvolvedores não conseguem ver mensagens específicas de validação da API
- Erros 400 aparecem apenas como "HTTP 400" sem detalhes
- Impossível debugar qual campo está causando erro de validação

### Solução Proposta

```python
# Linha 229: Lê o corpo da resposta
response_text = await response.text()

# Linha 264-270: Usa response_text já lido
try:
    error_data = json.loads(response_text)  # ✅ Usa texto já lido

    # Extrai mensagem principal
    if 'mensagens' in error_data and isinstance(error_data['mensagens'], list):
        # Formato padrão API Sicoob: {"mensagens": [{"mensagem": "...", "codigo": "..."}]}
        mensagens = error_data['mensagens']
        if mensagens:
            primeira_msg = mensagens[0].get('mensagem', '')
            error_msg = f"HTTP {response.status}: {primeira_msg}"

            # Adiciona outras mensagens se houver múltiplos erros
            if len(mensagens) > 1:
                outras = ', '.join([m.get('mensagem', '') for m in mensagens[1:]])
                error_msg += f" (+{len(mensagens)-1} erros: {outras})"
        else:
            error_msg = f"HTTP {response.status}"
    else:
        error_msg = error_data.get('message', f'HTTP {response.status}')

except json.JSONDecodeError:
    error_msg = f'HTTP {response.status}: {response_text[:500]}'  # Trunca em 500 chars

# ✅ Preserva response_text estruturado na exceção
raise SicoobError(
    error_msg,
    response_body=response_text,
    status_code=response.status,
    response_headers=dict(response.headers)
)
```

---

## 2. 🔴 CRÍTICO: Enriquecer Classes de Exceção

### Problema Atual

**Arquivo:** `sicoob/exceptions.py`

```python
class SicoobError(Exception):
    """Exceção base"""
    pass

class BoletoError(SicoobError):
    """Erro relacionado a boletos"""
    pass
```

**Impacto:**
- Exceções não carregam metadados úteis para debugging
- Não há acesso programático aos detalhes do erro HTTP
- Código cliente precisa fazer parsing manual de strings

### Solução Proposta

```python
import json
from typing import Optional, Dict, Any

class SicoobError(Exception):
    """Exceção base com detalhes da resposta HTTP"""

    def __init__(
        self,
        message: str,
        response_body: Optional[str] = None,
        status_code: Optional[int] = None,
        response_headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(message)
        self.response_body = response_body
        self.status_code = status_code
        self.code = status_code  # Mantém compatibilidade com código existente
        self.response_headers = response_headers

    def get_error_details(self) -> Dict[str, Any]:
        """Retorna dict com detalhes completos do erro"""
        if not self.response_body:
            return {}

        try:
            return json.loads(self.response_body)
        except json.JSONDecodeError:
            return {'raw_response': self.response_body}

    def get_validation_errors(self) -> list:
        """Extrai erros de validação específicos (formato API Sicoob)"""
        details = self.get_error_details()
        return details.get('mensagens', [])

    def __repr__(self):
        return f"{self.__class__.__name__}(message={self.args[0]!r}, status_code={self.status_code})"


class BoletoError(SicoobError):
    """Erro relacionado a boletos com detalhes de validação"""

    def get_campo_invalido(self) -> Optional[str]:
        """Retorna nome do campo que causou erro de validação, se disponível"""
        for msg in self.get_validation_errors():
            if 'campo' in msg:
                return msg['campo']
        return None
```

**Exemplo de Uso:**
```python
try:
    resultado = sicoob.cobranca.boleto.emitir_boleto(dados)
except BoletoError as e:
    print(f"Erro: {e}")  # Mensagem legível
    print(f"Status HTTP: {e.status_code}")  # 400
    print(f"Detalhes: {e.get_error_details()}")  # Dict completo
    print(f"Campo inválido: {e.get_campo_invalido()}")  # Ex: "numeroCliente"
```

---

## 3. 🟡 IMPORTANTE: Logger Estruturado para Requisições

### Problema Atual

**Arquivo:** `sicoob/async_client.py`
**Linhas:** 216-217, 231-232

```python
# Log da requisição (simplificado)
# TODO: Implementar logging apropriado quando SicoobLogger estiver disponível
```

**Impacto:**
- Impossível debugar payloads enviados sem modificar código da biblioteca
- Não há visibilidade sobre URLs chamadas, headers, timeouts
- Difficult troubleshooting em produção

### Solução Proposta

```python
import logging
from typing import Any

class AsyncAPIClient:
    def __init__(self, ..., enable_request_logging: bool = False):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.enable_request_logging = enable_request_logging
        # ... resto da init

    async def _make_request(self, method: str, url: str, scope: str, **kwargs: Any):
        await self._ensure_session()

        headers = self._get_headers(scope)
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers

        # ✅ Log ANTES da requisição
        if self.enable_request_logging or self.logger.isEnabledFor(logging.DEBUG):
            # Remove Authorization para segurança
            safe_headers = {k: v for k, v in headers.items() if k.lower() != 'authorization'}

            self.logger.debug(
                f"HTTP {method} {url}",
                extra={
                    'method': method,
                    'url': url,
                    'headers': safe_headers,
                    'payload_size': len(str(kwargs.get('json', '')))
                }
            )

            # Log completo do payload apenas se explicitamente ativado
            if self.enable_request_logging and 'json' in kwargs:
                self.logger.debug(f"Request payload: {kwargs['json']}")

        # ... código de retry existente

        async with self._session.request(method, url, **kwargs) as response:
            response_text = await response.text()

            # ✅ Log APÓS resposta
            if self.enable_request_logging or self.logger.isEnabledFor(logging.DEBUG):
                # Trunca response body em 1000 chars se muito grande
                body_preview = response_text[:1000] + ('...' if len(response_text) > 1000 else '')

                self.logger.debug(
                    f"HTTP {response.status} (em {kwargs.get('timeout', 'N/A')}s)",
                    extra={
                        'status': response.status,
                        'response_size': len(response_text),
                        'content_type': response.headers.get('Content-Type', 'unknown')
                    }
                )

                if self.enable_request_logging:
                    self.logger.debug(f"Response body: {body_preview}")

            # ... resto do código de validação
```

**Uso:**
```python
# Modo normal (sem logs de payload)
async with AsyncSicoob(client_id="...") as client:
    await client.cobranca.boleto.emitir_boleto(dados)

# Modo debug (com logs de payload)
async with AsyncSicoob(client_id="...", enable_request_logging=True) as client:
    await client.cobranca.boleto.emitir_boleto(dados)
```

---

## 4. 🟡 IMPORTANTE: Melhorar Mensagens de Erro de Validação

### Problema Atual

**Arquivo:** `sicoob/async_boleto.py`
**Linhas:** 75-76

```python
except Exception as e:
    raise BoletoError(f'Erro ao emitir boleto: {e!s}') from e  # ❌ Genérico demais
```

**Impacto:**
- Mensagem "Erro ao emitir boleto: [400] HTTP 400" não ajuda em nada
- Desenvolvedor precisa debugar código da biblioteca para ver detalhes

### Solução Proposta

```python
except SicoobError as e:
    # Extrai mensagens estruturadas da API Sicoob
    error_details = e.get_error_details()

    if e.status_code == 400 and 'mensagens' in error_details:
        # Formata mensagens de validação de forma legível
        msgs = error_details['mensagens']

        if len(msgs) == 1:
            # Erro único - mensagem direta
            msg = msgs[0]
            campo = msg.get('campo', '')
            mensagem = msg.get('mensagem', 'Erro desconhecido')

            if campo:
                error_message = f"Validação falhou no campo '{campo}': {mensagem}"
            else:
                error_message = f"Validação falhou: {mensagem}"
        else:
            # Múltiplos erros - lista formatada
            formatted_msgs = '\n'.join([
                f"  • {msg.get('campo', 'campo desconhecido')}: {msg.get('mensagem', 'erro desconhecido')}"
                for msg in msgs
            ])
            error_message = f"Validação falhou em {len(msgs)} campos:\n{formatted_msgs}"

        raise BoletoError(
            error_message,
            response_body=e.response_body,
            status_code=e.status_code,
            response_headers=e.response_headers
        ) from e

    elif e.status_code == 404:
        nosso_numero = dados.get('nossoNumero', 'desconhecido')
        raise BoletoError(
            f"Boleto não encontrado (nossoNumero={nosso_numero}). "
            f"Verifique se o boleto existe ou se os dados estão corretos.",
            response_body=e.response_body,
            status_code=e.status_code,
            response_headers=e.response_headers
        ) from e

    # Outros erros - mensagem genérica melhorada
    raise BoletoError(
        f'Erro ao emitir boleto (HTTP {e.status_code}): {e}',
        response_body=e.response_body,
        status_code=e.status_code,
        response_headers=e.response_headers
    ) from e

except Exception as e:
    # Erros não-HTTP (timeout, rede, etc)
    raise BoletoError(f'Erro ao emitir boleto: {e!s}') from e
```

**Exemplo de Mensagem Melhorada:**
```
Antes: "Erro ao emitir boleto: [400] HTTP 400"

Depois: "Validação falhou em 2 campos:
  • numeroCliente: Número do cliente é obrigatório
  • tipoJurosMora: Valor inválido. Valores aceitos: 1, 2, 3"
```

---

## 5. 🟢 MELHORIA: Modo Debug Global

### Problema Atual

Não há forma fácil de ativar logs verbosos sem modificar código.

### Solução Proposta

**Arquivo:** `sicoob/config.py`

```python
import os
import logging

class SicoobConfig:
    """Configuração global do SDK"""

    # Modo debug (ativa logs verbosos)
    DEBUG_MODE = os.getenv('SICOOB_DEBUG', 'false').lower() == 'true'

    # Logging de payloads completos (pode expor dados sensíveis)
    LOG_PAYLOADS = os.getenv('SICOOB_LOG_PAYLOADS', 'false').lower() == 'true'

    @classmethod
    def enable_debug(cls, log_payloads: bool = False):
        """
        Ativa modo debug com logs verbosos

        Args:
            log_payloads: Se True, loga payloads completos (use com cuidado)
        """
        cls.DEBUG_MODE = True
        cls.LOG_PAYLOADS = log_payloads

        # Configura logging da biblioteca para DEBUG
        logging.getLogger('sicoob').setLevel(logging.DEBUG)

    @classmethod
    def disable_debug(cls):
        """Desativa modo debug"""
        cls.DEBUG_MODE = False
        cls.LOG_PAYLOADS = False
        logging.getLogger('sicoob').setLevel(logging.INFO)
```

**Uso:**
```python
from sicoob.config import SicoobConfig

# Opção 1: Via código
SicoobConfig.enable_debug(log_payloads=True)

# Opção 2: Via variável de ambiente
# export SICOOB_DEBUG=true
# export SICOOB_LOG_PAYLOADS=true
# python seu_script.py
```

---

## 6. 🟢 MELHORIA: Adicionar Context Manager para Debug

### Solução Proposta

**Arquivo:** `sicoob/debug.py` (novo)

```python
from contextlib import contextmanager
import logging
from sicoob.config import SicoobConfig

@contextmanager
def debug_mode(log_payloads: bool = False):
    """
    Context manager para ativar debug temporariamente

    Usage:
        with debug_mode(log_payloads=True):
            resultado = sicoob.cobranca.boleto.emitir_boleto(dados)
    """
    # Salva estado anterior
    original_debug = SicoobConfig.DEBUG_MODE
    original_payloads = SicoobConfig.LOG_PAYLOADS

    try:
        # Ativa debug
        SicoobConfig.enable_debug(log_payloads=log_payloads)
        yield
    finally:
        # Restaura estado anterior
        SicoobConfig.DEBUG_MODE = original_debug
        SicoobConfig.LOG_PAYLOADS = original_payloads
```

---

## 7. 🟢 MELHORIA: CLI para Testar Endpoints

### Solução Proposta

**Arquivo:** `sicoob/cli.py` (novo)

```python
"""
CLI para debugging da API Sicoob

Usage:
    python -m sicoob.cli emitir-boleto --payload payload.json --debug
    python -m sicoob.cli consultar-boleto --nosso-numero 123 --debug
"""

import click
import json
import asyncio
from sicoob import AsyncSicoob
from sicoob.config import SicoobConfig

@click.group()
def cli():
    """CLI de debugging para sicoob-sdk"""
    pass

@cli.command()
@click.option('--payload', type=click.File('r'), required=True, help='Arquivo JSON com dados do boleto')
@click.option('--client-id', envvar='SICOOB_CLIENT_ID', required=True)
@click.option('--cert', envvar='SICOOB_CERT_PATH', required=True)
@click.option('--debug/--no-debug', default=False)
async def emitir_boleto(payload, client_id, cert, debug):
    """Emite um boleto via API"""
    if debug:
        SicoobConfig.enable_debug(log_payloads=True)

    dados = json.load(payload)

    async with AsyncSicoob(client_id=client_id, certificado_pfx=cert) as client:
        resultado = await client.cobranca.boleto.emitir_boleto(dados)
        click.echo(json.dumps(resultado, indent=2))

if __name__ == '__main__':
    cli()
```

---

## Priorização e Roadmap Sugerido

### Sprint 1 (Crítico) - 1-2 dias
- [ ] Item 1: Preservar response body em exceções
- [ ] Item 2: Enriquecer classes de exceção

### Sprint 2 (Importante) - 2-3 dias
- [ ] Item 3: Logger estruturado
- [ ] Item 4: Melhorar mensagens de erro

### Sprint 3 (Melhorias) - 1-2 dias
- [ ] Item 5: Modo debug global
- [ ] Item 6: Context manager para debug
- [ ] Item 7: CLI para testes

---

## Benefícios Esperados

1. **Redução de 80% no tempo de debugging** de erros de validação
2. **Mensagens de erro claras** que indicam exatamente o problema
3. **Logs estruturados** facilitam troubleshooting em produção
4. **Melhor DX (Developer Experience)** para usuários da biblioteca
5. **Facilita contribuições** open-source com melhor visibilidade

---

## Referências

- Documentação API Sicoob: https://developers.sicoob.com.br
- Issue relacionado: [Link para issue quando criado]
- Casos de uso real que motivaram estas sugestões: Implementação de emissão em lote de boletos com retry automático

---

**Autor:** Fábio Thomaz / Ladder Tecnologia
**Data:** 2025-11-07
**Versão sicoob-sdk:** 0.2.1
