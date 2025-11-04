"""Testes para o sistema de logging do SDK"""

import io
import json
import logging
import os
from unittest.mock import patch

from sicoob.logging_config import (
    JSONFormatter,
    SensitiveDataFilter,
    SicoobLogger,
    get_logger,
)


def test_sensitive_data_filter():
    """Testa o filtro de dados sensíveis"""
    filter_obj = SensitiveDataFilter()

    # Teste com dados sensíveis
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='',
        lineno=0,
        msg='{"password": "secret123", "token": "abc123", "normal_field": "value"}',
        args=(),
        exc_info=None,
    )

    # Aplica o filtro
    assert filter_obj.filter(record) is True

    # Verifica se dados sensíveis foram mascarados
    msg = str(record.msg)
    assert 'secret123' not in msg
    assert 'abc123' not in msg
    assert '"password": "***"' in msg or 'password=***' in msg.replace(' ', '')


def test_json_formatter():
    """Testa o formatador JSON"""
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name='sicoob.test',
        level=logging.INFO,
        pathname='/path/test.py',
        lineno=42,
        msg='Test message',
        args=(),
        exc_info=None,
    )

    # Adiciona campos extras
    record.request_id = 'req_123'
    record.operation = 'test_operation'
    record.duration_ms = 150.5

    output = formatter.format(record)
    log_data = json.loads(output)

    assert log_data['level'] == 'INFO'
    assert log_data['logger'] == 'sicoob.test'
    assert log_data['message'] == 'Test message'
    assert log_data['request_id'] == 'req_123'
    assert log_data['operation'] == 'test_operation'
    assert log_data['duration_ms'] == 150.5


def test_sicoob_logger_configuration():
    """Testa a configuração do logger"""
    # Força reconfiguração para teste
    SicoobLogger.configure(level='DEBUG', format_type='custom', force_reconfigure=True)

    logger = SicoobLogger.get_logger('test.logger')
    # Verifica se é uma instância de logger válida
    assert isinstance(logger, logging.Logger)

    # Verifica se o logger raiz foi configurado corretamente
    root_logger = logging.getLogger('sicoob')
    assert root_logger.level == logging.DEBUG


def test_get_logger_convenience():
    """Testa função de conveniência get_logger"""
    logger = get_logger('sicoob.test')
    assert isinstance(logger, logging.Logger)
    assert logger.name == 'sicoob.test'


@patch.dict(
    os.environ,
    {
        'SICOOB_LOG_LEVEL': 'WARNING',
        'SICOOB_LOG_FORMAT': 'json',
        'SICOOB_LOG_REQUESTS': 'true',
        'SICOOB_LOG_RESPONSES': 'true',
    },
)
def test_environment_configuration():
    """Testa configuração via variáveis de ambiente"""
    SicoobLogger.configure(force_reconfigure=True)

    # Verifica se as configurações foram aplicadas
    root_logger = logging.getLogger('sicoob')
    assert root_logger.level == logging.WARNING

    # Verifica se a configuração HTTP foi aplicada
    assert SicoobLogger._log_requests is True
    assert SicoobLogger._log_responses is True


def test_http_logging():
    """Testa logging de requisições e respostas HTTP"""
    # Configura logging HTTP
    SicoobLogger.configure(
        log_requests=True, log_responses=True, force_reconfigure=True
    )

    # Captura logs
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(JSONFormatter())  # Usa JSON para capturar campos extras
    logger = logging.getLogger('sicoob.http')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Testa log de requisição
    SicoobLogger.log_http_request(
        method='POST',
        url='https://api.sicoob.com.br/test',
        headers={
            'Authorization': 'Bearer token123',
            'Content-Type': 'application/json',
        },
        body='{"test": "data"}',
        request_id='req_123',
    )

    # Testa log de resposta
    SicoobLogger.log_http_response(
        status_code=200,
        url='https://api.sicoob.com.br/test',
        duration_ms=150.5,
        response_body='{"result": "success"}',
        request_id='req_123',
    )

    # Verifica se logs foram gerados
    log_output = log_stream.getvalue()
    log_lines = log_output.strip().split('\n')

    # Deve ter duas linhas: uma para request e uma para response
    assert len(log_lines) == 2

    # Verifica log de request
    request_log = json.loads(log_lines[0])
    assert 'HTTP Request: POST' in request_log['message']
    assert request_log['request_id'] == 'req_123'
    assert request_log['method'] == 'POST'
    assert 'Bearer token123' not in json.dumps(
        request_log
    )  # Token deve estar mascarado

    # Verifica log de response
    response_log = json.loads(log_lines[1])
    assert 'HTTP Response: 200' in response_log['message']
    assert response_log['request_id'] == 'req_123'
    assert response_log['status_code'] == 200


def test_logger_with_extra_fields():
    """Testa logger com campos extras"""
    logger = get_logger('sicoob.test')

    # Captura logs
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Log com campos extras
    logger.info(
        'Operation completed',
        extra={
            'operation': 'test_op',
            'duration_ms': 250,
            'status_code': 201,
            'url': 'https://api.test.com',
        },
    )

    log_output = log_stream.getvalue()
    assert 'Operation completed' in log_output


def test_logging_with_sensitive_data():
    """Testa que dados sensíveis são filtrados nos logs"""
    logger = get_logger('sicoob.test')

    # Captura logs
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Log com dados sensíveis
    logger.info('Authentication data: {"password": "secret123", "token": "abc456"}')

    log_output = log_stream.getvalue()
    assert 'secret123' not in log_output
    assert 'abc456' not in log_output


def test_external_logger_configuration():
    """Testa configuração de loggers externos"""
    SicoobLogger.configure(level='DEBUG', force_reconfigure=True)

    # Verifica configuração de bibliotecas externas
    requests_logger = logging.getLogger('requests')
    urllib3_logger = logging.getLogger('urllib3')
    pypix_logger = logging.getLogger('pypix_api')

    assert requests_logger.level == logging.WARNING
    assert urllib3_logger.level == logging.WARNING
    assert pypix_logger.level == logging.DEBUG  # Em modo DEBUG fica verbosa


def test_json_format_configuration():
    """Testa configuração com formato JSON"""
    SicoobLogger.configure(format_type='json', force_reconfigure=True)

    logger = get_logger('sicoob.test')

    # Captura logs
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info('Test JSON format')

    log_output = log_stream.getvalue().strip()
    log_data = json.loads(log_output)

    assert log_data['level'] == 'INFO'
    assert log_data['message'] == 'Test JSON format'
    assert 'timestamp' in log_data
