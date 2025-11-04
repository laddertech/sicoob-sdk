"""Testes para módulo de validação."""

from datetime import datetime
from decimal import Decimal

import pytest

from sicoob.validation import (
    DataValidator,
    FieldValidator,
    MultipleValidationError,
    ValidationError,
    get_boleto_schema,
    get_pagador_schema,
    get_pix_cobranca_schema,
    get_webhook_schema,
    validate_cnpj,
    validate_cpf,
    validate_date_range,
    validate_email,
    validate_input,
    validate_monetary_value,
    validate_txid,
    validate_url,
)


class TestValidationError:
    """Testes para exceções de validação."""

    def test_validation_error_basic(self):
        """Testa criação básica da exceção."""
        error = ValidationError('Erro teste')
        assert str(error) == 'Erro teste'
        assert error.field is None
        assert error.value is None

    def test_validation_error_with_field(self):
        """Testa exceção com campo e valor."""
        error = ValidationError('Valor inválido', 'nome', 'teste')
        assert "Campo 'nome': Valor inválido" in str(error)
        assert error.field == 'nome'
        assert error.value == 'teste'

    def test_multiple_validation_error(self):
        """Testa múltiplas exceções de validação."""
        errors = [
            ValidationError('Erro 1', 'campo1'),
            ValidationError('Erro 2', 'campo2'),
        ]
        multi_error = MultipleValidationError(errors)
        assert 'Múltiplos erros de validação' in str(multi_error)
        assert len(multi_error.errors) == 2


class TestFieldValidator:
    """Testes para validador de campo."""

    def test_required_field_validation(self):
        """Testa validação de campo obrigatório."""
        validator = FieldValidator('nome', required=True)

        # Campo obrigatório vazio
        with pytest.raises(ValidationError, match='Campo obrigatório'):
            validator.validate(None)

        with pytest.raises(ValidationError, match='Campo obrigatório'):
            validator.validate('')

        # Campo obrigatório preenchido
        assert validator.validate('João') == 'João'

    def test_optional_field_validation(self):
        """Testa validação de campo opcional."""
        validator = FieldValidator('descricao', required=False)

        # Campo opcional pode ser None ou vazio
        assert validator.validate(None) is None
        assert validator.validate('') == ''
        assert validator.validate('Descrição') == 'Descrição'

    def test_data_type_validation(self):
        """Testa validação de tipo de dados."""
        # String
        validator = FieldValidator('nome', data_type=str)
        assert validator.validate('João') == 'João'
        assert validator.validate(123) == '123'  # Conversão automática

        # Inteiro
        validator = FieldValidator('idade', data_type=int)
        assert validator.validate(25) == 25
        assert validator.validate('25') == 25  # Conversão automática

        with pytest.raises(ValidationError, match='Deve ser do tipo int'):
            validator.validate('abc')

        # Float
        validator = FieldValidator('preco', data_type=float)
        assert validator.validate(10.5) == 10.5
        assert validator.validate('10.5') == 10.5

        with pytest.raises(ValidationError, match='Deve ser do tipo float'):
            validator.validate('abc')

    def test_numeric_range_validation(self):
        """Testa validação de faixas numéricas."""
        validator = FieldValidator('nota', min_value=0, max_value=10)

        # Valores válidos
        assert validator.validate(5) == 5
        assert validator.validate(0) == 0
        assert validator.validate(10) == 10

        # Valores inválidos
        with pytest.raises(ValidationError, match='Deve ser >= 0'):
            validator.validate(-1)

        with pytest.raises(ValidationError, match='Deve ser <= 10'):
            validator.validate(11)

    def test_string_length_validation(self):
        """Testa validação de comprimento de string."""
        validator = FieldValidator('senha', min_length=6, max_length=20)

        # Comprimentos válidos
        assert validator.validate('123456') == '123456'
        assert validator.validate('a' * 20) == 'a' * 20

        # Comprimentos inválidos
        with pytest.raises(ValidationError, match='pelo menos 6 caracteres'):
            validator.validate('12345')

        with pytest.raises(ValidationError, match='no máximo 20 caracteres'):
            validator.validate('a' * 21)

    def test_pattern_validation(self):
        """Testa validação de padrão regex."""
        validator = FieldValidator('cep', pattern=r'^\d{5}-\d{3}$')

        # Padrão válido
        assert validator.validate('12345-678') == '12345-678'

        # Padrão inválido
        with pytest.raises(ValidationError, match='Formato inválido'):
            validator.validate('12345678')

    def test_allowed_values_validation(self):
        """Testa validação de valores permitidos."""
        validator = FieldValidator(
            'status', allowed_values=['ativo', 'inativo', 'pendente']
        )

        # Valores válidos
        assert validator.validate('ativo') == 'ativo'
        assert validator.validate('inativo') == 'inativo'

        # Valor inválido
        with pytest.raises(ValidationError, match='Deve ser um dos valores'):
            validator.validate('cancelado')

    def test_custom_validator(self):
        """Testa validador customizado."""

        def validate_even(value):
            if value % 2 != 0:
                raise ValueError('Deve ser par')
            return value

        validator = FieldValidator('numero', custom_validator=validate_even)

        # Valor válido
        assert validator.validate(4) == 4

        # Valor inválido
        with pytest.raises(ValidationError, match='Validação customizada falhou'):
            validator.validate(3)


