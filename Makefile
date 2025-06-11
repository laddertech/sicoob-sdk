.PHONY: help build test publish bump-patch bump-minor bump-major

help:
	python help.py

## @ Gerenciamento de Pacote Python

build: ## Build do pacote
	python -m build

test: ## Executar testes
	pytest tests/

publish: build ## Publicar no PyPI (requer TWINE_USERNAME e TWINE_PASSWORD)
	twine upload dist/*

clean: ## Limpar builds anteriores
	rm -rf dist/ build/ *.egg-info/

## @ Atualiza versão do pacote

bump-patch: ## Incrementar versão (patch)
	python scripts/bump_version.py patch

bump-minor: ## Incrementar versão (minor)
	python scripts/bump_version.py minor

bump-major: ## Incrementar versão (major)
	python scripts/bump_version.py major

## @ Verifica e formata código

lint: ## Verificar estilo de código
	ruff check .

format: ## Formatar código
	ruff format .

fix: ## Corrigir problemas de estilo de código
	lint format
