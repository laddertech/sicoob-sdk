"""Testes para o sistema de validação de entrada"""

import pytest
from decimal import Decimal
from datetime import datetime

from sicoob.validation import (
    ValidationError,
    MultipleValidationError,
    FieldValidator,
    DataValidator,
    validate_cpf,
    validate_cnpj,
    validate_email,
    validate_url,
    validate_txid,
    validate_monetary_value,
    validate_date_range,
    get_boleto_schema,
    get_pix_cobranca_schema,
    get_webhook_schema,
    get_pagador_schema,
)


class TestFieldValidator:
    """Testes para FieldValidator"""

    def test_required_field_validation(self):
        """Testa validação de campo obrigatório"""
        validator = FieldValidator("test_field", required=True)
        
        # Campo vazio deve falhar
        with pytest.raises(ValidationError) as exc_info:
            validator.validate(None)
        assert "Campo obrigatório não pode estar vazio" in str(exc_info.value)
        assert exc_info.value.field == "test_field"
        
        # Campo com valor deve passar
        assert validator.validate("valor") == "valor"

    def test_optional_field_validation(self):
        """Testa validação de campo opcional"""
        validator = FieldValidator("test_field", required=False)
        
        # Campo vazio deve passar
        assert validator.validate(None) is None
        assert validator.validate("") == ""
        
        # Campo com valor deve passar
        assert validator.validate("valor") == "valor"

    def test_data_type_validation(self):
        """Testa validação de tipo de dados"""
        validator = FieldValidator("test_field", data_type=int)
        
        # Tipo correto deve passar
        assert validator.validate(42) == 42
        
        # Conversão automática deve funcionar
        assert validator.validate("42") == 42
        
        # Tipo incompatível deve falhar
        with pytest.raises(ValidationError) as exc_info:
            validator.validate("texto")
        assert "Deve ser do tipo int" in str(exc_info.value)

    def test_range_validation(self):
        """Testa validação de range numérico"""
        validator = FieldValidator("test_field", data_type=int, min_value=1, max_value=10)
        
        # Valores dentro do range devem passar
        assert validator.validate(5) == 5
        assert validator.validate(1) == 1
        assert validator.validate(10) == 10
        
        # Valores fora do range devem falhar
        with pytest.raises(ValidationError):
            validator.validate(0)
        
        with pytest.raises(ValidationError):
            validator.validate(11)

    def test_length_validation(self):
        """Testa validação de comprimento de string"""
        validator = FieldValidator("test_field", data_type=str, min_length=3, max_length=10)
        
        # Comprimentos válidos devem passar
        assert validator.validate("abc") == "abc"
        assert validator.validate("1234567890") == "1234567890"
        
        # Comprimentos inválidos devem falhar
        with pytest.raises(ValidationError):
            validator.validate("ab")
        
        with pytest.raises(ValidationError):
            validator.validate("12345678901")

    def test_pattern_validation(self):
        """Testa validação de padrão regex"""
        validator = FieldValidator("test_field", pattern=r'^\d{4}-\d{2}-\d{2}$')
        
        # Padrão válido deve passar
        assert validator.validate("2024-01-15") == "2024-01-15"
        
        # Padrão inválido deve falhar
        with pytest.raises(ValidationError):
            validator.validate("15/01/2024")

    def test_allowed_values_validation(self):
        """Testa validação de valores permitidos"""
        validator = FieldValidator("test_field", allowed_values=["A", "B", "C"])
        
        # Valores permitidos devem passar
        assert validator.validate("A") == "A"
        assert validator.validate("B") == "B"
        
        # Valores não permitidos devem falhar
        with pytest.raises(ValidationError):
            validator.validate("D")

    def test_custom_validator(self):
        """Testa validador customizado"""
        def uppercase_validator(value):
            return value.upper()
        
        validator = FieldValidator("test_field", custom_validator=uppercase_validator)
        
        # Validador customizado deve ser aplicado
        assert validator.validate("hello") == "HELLO"
        
        # Erro no validador customizado deve ser capturado
        def failing_validator(value):
            raise ValueError("Custom validation failed")
        
        validator = FieldValidator("test_field", custom_validator=failing_validator)
        
        with pytest.raises(ValidationError) as exc_info:
            validator.validate("test")
        assert "Validação customizada falhou" in str(exc_info.value)