class TestDataValidator:
    """Testes para validador de dados."""

    def test_valid_data_validation(self):
        """Testa validação de dados válidos."""
        fields = [
            FieldValidator('nome', required=True, data_type=str),
            FieldValidator('idade', required=True, data_type=int, min_value=0),
            FieldValidator('email', required=False, data_type=str),
        ]
        validator = DataValidator('usuario', fields)

        data = {'nome': 'João', 'idade': 25, 'email': 'joao@email.com'}
        result = validator.validate(data)

        assert result['nome'] == 'João'
        assert result['idade'] == 25
        assert result['email'] == 'joao@email.com'

    def test_strict_mode_validation(self):
        """Testa modo strict que rejeita campos extras."""
        fields = [FieldValidator('nome', required=True)]
        validator = DataValidator('usuario', fields)

        data = {'nome': 'João', 'extra': 'valor'}

        # Modo strict (padrão) rejeita campo extra
        with pytest.raises(MultipleValidationError):
            validator.validate(data, strict=True)

        # Modo não-strict aceita campo extra
        result = validator.validate(data, strict=False)
        assert result['nome'] == 'João'
        assert result['extra'] == 'valor'

    def test_multiple_validation_errors(self):
        """Testa coleta de múltiplos erros."""
        fields = [
            FieldValidator('nome', required=True),
            FieldValidator('idade', required=True, data_type=int, min_value=0),
        ]
        validator = DataValidator('usuario', fields)

        data = {'nome': '', 'idade': -5}

        with pytest.raises(MultipleValidationError) as exc_info:
            validator.validate(data)

        errors = exc_info.value.errors
        assert len(errors) >= 2  # Pelo menos nome vazio e idade negativa

    def test_non_dict_data(self):
        """Testa validação de dados que não são dicionário."""
        fields = [FieldValidator('nome', required=True)]
        validator = DataValidator('usuario', fields)

        with pytest.raises(ValidationError, match='Dados devem ser um dicionário'):
            validator.validate('não é dict')


