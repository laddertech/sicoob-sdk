"""Sistema de logging configurável para o Sicoob SDK

Este módulo fornece uma configuração centralized de logging para todo o SDK,
permitindo diferentes níveis de verbosidade para debug, desenvolvimento e produção.

Configuração via variáveis de ambiente:
    SICOOB_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL
    SICOOB_LOG_FORMAT: custom, json, simple
    SICOOB_LOG_FILE: caminho para arquivo de log (opcional)
    SICOOB_LOG_REQUESTS: true/false (logar requisições HTTP)
    SICOOB_LOG_RESPONSES: true/false (logar respostas HTTP)
"""

import json
import logging
import logging.handlers
import os
import sys
from pathlib import Path


class SensitiveDataFilter(logging.Filter):
    """Filtro para remover dados sensíveis dos logs"""

    SENSITIVE_FIELDS = {
        'password',
        'senha',
        'token',
        'access_token',
        'refresh_token',
        'authorization',
        'certificate',
        'key',
        'cpf',
        'cnpj',
        'bearer',
        'client_secret',
        'private_key',
        'certificado',
        'chave_privada',
    }

    def filter(self, record: logging.LogRecord) -> bool:
        """Filtra dados sensíveis da mensagem de log"""
        if hasattr(record, 'msg') and record.msg:
            # Converte para string se necessário
            msg = str(record.msg)

            # Procura por padrões sensíveis e os mascarar
            for field in self.SENSITIVE_FIELDS:
                # Padrão: "campo": "valor" ou campo=valor
                import re

                patterns = [
                    rf'("{field}"\s*:\s*"[^"]*")',
                    rf"('{field}'\s*:\s*'[^']*')",
                    rf'({field}\s*=\s*[^\s,&]*)',
                ]

                for pattern in patterns:
                    msg = re.sub(
                        pattern,
                        lambda m: m.group(0).split('=')[0] + '=***'
                        if '=' in m.group(0)
                        else f'"{field}": "***"',
                        msg,
                        flags=re.IGNORECASE,
                    )

            record.msg = msg

        return True