class TestDataValidator:
    """Testes para DataValidator"""

    def test_basic_validation(self):
        """Testa validação básica de estrutura"""
        schema = DataValidator("test_schema", [
            FieldValidator("name", required=True, data_type=str),
            FieldValidator("age", required=True, data_type=int, min_value=0),
            FieldValidator("email", required=False, data_type=str),
        ])
        
        # Dados válidos devem passar
        data = {"name": "João", "age": 30}
        result = schema.validate(data)
        assert result["name"] == "João"
        assert result["age"] == 30
        
        # Dados com campo opcional devem passar
        data = {"name": "João", "age": 30, "email": "joao@email.com"}
        result = schema.validate(data)
        assert result["email"] == "joao@email.com"

    def test_multiple_validation_errors(self):
        """Testa múltiplos erros de validação"""
        schema = DataValidator("test_schema", [
            FieldValidator("name", required=True, data_type=str),
            FieldValidator("age", required=True, data_type=int, min_value=0),
        ])
        
        # Múltiplos erros devem ser coletados
        data = {"age": -1}  # name ausente, age inválido
        
        with pytest.raises(MultipleValidationError) as exc_info:
            schema.validate(data)
        
        errors = exc_info.value.errors
        assert len(errors) == 2
        assert any("Campo obrigatório" in str(e) for e in errors)
        assert any("Deve ser >= 0" in str(e) for e in errors)

    def test_strict_mode(self):
        """Testa modo strict (rejeita campos extras)"""
        schema = DataValidator("test_schema", [
            FieldValidator("name", required=True, data_type=str),
        ])
        
        data = {"name": "João", "extra_field": "valor"}
        
        # Modo strict deve rejeitar campos extras
        with pytest.raises(MultipleValidationError) as exc_info:
            schema.validate(data, strict=True)
        
        # Modo não-strict deve aceitar campos extras
        result = schema.validate(data, strict=False)
        assert result["name"] == "João"
        assert result["extra_field"] == "valor"


class TestCustomValidators:
    """Testes para validadores customizados"""

    def test_validate_cpf(self):
        """Testa validação de CPF"""
        # CPF válido deve passar
        assert validate_cpf("11144477735") == "11144477735"
        assert validate_cpf("111.444.777-35") == "11144477735"
        
        # CPF inválido deve falhar
        with pytest.raises(ValueError):
            validate_cpf("12345678901")
        
        with pytest.raises(ValueError):
            validate_cpf("111.111.111-11")  # Sequência
        
        with pytest.raises(ValueError):
            validate_cpf("123456789")  # Tamanho incorreto

    def test_validate_cnpj(self):
        """Testa validação de CNPJ"""
        # CNPJ válido deve passar
        assert validate_cnpj("11222333000181") == "11222333000181"
        assert validate_cnpj("11.222.333/0001-81") == "11222333000181"
        
        # CNPJ inválido deve falhar
        with pytest.raises(ValueError):
            validate_cnpj("12345678000123")
        
        with pytest.raises(ValueError):
            validate_cnpj("11.111.111/1111-11")  # Sequência

    def test_validate_email(self):
        """Testa validação de email"""
        # Emails válidos devem passar
        assert validate_email("test@example.com") == "test@example.com"
        assert validate_email("USER@DOMAIN.COM") == "user@domain.com"
        
        # Emails inválidos devem falhar
        with pytest.raises(ValueError):
            validate_email("invalid-email")
        
        with pytest.raises(ValueError):
            validate_email("@domain.com")

    def test_validate_url(self):
        """Testa validação de URL"""
        # URLs válidas devem passar
        assert validate_url("https://example.com") == "https://example.com"
        assert validate_url("http://api.example.com/webhook") == "http://api.example.com/webhook"
        
        # URLs inválidas devem falhar
        with pytest.raises(ValueError):
            validate_url("ftp://example.com")
        
        with pytest.raises(ValueError):
            validate_url("not-a-url")

    def test_validate_txid(self):
        """Testa validação de TXID PIX"""
        # TXIDs válidos devem passar
        assert validate_txid("abcdefghijklmnopqrstuvwxyz") == "abcdefghijklmnopqrstuvwxyz"
        assert validate_txid("12345678901234567890123456") == "12345678901234567890123456"
        
        # TXIDs inválidos devem falhar
        with pytest.raises(ValueError):
            validate_txid("12345")  # Muito curto
        
        with pytest.raises(ValueError):
            validate_txid("a" * 40)  # Muito longo
        
        with pytest.raises(ValueError):
            validate_txid("txid-com-hifen")  # Caracteres inválidos

    def test_validate_monetary_value(self):
        """Testa validação de valor monetário"""
        # Valores válidos devem passar
        assert validate_monetary_value("100.50") == "100.50"
        assert validate_monetary_value(100) == "100.00"
        assert validate_monetary_value(Decimal("50.75")) == "50.75"
        
        # Valores inválidos devem falhar
        with pytest.raises(ValueError):
            validate_monetary_value(-10)  # Negativo
        
        with pytest.raises(ValueError):
            validate_monetary_value("texto")  # Não numérico
        
        with pytest.raises(ValueError):
            validate_monetary_value(10**10)  # Muito alto

    def test_validate_date_range(self):
        """Testa validação de range de datas"""
        # Datas válidas devem passar
        result = validate_date_range(1, 2024, 1, 31)
        assert result == (1, 2024, 1, 31)
        
        # Datas inválidas devem falhar
        with pytest.raises(ValueError):
            validate_date_range(13, 2024, 1, 31)  # Mês inválido
        
        with pytest.raises(ValueError):
            validate_date_range(1, 1999, 1, 31)  # Ano muito antigo
        
        with pytest.raises(ValueError):
            validate_date_range(1, 2024, 31, 1)  # Dia inicial > final
        
        with pytest.raises(ValueError):
            validate_date_range(2, 2024, 30, 30)  # Data inexistente