class TestCustomValidators:
    """Testes para validadores customizados."""

    def test_validate_cpf(self):
        """Testa validador de CPF."""
        # CPF válido
        assert validate_cpf('11144477735') == '11144477735'
        assert validate_cpf('111.444.777-35') == '11144477735'  # Remove formatação

        # CPF inválido - tamanho
        with pytest.raises(ValueError, match='CPF deve ter 11 dígitos'):
            validate_cpf('123456789')

        # CPF inválido - sequência
        with pytest.raises(ValueError, match='CPF inválido \\(sequência\\)'):
            validate_cpf('11111111111')

        # CPF inválido - dígitos verificadores
        with pytest.raises(ValueError, match='CPF inválido'):
            validate_cpf('12345678901')

    def test_validate_cnpj(self):
        """Testa validador de CNPJ."""
        # CNPJ válido
        assert validate_cnpj('11222333000181') == '11222333000181'
        assert validate_cnpj('11.222.333/0001-81') == '11222333000181'

        # CNPJ inválido - tamanho
        with pytest.raises(ValueError, match='CNPJ deve ter 14 dígitos'):
            validate_cnpj('123456789')

        # CNPJ inválido - sequência
        with pytest.raises(ValueError, match='CNPJ inválido \\(sequência\\)'):
            validate_cnpj('11111111111111')

        # CNPJ inválido - dígitos verificadores
        with pytest.raises(ValueError, match='CNPJ inválido'):
            validate_cnpj('12345678000123')

    def test_validate_email(self):
        """Testa validador de email."""
        # Email válido
        assert validate_email('test@example.com') == 'test@example.com'
        assert validate_email('User@Example.COM') == 'user@example.com'  # Normaliza

        # Email inválido
        with pytest.raises(ValueError, match='Formato de email inválido'):
            validate_email('invalid-email')

        with pytest.raises(ValueError, match='Formato de email inválido'):
            validate_email('@example.com')

    def test_validate_url(self):
        """Testa validador de URL."""
        # URL válida
        assert validate_url('https://example.com') == 'https://example.com'
        assert (
            validate_url('http://sub.domain.com/path') == 'http://sub.domain.com/path'
        )

        # URL inválida
        with pytest.raises(ValueError, match='Formato de URL inválido'):
            validate_url('ftp://example.com')

        with pytest.raises(ValueError, match='Formato de URL inválido'):
            validate_url('not-a-url')

    def test_validate_txid(self):
        """Testa validador de TXID PIX."""
        # TXID válido
        valid_txid = 'a' * 26
        assert validate_txid(valid_txid) == valid_txid

        valid_txid = 'A1B2C3D4E5F6G7H8I9J0K1L2M3'
        assert validate_txid(valid_txid) == valid_txid

        # TXID inválido - tamanho
        with pytest.raises(ValueError, match='TXID deve ter entre 26 e 35 caracteres'):
            validate_txid('abc')

        with pytest.raises(ValueError, match='TXID deve ter entre 26 e 35 caracteres'):
            validate_txid('a' * 36)

        # TXID inválido - caracteres
        with pytest.raises(
            ValueError, match='TXID deve conter apenas caracteres alfanuméricos'
        ):
            validate_txid('a' * 25 + '@')

    def test_validate_monetary_value(self):
        """Testa validador de valor monetário."""
        # Valores válidos
        assert validate_monetary_value('100.50') == '100.50'
        assert validate_monetary_value('100,50') == '100.50'  # Normaliza vírgula
        assert validate_monetary_value(100.5) == '100.50'
        assert validate_monetary_value(Decimal('100.50')) == '100.50'

        # Valor negativo
        with pytest.raises(ValueError, match='Valor monetário inválido'):
            validate_monetary_value(-10)

        # Valor muito alto
        with pytest.raises(ValueError, match='Valor monetário inválido'):
            validate_monetary_value('1000000000')

        # Valor inválido
        with pytest.raises(ValueError, match='Valor monetário inválido'):
            validate_monetary_value('abc')

    def test_validate_date_range(self):
        """Testa validador de range de datas."""
        current_year = datetime.now().year

        # Range válido
        result = validate_date_range(12, 2023, 1, 15)
        assert result == (12, 2023, 1, 15)

        # Mês inválido
        with pytest.raises(ValueError, match='Mês deve estar entre 1 e 12'):
            validate_date_range(13, 2023, 1, 15)

        # Ano inválido
        with pytest.raises(ValueError, match='Ano deve estar entre'):
            validate_date_range(12, 1999, 1, 15)

        with pytest.raises(ValueError, match='Ano deve estar entre'):
            validate_date_range(12, current_year + 1, 1, 15)

        # Dia inválido
        with pytest.raises(ValueError, match='Dia inicial deve estar entre 1 e 31'):
            validate_date_range(12, 2023, 0, 15)

        # Range inválido (inicial > final)
        with pytest.raises(ValueError, match='Dia inicial não pode ser maior'):
            validate_date_range(12, 2023, 20, 10)

        # Data inexistente
        with pytest.raises(ValueError, match='Data inválida'):
            validate_date_range(2, 2023, 30, 31)  # Fevereiro não tem 30 dias


