"""Sistema de validação de entrada para o Sicoob SDK"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


class ValidationError(Exception):
    """Erro de validação de dados"""

    def __init__(
        self, message: str, field: str | None = None, value: Any = None
    ) -> None:
        super().__init__(message)
        self.field = field
        self.value = value

    def __str__(self) -> str:
        if self.field:
            return f"Campo '{self.field}': {super().__str__()}"
        return super().__str__()


class MultipleValidationError(Exception):
    """Múltiplos erros de validação"""

    def __init__(self, errors: list[ValidationError]) -> None:
        self.errors = errors
        messages = [str(error) for error in errors]
        super().__init__(f'Múltiplos erros de validação: {"; ".join(messages)}')


@dataclass
class FieldValidator:
    """Validador para um campo específico"""

    name: str
    required: bool = True
    data_type: type | None = None
    min_value: int | float | None = None
    max_value: int | float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    allowed_values: list[Any] | None = None
    custom_validator: Callable | None = None
    description: str | None = None

    def validate(self, value: Any) -> Any:
        """Valida um valor para este campo"""
        # Validação de obrigatoriedade
        value = self._validate_required(value)

        # Campo opcional e vazio - retorna cedo
        if not self.required and (value is None or value == ''):
            return value

        # Conversão de tipo
        value = self._validate_and_convert_type(value)

        # Validações específicas
        self._validate_numeric_range(value)
        self._validate_string_length(value)
        self._validate_pattern(value)
        self._validate_allowed_values(value)
        value = self._validate_custom(value)

        return value

    def _validate_required(self, value: Any) -> Any:
        """Valida se campo obrigatório está presente."""
        if self.required and (value is None or value == ''):
            raise ValidationError(
                'Campo obrigatório não pode estar vazio', self.name, value
            )
        return value

    def _validate_and_convert_type(self, value: Any) -> Any:
        """Valida e converte tipo de dados."""
        if self.data_type and not isinstance(value, self.data_type):
            try:
                # Tenta conversão automática
                if self.data_type in (int, float):
                    value = self.data_type(value)
                elif self.data_type is str:
                    value = str(value)
                else:
                    raise TypeError()
            except (ValueError, TypeError) as e:
                raise ValidationError(
                    f'Deve ser do tipo {self.data_type.__name__}, recebido {type(value).__name__}',
                    self.name,
                    value,
                ) from e
        return value

    def _validate_numeric_range(self, value: Any) -> None:
        """Valida range para valores numéricos."""
        if isinstance(value, int | float):
            if self.min_value is not None and value < self.min_value:
                raise ValidationError(f'Deve ser >= {self.min_value}', self.name, value)
            if self.max_value is not None and value > self.max_value:
                raise ValidationError(f'Deve ser <= {self.max_value}', self.name, value)

    def _validate_string_length(self, value: Any) -> None:
        """Valida comprimento de strings."""
        if isinstance(value, str):
            if self.min_length is not None and len(value) < self.min_length:
                raise ValidationError(
                    f'Deve ter pelo menos {self.min_length} caracteres',
                    self.name,
                    value,
                )
            if self.max_length is not None and len(value) > self.max_length:
                raise ValidationError(
                    f'Deve ter no máximo {self.max_length} caracteres', self.name, value
                )

    def _validate_pattern(self, value: Any) -> None:
        """Valida padrão regex."""
        if self.pattern and isinstance(value, str):
            if not re.match(self.pattern, value):
                raise ValidationError(
                    f'Formato inválido (padrão: {self.pattern})', self.name, value
                )

    def _validate_allowed_values(self, value: Any) -> None:
        """Valida valores permitidos."""
        if self.allowed_values and value not in self.allowed_values:
            raise ValidationError(
                f'Deve ser um dos valores: {self.allowed_values}', self.name, value
            )

    def _validate_custom(self, value: Any) -> Any:
        """Executa validador customizado."""
        if self.custom_validator:
            try:
                validated_value = self.custom_validator(value)
                if validated_value is not None:
                    value = validated_value
            except Exception as e:
                raise ValidationError(
                    f'Validação customizada falhou: {e}', self.name, value
                ) from e
        return value


class DataValidator:
    """Validador para estruturas de dados completas"""

    def __init__(self, name: str, fields: list[FieldValidator]) -> None:
        self.name = name
        self.fields = {field.name: field for field in fields}

    def validate(self, data: dict[str, Any], strict: bool = True) -> dict[str, Any]:
        """Valida uma estrutura de dados completa

        Args:
            data: Dados para validar
            strict: Se True, rejeita campos não definidos no schema

        Returns:
            Dados validados e normalizados

        Raises:
            MultipleValidationError: Se houver múltiplos erros
        """
        if not isinstance(data, dict):
            raise ValidationError(
                f'Dados devem ser um dicionário, recebido {type(data).__name__}'
            )

        errors = []
        validated_data = {}

        # Valida campos definidos
        self._validate_defined_fields(data, validated_data, errors)

        # Processa campos não definidos no schema
        self._handle_undefined_fields(data, validated_data, errors, strict)

        if errors:
            raise MultipleValidationError(errors)

        return validated_data

    def _validate_defined_fields(
        self,
        data: dict[str, Any],
        validated_data: dict[str, Any],
        errors: list[ValidationError],
    ) -> None:
        """Valida campos definidos no schema."""
        for field_name, field_validator in self.fields.items():
            try:
                value = data.get(field_name)
                validated_value = field_validator.validate(value)
                if validated_value is not None:
                    validated_data[field_name] = validated_value
            except ValidationError as e:
                errors.append(e)

    def _handle_undefined_fields(
        self,
        data: dict[str, Any],
        validated_data: dict[str, Any],
        errors: list[ValidationError],
        strict: bool,
    ) -> None:
        """Processa campos não definidos no schema."""
        if strict:
            self._reject_undefined_fields(data, errors)
        else:
            self._include_undefined_fields(data, validated_data)

    def _reject_undefined_fields(
        self, data: dict[str, Any], errors: list[ValidationError]
    ) -> None:
        """Rejeita campos não definidos no schema."""
        for field_name in data:
            if field_name not in self.fields:
                errors.append(
                    ValidationError(
                        'Campo não permitido no schema',
                        field_name,
                        data[field_name],
                    )
                )

    def _include_undefined_fields(
        self, data: dict[str, Any], validated_data: dict[str, Any]
    ) -> None:
        """Inclui campos não definidos sem validação."""
        for field_name, value in data.items():
            if field_name not in validated_data:
                validated_data[field_name] = value


# Validadores customizados comuns


def validate_cpf(value: str) -> str:
    """Valida CPF"""
    if not isinstance(value, str):
        value = str(value)

    # Remove formatação
    cpf = re.sub(r'[^\d]', '', value)

    if len(cpf) != 11:
        raise ValueError('CPF deve ter 11 dígitos')

    # Verifica sequências inválidas
    if cpf == cpf[0] * 11:
        raise ValueError('CPF inválido (sequência)')

    # Algoritmo de validação do CPF
    def calc_digit(cpf_partial: str) -> str:
        total = 0
        for i, digit in enumerate(cpf_partial):
            total += int(digit) * (len(cpf_partial) + 1 - i)
        remainder = total % 11
        return '0' if remainder < 2 else str(11 - remainder)

    if cpf[9] != calc_digit(cpf[:9]) or cpf[10] != calc_digit(cpf[:10]):
        raise ValueError('CPF inválido')

    return cpf


def validate_cnpj(value: str) -> str:
    """Valida CNPJ"""
    if not isinstance(value, str):
        value = str(value)

    # Remove formatação
    cnpj = re.sub(r'[^\d]', '', value)

    if len(cnpj) != 14:
        raise ValueError('CNPJ deve ter 14 dígitos')

    # Verifica sequências inválidas
    if cnpj == cnpj[0] * 14:
        raise ValueError('CNPJ inválido (sequência)')

    # Algoritmo de validação do CNPJ
    def calc_digit(cnpj_partial: str, weights: list[int]) -> str:
        total = sum(
            int(digit) * weight
            for digit, weight in zip(cnpj_partial, weights, strict=False)
        )
        remainder = total % 11
        return '0' if remainder < 2 else str(11 - remainder)

    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    if cnpj[12] != calc_digit(cnpj[:12], weights_1) or cnpj[13] != calc_digit(
        cnpj[:13], weights_2
    ):
        raise ValueError('CNPJ inválido')

    return cnpj


def validate_email(value: str) -> str:
    """Valida email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, value):
        raise ValueError('Formato de email inválido')
    return value.lower()


