# ⚡ Instalação Rápida do Pre-commit

## Instalação em 3 passos

### 1. Instalar pre-commit
```bash
pip install pre-commit
# ou
uv pip install pre-commit
```

### 2. Ativar hooks no repositório
```bash
cd /caminho/para/sicoob-sdk
pre-commit install
```

**Saída esperada:**
```
pre-commit installed at .git/hooks/pre-commit
```

### 3. Testar
```bash
# Rodar em todos os arquivos (primeira vez)
pre-commit run --all-files
```

**Saída esperada:**
```
ruff.....................................Passed
ruff-format..............................Passed
trailing-whitespace......................Passed
end-of-file-fixer........................Passed
check-yaml...............................Passed
check-toml...............................Passed
check-added-large-files..................Passed
check-merge-conflict.....................Passed
detect-private-key.......................Passed
no-commit-to-branch......................Passed
```

## Pronto! 🎉

Agora o pre-commit vai rodar automaticamente em cada `git commit`, verificando:
- ✅ Linting com ruff (mesmas regras do GitHub Actions)
- ✅ Formatação de código
- ✅ Imports organizados
- ✅ Espaços em branco
- ✅ Sintaxe YAML/TOML
- ✅ Previne commits em main/master
- ✅ Detecta chaves privadas

## Exemplo de uso

```bash
# 1. Faz alterações no código
vim sicoob/async_client.py

# 2. Adiciona arquivos
git add sicoob/async_client.py

# 3. Commit (pre-commit roda automaticamente)
git commit -m "fix: corrigir bug"

# Pre-commit roda automaticamente:
# ruff.....................................Passed
# ruff-format..............................Passed
# ...
# [main abc1234] fix: corrigir bug
```

Se houver erros, eles são **corrigidos automaticamente**:

```bash
git commit -m "fix: teste"

# ruff.....................................Failed
# - hook id: ruff
# - Files were modified by this hook. Additional output:
#
# sicoob/__init__.py:3:1: I001 Import block is un-sorted
# Found 1 error (1 fixed, 0 remaining).

# Arquivos corrigidos! Basta adicionar novamente:
git add sicoob/__init__.py
git commit -m "fix: teste"
# [main def5678] fix: teste
```

## Documentação Completa

Para mais detalhes, troubleshooting e configurações avançadas:

```bash
cat docs/PRE_COMMIT_SETUP.md
```

## Desinstalar (se necessário)

```bash
pre-commit uninstall
```

---

**Tempo de instalação:** ~30 segundos
**Tempo economizado:** Horas de espera em CI falhando 🚀
