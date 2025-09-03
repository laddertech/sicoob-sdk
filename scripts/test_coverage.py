#!/usr/bin/env python3
"""Script para executar testes com coverage e gerar relatórios"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Executa comando e trata erros"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} concluído")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} falhou:")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Executar testes com coverage')
    parser.add_argument('--unit', action='store_true', help='Executar apenas testes unitários')
    parser.add_argument('--integration', action='store_true', help='Executar apenas testes de integração')
    parser.add_argument('--fast', action='store_true', help='Pular testes lentos')
    parser.add_argument('--min-coverage', type=int, default=80, help='Coverage mínimo (default: 80)')
    parser.add_argument('--html', action='store_true', help='Gerar relatório HTML')
    parser.add_argument('--xml', action='store_true', help='Gerar relatório XML')
    parser.add_argument('--json', action='store_true', help='Gerar relatório JSON')
    parser.add_argument('--open-html', action='store_true', help='Abrir relatório HTML no browser')
    
    args = parser.parse_args()
    
    # Constrói comando pytest
    pytest_cmd = ['uv', 'run', 'pytest']
    
    # Adiciona filtros de teste
    if args.unit:
        pytest_cmd.extend(['-m', 'unit'])
    elif args.integration:
        pytest_cmd.extend(['-m', 'integration'])
    elif args.fast:
        pytest_cmd.extend(['-m', 'not slow'])
    
    # Configurações de coverage
    pytest_cmd.extend([
        '--cov=sicoob',
        '--cov-branch',
        '--cov-report=term-missing',
        f'--cov-fail-under={args.min_coverage}'
    ])
    
    # Adiciona relatórios específicos
    if args.html:
        pytest_cmd.append('--cov-report=html')
    if args.xml:
        pytest_cmd.append('--cov-report=xml')
    if args.json:
        pytest_cmd.append('--cov-report=json')
    
    # Executa testes
    cmd = ' '.join(pytest_cmd)
    output = run_command(cmd, "Executando testes com coverage")
    
    if output is None:
        print("\n❌ Testes falharam!")
        sys.exit(1)
    
    # Exibe estatísticas de coverage
    print("\n📊 Estatísticas de Coverage:")
    lines = output.split('\n')
    for line in lines:
        if 'TOTAL' in line and '%' in line:
            print(f"   {line}")
    
    # Abre relatório HTML se solicitado
    if args.open_html and args.html:
        import webbrowser
        html_file = Path('htmlcov/index.html')
        if html_file.exists():
            webbrowser.open(html_file.as_uri())
            print(f"🌐 Relatório HTML aberto no browser")
    
    # Exibe dicas finais
    print("\n💡 Dicas:")
    if args.html:
        print("   - Relatório HTML: htmlcov/index.html")
    if args.xml:
        print("   - Relatório XML: coverage.xml")
    if args.json:
        print("   - Relatório JSON: coverage.json")
    
    print("   - Para ver arquivos com baixa cobertura: coverage report --show-missing")
    print("   - Para executar apenas testes rápidos: python scripts/test_coverage.py --fast")
    print("   - Para ver detalhes de uma linha: coverage annotate sicoob/modulo.py")


if __name__ == '__main__':
    main()