#!/bin/bash
"""Script de CI para coverage automatizado"""

set -e  # Para na primeira falha

echo "🚀 Iniciando pipeline de testes e coverage..."

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Verifica se está em ambiente CI
if [[ "${CI:-false}" == "true" ]]; then
    log "Executando em ambiente CI"
    CI_MODE=true
else
    log "Executando em ambiente local"
    CI_MODE=false
fi

# Instala dependências
log "Instalando dependências..."
if command -v uv &> /dev/null; then
    uv sync --dev
else
    pip install -e ".[dev]"
fi

# Executa linting
log "Executando linting..."
uv run ruff check sicoob/ || {
    error "Linting falhou!"
    exit 1
}

uv run ruff format sicoob/ --check || {
    warning "Formatação precisa ser corrigida"
    if [[ "$CI_MODE" == "true" ]]; then
        exit 1
    fi
}

# Executa testes unitários com coverage
log "Executando testes unitários..."
uv run pytest \
    -m "not integration and not slow" \
    --cov=sicoob \
    --cov-branch \
    --cov-report=term-missing \
    --cov-report=xml \
    --cov-report=html \
    --junit-xml=junit.xml \
    --cov-fail-under=80 || {
    error "Testes unitários falharam!"
    exit 1
}

# Se não estiver no CI, executa testes de integração
if [[ "$CI_MODE" == "false" ]]; then
    log "Executando testes de integração (somente local)..."
    uv run pytest \
        -m "integration" \
        --cov=sicoob \
        --cov-append \
        --cov-report=term-missing \
        --cov-report=xml \
        --cov-report=html \
        --junit-xml=junit-integration.xml || {
        warning "Alguns testes de integração falharam (pode ser esperado)"
    }
fi

# Analisa cobertura e gera relatório
log "Analisando cobertura..."
coverage report --format=markdown > coverage-report.md
coverage json

# Extrai estatísticas de cobertura
TOTAL_COVERAGE=$(python3 -c "
import json
with open('coverage.json') as f:
    data = json.load(f)
    print(f'{data[\"totals\"][\"percent_covered\"]:.2f}')
")

log "Coverage total: ${TOTAL_COVERAGE}%"

# Verifica se coverage atende aos requisitos
if (( $(echo "$TOTAL_COVERAGE < 80" | bc -l) )); then
    error "Coverage abaixo do mínimo (80%): ${TOTAL_COVERAGE}%"
    if [[ "$CI_MODE" == "true" ]]; then
        exit 1
    fi
else
    log "Coverage adequado: ${TOTAL_COVERAGE}%"
fi

# Encontra arquivos com baixa cobertura
log "Identificando arquivos com baixa cobertura..."
python3 -c "
import json
with open('coverage.json') as f:
    data = json.load(f)
    low_coverage = []
    for file, stats in data['files'].items():
        if stats['summary']['percent_covered'] < 75 and not file.endswith('__init__.py'):
            low_coverage.append((file, stats['summary']['percent_covered']))
    
    if low_coverage:
        print('⚠️  Arquivos com cobertura < 75%:')
        for file, coverage in sorted(low_coverage, key=lambda x: x[1]):
            print(f'   {file}: {coverage:.1f}%')
    else:
        print('✅ Todos os arquivos têm cobertura adequada!')
"

# Gera badge de coverage (se em CI)
if [[ "$CI_MODE" == "true" ]] && command -v genbadge &> /dev/null; then
    log "Gerando badge de coverage..."
    genbadge coverage -i coverage.xml -o coverage-badge.svg
fi

# Relatório final
log "📋 Resumo da execução:"
echo "   • Linting: ✅"
echo "   • Testes unitários: ✅" 
if [[ "$CI_MODE" == "false" ]]; then
    echo "   • Testes integração: ⚠️ (local)"
fi
echo "   • Coverage total: ${TOTAL_COVERAGE}%"
echo "   • Relatórios gerados:"
echo "     - HTML: htmlcov/index.html"
echo "     - XML: coverage.xml"
echo "     - JSON: coverage.json"
echo "     - Markdown: coverage-report.md"

# Se estiver em ambiente local, oferece abrir relatórios
if [[ "$CI_MODE" == "false" ]]; then
    echo ""
    echo "💡 Para ver relatório HTML: open htmlcov/index.html"
    echo "💡 Para ver detalhes: coverage report --show-missing"
    echo "💡 Para coverage por linha: coverage annotate sicoob/arquivo.py"
fi

log "✅ Pipeline de testes concluído com sucesso!"