class JSONFormatter(logging.Formatter):
    """Formatador JSON estruturado para logs"""

    def format(self, record: logging.LogRecord) -> str:
        """Formata o log em JSON estruturado"""
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Adiciona todos os campos extras automaticamente
        reserved_attrs = {
            'name',
            'msg',
            'args',
            'levelname',
            'levelno',
            'pathname',
            'filename',
            'module',
            'lineno',
            'funcName',
            'created',
            'msecs',
            'relativeCreated',
            'thread',
            'threadName',
            'processName',
            'process',
            'message',
            'exc_info',
            'exc_text',
            'stack_info',
            'getMessage',
            'extra',
        }

        # Adiciona campos extras que não sejam atributos padrão do LogRecord
        for key, value in record.__dict__.items():
            if key not in reserved_attrs and not key.startswith('_'):
                log_entry[key] = value

        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class SicoobLogger:
    """Classe principal para configuração de logging do SDK"""

    _configured = False
    _loggers: dict[str, logging.Logger] = {}

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Obtém ou cria um logger configurado

        Args:
            name: Nome do logger (geralmente __name__)

        Returns:
            Logger configurado
        """
        if not cls._configured:
            cls.configure()

        if name not in cls._loggers:
            logger = logging.getLogger(name)
            logger.addFilter(SensitiveDataFilter())
            cls._loggers[name] = logger

        return cls._loggers[name]

    @classmethod
    def configure(
        cls,
        level: str | None = None,
        format_type: str | None = None,
        log_file: str | None = None,
        log_requests: bool | None = None,
        log_responses: bool | None = None,
        force_reconfigure: bool = False,
    ) -> None:
        """Configura o sistema de logging

        Args:
            level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_type: Tipo de formato (custom, json, simple)
            log_file: Caminho para arquivo de log
            log_requests: Se deve logar requisições HTTP
            log_responses: Se deve logar respostas HTTP
            force_reconfigure: Força reconfiguração mesmo se já configurado
        """
        if cls._configured and not force_reconfigure:
            return

        # Configurações padrão e de ambiente
        level = level or os.getenv('SICOOB_LOG_LEVEL', 'INFO').upper()
        format_type = format_type or os.getenv('SICOOB_LOG_FORMAT', 'custom').lower()
        log_file = log_file or os.getenv('SICOOB_LOG_FILE')
        log_requests = (
            log_requests
            if log_requests is not None
            else os.getenv('SICOOB_LOG_REQUESTS', 'false').lower() == 'true'
        )
        log_responses = (
            log_responses
            if log_responses is not None
            else os.getenv('SICOOB_LOG_RESPONSES', 'false').lower() == 'true'
        )

        # Configura o logger raiz do SDK
        root_logger = logging.getLogger('sicoob')
        root_logger.setLevel(getattr(logging, level, logging.INFO))

        # Remove handlers existentes para reconfiguração
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Formatadores
        formatters = {
            'custom': logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
            ),
            'json': JSONFormatter(),
            'simple': logging.Formatter('%(levelname)s: %(message)s'),
        }

        formatter = formatters.get(format_type, formatters['custom'])

        # Handler para console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(SensitiveDataFilter())
        root_logger.addHandler(console_handler)

        # Handler para arquivo se especificado
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8',
            )
            file_handler.setFormatter(formatter)
            file_handler.addFilter(SensitiveDataFilter())
            root_logger.addHandler(file_handler)

        # Configurações específicas para requests HTTP
        cls._configure_http_logging(log_requests, log_responses)

        # Configurações para bibliotecas externas
        cls._configure_external_loggers(level)

        cls._configured = True

        # Log de inicialização
        logger = cls.get_logger('sicoob.logging')
        logger.info(
            'Sistema de logging configurado',
            extra={
                'operation': 'logging_init',
                'log_level': level,
                'format_type': format_type,
                'log_file': bool(log_file),
                'log_requests': log_requests,
                'log_responses': log_responses,
            },
        )

    @classmethod
    def _configure_http_logging(cls, log_requests: bool, log_responses: bool) -> None:
        """Configura logging para requests HTTP"""
        if log_requests:
            # Configura urllib3 para logar requisições
            logging.getLogger('urllib3.connectionpool').setLevel(logging.DEBUG)

        # Mantém urllib3 mais silencioso por padrão para não poluir logs
        if not log_requests:
            logging.getLogger('urllib3').setLevel(logging.WARNING)

        # Armazena configuração para uso posterior
        cls._log_requests = log_requests
        cls._log_responses = log_responses

    @classmethod
    def _configure_external_loggers(cls, level: str) -> None:
        """Configura níveis de log para bibliotecas externas"""
        external_loggers = {
            'requests': 'WARNING',
            'urllib3': 'WARNING',
            'pypix_api': 'INFO',  # Mantém pypix-api informativo
        }

        # Em modo DEBUG, deixa pypix-api mais verbosa
        if level == 'DEBUG':
            external_loggers['pypix_api'] = 'DEBUG'

        for logger_name, logger_level in external_loggers.items():
            logging.getLogger(logger_name).setLevel(getattr(logging, logger_level))

    @classmethod
    def log_http_request(
        cls,
        method: str,
        url: str,
        headers: dict | None = None,
        body: str | None = None,
        request_id: str | None = None,
    ) -> None:
        """Loga uma requisição HTTP

        Args:
            method: Método HTTP
            url: URL da requisição
            headers: Headers da requisição
            body: Corpo da requisição
            request_id: ID único da requisição
        """
        if not cls._log_requests:
            return

        logger = cls.get_logger('sicoob.http')

        # Sanitiza headers sensíveis
        safe_headers = {}
        if headers:
            for key, value in headers.items():
                if key.lower() in {'authorization', 'x-api-key', 'bearer'}:
                    safe_headers[key] = '***'
                else:
                    safe_headers[key] = value

        logger.info(
            f'HTTP Request: {method} {url}',
            extra={
                'operation': 'http_request',
                'request_id': request_id,
                'method': method,
                'url': url,
                'headers': safe_headers,
                'has_body': bool(body),
                'body_length': len(body) if body else 0,
            },
        )

    @classmethod
    def log_http_response(
        cls,
        status_code: int,
        url: str,
        duration_ms: float,
        response_body: str | None = None,
        request_id: str | None = None,
    ) -> None:
        """Loga uma resposta HTTP

        Args:
            status_code: Código de status HTTP
            url: URL da requisição
            duration_ms: Duração em milissegundos
            response_body: Corpo da resposta
            request_id: ID único da requisição
        """
        if not cls._log_responses:
            return

        logger = cls.get_logger('sicoob.http')

        level = logging.INFO if 200 <= status_code < 400 else logging.WARNING

        logger.log(
            level,
            f'HTTP Response: {status_code} from {url} ({duration_ms:.2f}ms)',
            extra={
                'operation': 'http_response',
                'request_id': request_id,
                'status_code': status_code,
                'url': url,
                'duration_ms': duration_ms,
                'has_response_body': bool(response_body),
                'response_length': len(response_body) if response_body else 0,
            },
        )


# Função de conveniência para obter logger
def get_logger(name: str) -> logging.Logger:
    """Função de conveniência para obter um logger configurado

    Args:
        name: Nome do logger (geralmente __name__)

    Returns:
        Logger configurado
    """
    return SicoobLogger.get_logger(name)


# Configuração automática na importação
SicoobLogger.configure()
