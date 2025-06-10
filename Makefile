.PHONY: build test publish bump-patch bump-minor bump-major

# Build do pacote
build:
	python -m build

# Executar testes
test:
	pytest tests/

# Publicar no PyPI (requer TWINE_USERNAME e TWINE_PASSWORD)
publish: build
	twine upload dist/*

# Incrementar versão (patch, minor, major)
bump-patch:
	python scripts/bump_version.py patch

bump-minor:
	python scripts/bump_version.py minor

bump-major:
	python scripts/bump_version.py major

# Limpar builds anteriores
clean:
	rm -rf dist/ build/ *.egg-info/

# Verificação de estilo/lint
lint:
	ruff check .

# Formatação automática
format:
	ruff format .

# Verificar e corrigir automaticamente
fix: lint format
