# Configuração do Pre-commit

Este documento explica como configurar e usar o pre-commit para evitar commits com problemas de linting.

## O que é Pre-commit?

O pre-commit é uma ferramenta que executa verificações automáticas **antes de fazer commit**, evitando que código com problemas chegue ao GitHub Actions.

**Benefícios:**
- ✅ Detecta erros de linting ANTES do commit
- ✅ Corrige automaticamente problemas quando possível
- ✅ Economiza tempo (não precisa esperar CI falhar)
- ✅ Evita commits de correção desnecessários

## Instalação

### 1. Instalar o pre-commit

```bash
# Via pip
pip install pre-commit

# Ou via uv (recomendado)
uv pip install pre-commit
```

### 2. Instalar os hooks no repositório

```bash
# Na raiz do projeto sicoob-sdk
pre-commit install

# Saída esperada:
# pre-commit installed at .git/hooks/pre-commit
```

Pronto! Agora o pre-commit vai rodar automaticamente em cada `git commit`.

## Uso

### Automático (recomendado)

Após instalar, o pre-commit roda automaticamente:

```bash
git add sicoob/async_client.py
git commit -m "fix: corrigir bug"

# Pre-commit roda automaticamente:
# ruff check................................Passed
# ruff format...............................Passed
# trailing-whitespace.......................Passed
# end-of-file-fixer.........................Passed
# [master abc1234] fix: corrigir bug
```

Se houver problemas, o commit é **bloqueado**:

```bash
git commit -m "fix: teste"

# ruff check................................Failed
# - hook id: ruff
# - exit code: 1
#
# sicoob/__init__.py:3:1: I001 [*] Import block is un-sorted
# Found 1 error (1 fixed, 0 remaining).
#
# Arquivos corrigidos automaticamente!
# Faça git add novamente e commit:
```

### Manual

Para rodar as verificações manualmente sem fazer commit:

```bash
# Rodar em todos os arquivos
pre-commit run --all-files

# Rodar apenas em arquivos modificados
pre-commit run

# Rodar apenas o ruff
pre-commit run ruff --all-files

# Rodar apenas o formatter
pre-commit run ruff-format --all-files
```

## Hooks Configurados

### 1. Ruff (Linting)

**O que faz:** Mesma verificação que o GitHub Actions
- Verifica estilo de código
- Detecta imports não ordenados
- Detecta código não usado
- Detecta problemas de segurança
- **Corrige automaticamente quando possível** (`--fix`)

**Exemplo:**
```bash
# Antes do commit
sicoob/__init__.py:3:1: I001 Import block is un-sorted
Found 1 error (1 fixed, 0 remaining).

# Arquivo corrigido automaticamente!
# Basta fazer git add novamente
```

### 2. Ruff Format (Formatação)

**O que faz:** Formata código automaticamente
- Indentação consistente
- Aspas simples (conforme configuração)
- Line breaks apropriados
- 88 caracteres por linha

### 3. Verificações Básicas

- **trailing-whitespace:** Remove espaços no final das linhas
- **end-of-file-fixer:** Garante newline no final dos arquivos
- **check-yaml:** Valida sintaxe YAML
- **check-toml:** Valida sintaxe TOML (pyproject.toml)
- **check-added-large-files:** Detecta arquivos >500KB
- **check-merge-conflict:** Detecta markers de merge conflict
- **detect-private-key:** Detecta chaves privadas acidentalmente commitadas
- **no-commit-to-branch:** Previne commits diretos em main/master

## Pular Verificações (use com cuidado!)

Se REALMENTE precisar pular as verificações (não recomendado):

```bash
# Pula todas as verificações do pre-commit
git commit -m "fix: urgente" --no-verify

# Ou use SKIP para hooks específicos
SKIP=ruff git commit -m "fix: teste"
```

**⚠️ Atenção:** Isso pode fazer o CI falhar no GitHub Actions!

## Atualizar Hooks

Para atualizar os hooks para as versões mais recentes:

```bash
pre-commit autoupdate

# Saída:
# Updating https://github.com/astral-sh/ruff-pre-commit ... updating v0.4.2 -> v0.5.0.
```

## Desinstalar

Se quiser desinstalar o pre-commit:

```bash
pre-commit uninstall

# Saída:
# pre-commit uninstalled
```

## Troubleshooting

### Problema: pre-commit muito lento

**Solução 1:** Desabilite o pytest (já vem desabilitado por padrão)

O hook do pytest está comentado em `.pre-commit-config.yaml` por ser lento.

**Solução 2:** Use cache

```bash
# Pre-commit usa cache automaticamente
# Primeira execução: ~5s
# Execuções seguintes: ~0.5s
```

### Problema: Hook falha mas arquivo não foi corrigido

**Causa:** Alguns erros não podem ser corrigidos automaticamente

**Solução:** Leia a mensagem de erro e corrija manualmente

```bash
# Exemplo de erro que requer correção manual:
sicoob/client.py:45:1: F401 'os' imported but unused

# Corrija manualmente: remova o import não usado
# Depois: git add e git commit novamente
```

### Problema: Conflito entre pre-commit e editor/IDE

**Solução:** Configure seu editor para usar ruff também

**VS Code:**
```json
{
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "ruff",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

**PyCharm:**
1. Settings → Tools → External Tools
2. Add: Name=ruff, Program=ruff, Arguments=check $FilePath$ --fix

## Integração com CI/CD

O pre-commit **complementa** o GitHub Actions, não substitui:

- **Pre-commit (local):** Primeira linha de defesa, rápido feedback
- **GitHub Actions (CI):** Verificação final antes de merge

Mesmo com pre-commit, o CI ainda roda para garantir que:
1. Ninguém usou `--no-verify`
2. Testes passam
3. Código funciona em ambiente limpo

## Comandos Úteis

```bash
# Rodar em todos os arquivos
pre-commit run --all-files

# Rodar apenas em arquivos staged
pre-commit run

# Ver quais hooks estão instalados
pre-commit run --all-files --verbose

# Limpar cache do pre-commit
pre-commit clean

# Ver versão
pre-commit --version
```

## Recomendações

### Para desenvolvedores individuais:
```bash
# Instale e ative
pre-commit install
```

### Para times:
```bash
# Adicione ao README.md
# Adicione ao processo de onboarding
# Mencione em pull request template
```

### Para CI/CD:
```bash
# GitHub Actions continua rodando os mesmos checks
# Mas agora pega menos erros pois pre-commit já pegou localmente
```

## FAQ

**P: O pre-commit torna o commit mais lento?**
R: Primeira vez: sim (~5s). Depois usa cache (~0.5s).

**P: Posso desabilitar hooks específicos?**
R: Sim, edite `.pre-commit-config.yaml` e comente o hook.

**P: O que acontece se eu usar --no-verify?**
R: O GitHub Actions vai pegar o erro e falhar.

**P: Posso usar pre-commit em outros projetos?**
R: Sim! Pre-commit é universal. Copie `.pre-commit-config.yaml` e adapte.

**P: Pre-commit funciona com Windows?**
R: Sim, funciona em Windows, Linux e macOS.

---

**Documentação oficial:** https://pre-commit.com/
**Ruff pre-commit:** https://github.com/astral-sh/ruff-pre-commit