class TestSchemas:
    """Testes para schemas predefinidos."""

    def test_boleto_schema(self):
        """Testa schema de boleto."""
        schema = get_boleto_schema()

        valid_data = {
            'numeroCliente': 12345,
            'codigoModalidade': 1,
            'numeroContaCorrente': 67890,
            'codigoEspecieDocumento': 'DM',
            'dataEmissao': '2024-01-01',
            'dataVencimento': '2024-12-31',
            'valor': 100.00,
            'seuNumero': '123456789',
            'identificacaoEmissaoBoleto': 1,
            'identificacaoDistribuicaoBoleto': 1,
            'tipoDesconto': 0,
            'tipoMulta': 0,
            'tipoJurosMora': 3,
            'numeroParcela': 1,
            'pagador': {
                'numeroCpfCnpj': '11144477735',
                'nome': 'João Silva',
                'endereco': 'Rua Teste, 123',
                'bairro': 'Centro',
                'cidade': 'São Paulo',
                'cep': '01001000',
                'uf': 'SP',
            },
        }

        # Deve validar sem erro
        result = schema.validate(valid_data, strict=False)
        assert result['numeroCliente'] == 12345
        assert result['codigoModalidade'] == 1

        # Campo obrigatório faltando
        invalid_data = valid_data.copy()
        del invalid_data['numeroCliente']

        with pytest.raises(MultipleValidationError):
            schema.validate(invalid_data)

    def test_pix_cobranca_schema(self):
        """Testa schema de cobrança PIX."""
        schema = get_pix_cobranca_schema()

        valid_data = {
            'calendario': {'expiracao': 3600},
            'valor': {'original': '100.00'},
            'chave': 'user@example.com',
        }

        result = schema.validate(valid_data, strict=False)
        assert result['chave'] == 'user@example.com'

    def test_webhook_schema(self):
        """Testa schema de webhook."""
        schema = get_webhook_schema()

        valid_data = {'webhookUrl': 'https://example.com/webhook'}
        result = schema.validate(valid_data, strict=False)
        assert result['webhookUrl'] == 'https://example.com/webhook'

        # URL inválida
        invalid_data = {'webhookUrl': 'not-a-url'}
        with pytest.raises(MultipleValidationError):
            schema.validate(invalid_data)

    def test_pagador_schema(self):
        """Testa schema de pagador."""
        schema = get_pagador_schema()

        valid_data = {
            'numeroCpfCnpj': '11144477735',
            'nome': 'João Silva',
            'endereco': 'Rua Teste, 123',
            'bairro': 'Centro',
            'cidade': 'São Paulo',
            'cep': '01001000',
            'uf': 'SP',
        }

        result = schema.validate(valid_data, strict=False)
        assert result['nome'] == 'João Silva'
        assert result['numeroCpfCnpj'] == '11144477735'


class TestValidateInputDecorator:
    """Testa decorator de validação automática."""

    def test_validate_input_decorator(self):
        """Testa decorator de validação de entrada."""

        @validate_input('webhook', 'data')
        def create_webhook(self, data):
            return data

        # Dados válidos
        valid_data = {'webhookUrl': 'https://example.com/webhook'}
        result = create_webhook(None, valid_data)
        assert result['webhookUrl'] == 'https://example.com/webhook'

        # Schema inexistente (deve passar sem validação)
        @validate_input('inexistente', 'data')
        def dummy_func(self, data):
            return data

        result = dummy_func(None, {'any': 'data'})
        assert result == {'any': 'data'}