def validate_url(value: str) -> str:
    """Valida URL"""
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    if not re.match(pattern, value):
        raise ValueError(
            'Formato de URL inválido (deve começar com http:// ou https://)'
        )
    return value


def validate_txid(value: str) -> str:
    """Valida TXID PIX (26-35 caracteres alfanuméricos)"""
    if not isinstance(value, str):
        value = str(value)

    if not (26 <= len(value) <= 35):
        raise ValueError('TXID deve ter entre 26 e 35 caracteres')

    if not re.match(r'^[a-zA-Z0-9]+$', value):
        raise ValueError('TXID deve conter apenas caracteres alfanuméricos')

    return value


def validate_monetary_value(value: str | int | float | Decimal) -> str:
    """Valida valor monetário e retorna como string formatada"""
    try:
        if isinstance(value, str):
            # Remove formatação se houver
            value = value.replace(',', '.')
            decimal_value = Decimal(value)
        else:
            decimal_value = Decimal(str(value))

        if decimal_value < 0:
            raise ValueError('Valor monetário não pode ser negativo')

        if decimal_value > Decimal('999999999.99'):
            raise ValueError('Valor monetário muito alto (máximo: 999.999.999,99)')

        # Formata com 2 casas decimais
        return f'{decimal_value:.2f}'

    except (InvalidOperation, ValueError, TypeError) as e:
        raise ValueError('Valor monetário inválido') from e


