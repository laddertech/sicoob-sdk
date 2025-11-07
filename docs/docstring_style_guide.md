# Guia de Estilo para Docstrings - Sicoob SDK

Este documento define o padrão de documentação para o Sicoob SDK.

## Estilo Adotado: Google Style

Usamos o Google Style para docstrings, compatível com Sphinx autodoc.

## Estrutura Padrão

```python
def exemplo_metodo(param1: str, param2: int = 10) -> Dict[str, Any]:
    """Descrição breve do que o método faz em uma linha.
    
    Descrição mais detalhada se necessário, explicando o comportamento,
    casos especiais ou considerações importantes.
    
    Args:
        param1: Descrição do primeiro parâmetro
        param2: Descrição do segundo parâmetro (default: 10)
        
    Returns:
        Dicionário com dados retornados contendo:
            - key1 (str): Descrição da chave
            - key2 (int): Descrição da outra chave
            
    Raises:
        ValidationError: Quando dados de entrada são inválidos
        APIError: Quando a API retorna erro
        
    Example:
        >>> resultado = exemplo_metodo("teste", 20)
        >>> print(resultado['key1'])
        'valor'
        
    Note:
        Informações adicionais importantes sobre o método.
        
    Warning:
        Avisos sobre uso inadequado ou limitações.
    """
    pass
```

## Elementos Obrigatórios

### 1. Descrição Breve
- Uma linha explicando o que o método faz
- Inicia com verbo no presente ("Obtém", "Cria", "Valida")
- Termina com ponto final

### 2. Args (se aplicável)
- Lista todos os parâmetros
- Formato: `nome: Descrição`
- Indica valores padrão quando relevante
- Use type hints no código, não na docstring

### 3. Returns (se aplicável)
- Descreve o que é retornado
- Para estruturas complexas, detalhe as chaves/campos
- Use type hints no código

### 4. Raises (se aplicável)
- Lista exceções que podem ser levantadas
- Explica quando cada exceção ocorre

## Elementos Opcionais

### Example
```python
Example:
    >>> cliente = Sicoob(client_id="123")
    >>> boleto = cliente.boleto.emitir_boleto(dados)
    >>> print(boleto['nossoNumero'])
    '123456789'
```

### Note
```python
Note:
    Este método requer autenticação OAuth2.
    Para ambiente sandbox, use sandbox_mode=True.
```

### Warning
```python
Warning:
    Este método pode ser removido em versões futuras.
    Use criar_cobranca_v2() em seu lugar.
```

## Padrões Específicos

### Classes
```python
class ExemploAPI:
    """API para operações de exemplo do Sicoob.
    
    Esta classe fornece acesso às funcionalidades de exemplo,
    incluindo criação, consulta e alteração de recursos.
    
    Attributes:
        base_path: Caminho base da API
        session: Sessão HTTP configurada
        
    Example:
        >>> api = ExemploAPI(oauth_client, session)
        >>> resultado = api.criar_exemplo(dados)
    """
```

### Módulos
```python
"""Módulo de validação de dados para o Sicoob SDK.

Este módulo fornece classes e funções para validar dados de entrada
nas APIs do Sicoob, prevenindo erros de runtime e garantindo
conformidade com os schemas esperados.

Classes:
    ValidationError: Exceção para erros de validação
    FieldValidator: Validador para campos individuais
    DataValidator: Validador para estruturas completas
    
Functions:
    validate_cpf: Valida CPF
    validate_cnpj: Valida CNPJ
    validate_email: Valida endereços de email
    
Example:
    >>> from sicoob.validation import validate_cpf
    >>> cpf = validate_cpf('111.444.777-35')
    >>> print(cpf)
    '11144477735'
"""
```

### Constantes
```python
#: URL base da API de produção do Sicoob
PRODUCTION_URL = "https://api.sicoob.com.br"

#: URL base da API de sandbox do Sicoob  
SANDBOX_URL = "https://sandbox.sicoob.com.br"

#: Escopos OAuth2 disponíveis para autenticação
OAUTH_SCOPES = {
    'boletos': 'boletos_inclusao boletos_consulta boletos_alteracao',
    'pix': 'cob.write cob.read cobv.write cobv.read',
    'conta': 'cco_consulta cco_transferencias'
}
```

## Regras de Qualidade

### ✅ Boas Práticas
- Use linguagem clara e objetiva
- Mantenha consistência de terminologia
- Inclua exemplos para APIs complexas
- Documente comportamentos especiais
- Use imperativos ("Cria", "Obtém", não "Criando")

### ❌ Evitar
- Docstrings vagas ("Faz alguma coisa")
- Repetir o nome da função na descrição
- Documentar parâmetros óbvios sem contexto
- Usar terminologia técnica sem explicação
- Docstrings desatualizadas

## Ferramentas

### Validação
```bash
# Verificar docstrings com pydocstyle
uv run pydocstyle sicoob/

# Verificar com interrogate
uv run interrogate sicoob/
```

### Geração
```bash
# Gerar documentação com Sphinx
make docs

# Servir documentação localmente
make docs-serve
```

## Checklist de Revisão

- [ ] Descrição breve clara e precisa
- [ ] Todos os parâmetros documentados em Args
- [ ] Tipo de retorno documentado em Returns  
- [ ] Exceções documentadas em Raises
- [ ] Exemplo incluído se método for complexo
- [ ] Type hints no código
- [ ] Consistente com outros métodos similares
- [ ] Sem erros de português ou digitação
