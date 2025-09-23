.PHONY: help build test publish bump-patch bump-minor bump-major

help:
	python help.py

## @ Gerenciamento de Pacote Python

build: ## Build do pacote
	python -m build

test: ## Executar todos os testes
	uv run pytest tests/

test-unit: ## Executar apenas testes unitários
	uv run pytest -m "unit or not integration" tests/

test-integration: ## Executar apenas testes de integração
	uv run pytest -m "integration" tests/

test-fast: ## Executar testes excluindo os lentos
	uv run pytest -m "not slow" tests/

publish: build ## Publicar no PyPI (requer TWINE_USERNAME e TWINE_PASSWORD)
	twine upload dist/*

clean: ## Limpar builds anteriores
	rm -rf dist/ build/ *.egg-info/

## @ Atualiza versão do pacote

bump-patch: ## Incrementar versão (patch)
	uv run python scripts/release.py patch

bump-minor: ## Incrementar versão (minor)
	uv run python scripts/release.py minor

bump-major: ## Incrementar versão (major)
	uv run python scripts/release.py major

release-patch: ## Preparar release patch completo (testes + versão + commit + tag)
	make format && uv run python scripts/release.py patch --skip-tests && git add -A && git commit -m "chore: :bookmark: Release $$(uv run python scripts/release.py --current | cut -d' ' -f3)" && git tag v$$(uv run python scripts/release.py --current | cut -d' ' -f3)

release-minor: ## Preparar release minor completo (testes + versão + commit + tag)
	make format && uv run python scripts/release.py minor --skip-tests && git add -A && git commit -m "chore: :bookmark: Release $$(uv run python scripts/release.py --current | cut -d' ' -f3)" && git tag v$$(uv run python scripts/release.py --current | cut -d' ' -f3)

release-major: ## Preparar release major completo (testes + versão + commit + tag)
	make format && uv run python scripts/release.py major --skip-tests && git add -A && git commit -m "chore: :bookmark: Release $$(uv run python scripts/release.py --current | cut -d' ' -f3)" && git tag v$$(uv run python scripts/release.py --current | cut -d' ' -f3)

release-push: ## Fazer push do commit e tag da release
	git push origin master --tags

## @ Verifica e formata código

lint: ## Verificar estilo de código
	ruff check .

format: ## Formatar código
	ruff format .

fix: ## Corrigir problemas de estilo de código
	make lint format

## @ Coverage e Relatórios de Teste

coverage: ## Executar testes com coverage completo
	uv run python scripts/test_coverage.py --html --xml --json

coverage-unit: ## Coverage apenas para testes unitários
	uv run python scripts/test_coverage.py --unit --html

coverage-fast: ## Coverage excluindo testes lentos
	uv run python scripts/test_coverage.py --fast --html

coverage-report: ## Mostrar relatório de coverage no terminal
	uv run coverage report --show-missing

coverage-html: ## Gerar e abrir relatório HTML
	uv run python scripts/test_coverage.py --html --open-html

coverage-ci: ## Pipeline de CI completo
	./scripts/ci_coverage.sh

## @ Documentação

docs: ## Construir documentação HTML
	uv run sphinx-build -b html docs docs/_build/html

docs-clean: ## Limpar build da documentação
	rm -rf docs/_build

docs-serve: ## Servir documentação localmente
	cd docs/_build/html && python -m http.server 8000

docs-rebuild: docs-clean docs ## Rebuild completo da documentação