def validate_date_range(mes: int, ano: int, dia_inicial: int, dia_final: int) -> tuple:
    """Valida range de datas para extrato"""
    # Valida mês
    if not (1 <= mes <= 12):
        raise ValueError('Mês deve estar entre 1 e 12')

    # Valida ano
    current_year = datetime.now().year
    if not (2000 <= ano <= current_year):
        raise ValueError(f'Ano deve estar entre 2000 e {current_year}')

    # Valida dias
    if not (1 <= dia_inicial <= 31):
        raise ValueError('Dia inicial deve estar entre 1 e 31')

    if not (1 <= dia_final <= 31):
        raise ValueError('Dia final deve estar entre 1 e 31')

    if dia_inicial > dia_final:
        raise ValueError('Dia inicial não pode ser maior que dia final')

    # Valida se a data existe
    try:
        datetime(ano, mes, dia_inicial)
        datetime(ano, mes, dia_final)
    except ValueError as e:
        raise ValueError(f'Data inválida: {e}') from e

    return mes, ano, dia_inicial, dia_final


# Schemas predefinidos para operações comuns


def get_boleto_schema() -> DataValidator:
    """Schema para emissão de boleto"""
    return DataValidator(
        'boleto',
        [
            FieldValidator('numeroContrato', required=True, data_type=int, min_value=1),
            FieldValidator(
                'modalidade', required=True, data_type=int, allowed_values=[1, 2, 3]
            ),
            FieldValidator(
                'numeroContaCorrente', required=True, data_type=int, min_value=1
            ),
            FieldValidator(
                'especieDocumento',
                required=True,
                data_type=str,
                allowed_values=['DM', 'DS', 'NP', 'RC', 'CH'],
            ),
            FieldValidator(
                'dataVencimento',
                required=True,
                data_type=str,
                pattern=r'^\d{4}-\d{2}-\d{2}$',
            ),
            FieldValidator(
                'valorNominal',
                required=True,
                data_type=str,
                custom_validator=validate_monetary_value,
            ),
            FieldValidator('nossoNumero', required=False, data_type=str, max_length=20),
            FieldValidator('seuNumero', required=False, data_type=str, max_length=15),
            FieldValidator(
                'tipoDesconto',
                required=False,
                data_type=int,
                allowed_values=[0, 1, 2, 3],
            ),
            FieldValidator(
                'valorDesconto1',
                required=False,
                data_type=str,
                custom_validator=validate_monetary_value,
            ),
            FieldValidator(
                'dataDesconto1',
                required=False,
                data_type=str,
                pattern=r'^\d{4}-\d{2}-\d{2}$',
            ),
            FieldValidator(
                'valorMulta',
                required=False,
                data_type=str,
                custom_validator=validate_monetary_value,
            ),
            FieldValidator(
                'valorJuros',
                required=False,
                data_type=str,
                custom_validator=validate_monetary_value,
            ),
            FieldValidator('pagador', required=True, data_type=dict),
            FieldValidator('beneficiarioFinal', required=False, data_type=dict),
            FieldValidator('mensagem', required=False, data_type=str, max_length=500),
        ],
    )