class TestSchemas:
    """Testes para schemas predefinidos"""

    def test_boleto_schema(self):
        """Testa schema de boleto"""
        schema = get_boleto_schema()
        
        # Dados válidos devem passar
        data = {
            "numeroContrato": 123456,
            "modalidade": 1,
            "numeroContaCorrente": 12345,
            "especieDocumento": "DM",
            "dataVencimento": "2024-12-31",
            "valorNominal": "100.50",
            "pagador": {"nome": "João", "cpfCnpj": "12345678901"},
        }
        
        result = schema.validate(data, strict=False)
        assert result["numeroContrato"] == 123456
        assert result["valorNominal"] == "100.50"
        
        # Dados inválidos devem falhar
        data["modalidade"] = 5  # Valor não permitido
        with pytest.raises(MultipleValidationError):
            schema.validate(data)

    def test_pix_cobranca_schema(self):
        """Testa schema de cobrança PIX"""
        schema = get_pix_cobranca_schema()
        
        # Dados válidos devem passar
        data = {
            "calendario": {"expiracao": 3600},
            "valor": {"original": "100.50"},
            "chave": "usuario@exemplo.com",
            "solicitacaoPagador": "Pagamento teste"
        }
        
        result = schema.validate(data, strict=False)
        assert result["chave"] == "usuario@exemplo.com"
        
        # Campo obrigatório ausente deve falhar
        del data["chave"]
        with pytest.raises(MultipleValidationError):
            schema.validate(data)

    def test_webhook_schema(self):
        """Testa schema de webhook"""
        schema = get_webhook_schema()
        
        # Dados válidos devem passar
        data = {"webhookUrl": "https://example.com/webhook"}
        result = schema.validate(data)
        assert result["webhookUrl"] == "https://example.com/webhook"
        
        # URL inválida deve falhar
        data = {"webhookUrl": "url-invalida"}
        with pytest.raises(MultipleValidationError):
            schema.validate(data)

    def test_pagador_schema(self):
        """Testa schema de pagador"""
        schema = get_pagador_schema()
        
        # Dados válidos com CPF devem passar
        data = {
            "nome": "João Silva",
            "cpfCnpj": "11144477735",
            "email": "joao@exemplo.com"
        }
        
        result = schema.validate(data, strict=False)
        assert result["nome"] == "João Silva"
        assert result["cpfCnpj"] == "11144477735"
        
        # Nome muito longo deve falhar
        data["nome"] = "x" * 80
        with pytest.raises(MultipleValidationError):
            schema.validate(data)


class TestIntegration:
    """Testes de integração com validação"""

    def test_error_messages(self):
        """Testa mensagens de erro descritivas"""
        validator = FieldValidator("test_field", required=True, data_type=int, min_value=1)
        
        with pytest.raises(ValidationError) as exc_info:
            validator.validate(None)
        
        error = exc_info.value
        assert error.field == "test_field"
        assert "Campo obrigatório" in str(error)
        assert "Campo 'test_field'" in str(error)

    def test_validation_error_attributes(self):
        """Testa atributos do ValidationError"""
        try:
            raise ValidationError("Test message", "test_field", "test_value")
        except ValidationError as e:
            assert e.field == "test_field"
            assert e.value == "test_value"
            assert "Campo 'test_field': Test message" in str(e)

    def test_multiple_validation_error_collection(self):
        """Testa coleta de múltiplos erros"""
        errors = [
            ValidationError("Error 1", "field1", "value1"),
            ValidationError("Error 2", "field2", "value2"),
        ]
        
        multiple_error = MultipleValidationError(errors)
        assert len(multiple_error.errors) == 2
        assert "Error 1" in str(multiple_error)
        assert "Error 2" in str(multiple_error)