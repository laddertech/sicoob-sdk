.PHONY: build test publish

# Build do pacote
build:
	python -m build

# Executar testes
test:
	pytest tests/

# Publicar no PyPI (requer TWINE_USERNAME e TWINE_PASSWORD)
publish: build
	twine upload dist/*

# Limpar builds anteriores
clean:
	rm -rf dist/ build/ *.egg-info/