def get_pix_cobranca_schema() -> DataValidator:
    """Schema para cobrança PIX"""
    return DataValidator(
        'pix_cobranca',
        [
            FieldValidator('calendario', required=True, data_type=dict),
            FieldValidator('valor', required=True, data_type=dict),
            FieldValidator('chave', required=True, data_type=str, min_length=1),
            FieldValidator(
                'solicitacaoPagador', required=False, data_type=str, max_length=140
            ),
            FieldValidator('infoAdicionais', required=False, data_type=list),
        ],
    )


def get_webhook_schema() -> DataValidator:
    """Schema para webhook"""
    return DataValidator(
        'webhook',
        [
            FieldValidator(
                'webhookUrl',
                required=True,
                data_type=str,
                custom_validator=validate_url,
            ),
        ],
    )


def get_pagador_schema() -> DataValidator:
    """Schema para dados do pagador"""
    return DataValidator(
        'pagador',
        [
            FieldValidator(
                'nome', required=True, data_type=str, min_length=1, max_length=70
            ),
            FieldValidator(
                'cpfCnpj',
                required=True,
                data_type=str,
                custom_validator=lambda x: validate_cpf(x)
                if len(re.sub(r'[^\d]', '', x)) == 11
                else validate_cnpj(x),
            ),
            FieldValidator(
                'email', required=False, data_type=str, custom_validator=validate_email
            ),
            FieldValidator('endereco', required=False, data_type=dict),
            FieldValidator(
                'telefone', required=False, data_type=str, pattern=r'^\d{10,11}$'
            ),
        ],
    )


# Decorator para validação automática
def validate_input(
    schema_name: str, field_name: str | None = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator para validar entrada de métodos automaticamente"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Mapeia schemas disponíveis
            schemas = {
                'boleto': get_boleto_schema(),
                'pix_cobranca': get_pix_cobranca_schema(),
                'webhook': get_webhook_schema(),
                'pagador': get_pagador_schema(),
            }

            if schema_name not in schemas:
                return func(*args, **kwargs)

            schema = schemas[schema_name]

            # Encontra o parâmetro a ser validado
            if field_name:
                # Procura nos kwargs primeiro
                if field_name in kwargs:
                    kwargs[field_name] = schema.validate(
                        kwargs[field_name], strict=False
                    )
                # Depois nos args (assume que field_name é o segundo parâmetro)
                elif len(args) > 1:
                    args_list = list(args)
                    args_list[1] = schema.validate(args_list[1], strict=False)
                    args = tuple(args_list)

            return func(*args, **kwargs)

        return wrapper

    return decorator
