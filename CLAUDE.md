# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandos de Desenvolvimento

### Testes
```bash
make test          # Executar todos os testes com pytest
pytest tests/      # Executar testes diretamente
```

### Build e Publicação
```bash
make build         # Construir pacote Python
make publish       # Publicar no PyPI (requer TWINE_USERNAME e TWINE_PASSWORD)
make clean         # Limpar builds anteriores
```

### Verificação de Código
```bash
make lint          # Verificar estilo de código com ruff
make format        # Formatar código com ruff
ruff check .       # Verificar diretamente
ruff format .      # Formatar diretamente
```

### Versionamento
```bash
make bump-patch    # Incrementar patch version (0.1.2 → 0.1.3)
make bump-minor    # Incrementar minor version (0.1.2 → 0.2.0) 
make bump-major    # Incrementar major version (0.1.2 → 1.0.0)
```

### Instalação para Desenvolvimento
```bash
pip install -e ".[dev]"    # Instalar em modo desenvolvimento
```

## Arquitetura

### Cliente Principal
- **Sicoob** (`sicoob/client.py`): Classe principal que integra todos os serviços
  - Suporta autenticação via certificado PEM/key ou PFX
  - Modo sandbox configurável
  - Acesso às APIs de cobrança e conta corrente

### Autenticação OAuth2
- **OAuth2Client** (`sicoob/auth/oauth.py`): Gerencia tokens de acesso com cache por escopo
- Suporta certificados PEM/key e PFX
- Tokens são renovados automaticamente quando expiram

### APIs de Serviços
- **BoletoAPI** (`sicoob/boleto.py`): Operações de boletos bancários
- **ContaCorrenteAPI** (`sicoob/conta_corrente.py`): Extratos, saldos e transferências
- **PixAPI**: Implementado via **pypix-api** (SicoobPixAPICustom)
  - Cobranças PIX imediatas e com vencimento
  - Webhooks PIX
  - Lotes de cobrança

### Classe Base
- **APIClientBase** (`sicoob/api_client.py`): Funcionalidades comuns
  - Gerenciamento de URLs (sandbox/produção)
  - Headers de autenticação padronizados
  - Tratamento de erros HTTP

### Tratamento de Exceções
- **Hierarquia de exceções** (`sicoob/exceptions.py`):
  - `SicoobError`: Base para todas as exceções
  - `BoletoError`, `PixError`, `ContaCorrenteError`: Por domínio
  - Exceções específicas: `BoletoNaoEncontradoError`, `CobrancaPixNaoEncontradaError`, etc.

## Estrutura Modular

```
sicoob/
├── __init__.py           # Exports principais
├── client.py            # Cliente principal Sicoob
├── api_client.py        # Classe base para APIs
├── auth/
│   ├── __init__.py
│   └── oauth.py         # Cliente OAuth2
├── boleto.py           # API de boletos
├── conta_corrente.py   # API de conta corrente  
├── cobranca.py         # Agrupa boleto e PIX
├── exceptions.py       # Exceções customizadas
└── constants.py        # Constantes do sistema
```

## Configurações Específicas

### Ruff (Linting/Formatação)
- Line length: 88 caracteres
- Quote style: single quotes
- Configurado em `pyproject.toml`

### Versionamento Automático
- Script: `scripts/bump_version.py`
- Atualiza: `setup.py`, `pyproject.toml`, `sicoob/__init__.py`

### CI/CD
- Testes automáticos no GitHub Actions
- Deploy automático no PyPI em releases
- Pipeline em `.github/workflows/ci-cd.yml`

## Dependências Principais

- **requests**: HTTP client
- **python-dotenv**: Variáveis de ambiente
- **pypix-api**: API PIX integrada via SicoobPixAPICustom
- **requests-pkcs12**: Certificados PFX
- **pytest**: Framework de testes

## Padrões de Commit
Use conventional commits com emoji em português brasileiro:
- `feat: :sparkles: Nova funcionalidade`
- `fix: :bug: Correção de bug`
- `chore: :bookmark: Atualização de versão`
- `docs: :memo: Documentação`