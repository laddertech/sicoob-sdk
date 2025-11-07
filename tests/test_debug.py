"""Testes para o módulo sicoob.debug."""

import logging
from unittest.mock import Mock, patch

from sicoob.config import SicoobConfig
from sicoob.debug import (
    debug_mode,
    disable_http_logging,
    enable_http_logging,
    suppress_sicoob_logs,
)


class TestDebugMode:
    """Testes para o context manager debug_mode()."""

    def test_debug_mode_enables_and_restores_config(self):
        """Testa que debug_mode ativa e restaura configurações."""
        # Salva estado inicial
        original_debug = SicoobConfig.get_current_config().debug_mode
        original_log_level = SicoobConfig.get_log_level()

        # Usa debug_mode
        with debug_mode():
            # Verifica que debug foi ativado
            assert SicoobConfig.is_debug_mode()

        # Verifica que configuração foi restaurada
        assert SicoobConfig.get_current_config().debug_mode == original_debug

    def test_debug_mode_with_log_payloads(self):
        """Testa debug_mode com log_payloads=True."""
        original_log_requests = SicoobConfig.should_log_requests()
        original_log_responses = SicoobConfig.should_log_responses()

        with debug_mode(log_payloads=True):
            # Dentro do context, logs devem estar ativos
            config = SicoobConfig.get_current_config()
            # Debug mode foi ativado
            assert config.debug_mode

        # Configurações restauradas
        assert SicoobConfig.should_log_requests() == original_log_requests
        assert SicoobConfig.should_log_responses() == original_log_responses

    def test_debug_mode_restores_logger_levels(self):
        """Testa que níveis de logging são restaurados."""
        logger_sicoob = logging.getLogger('sicoob')
        original_level = logger_sicoob.level

        with debug_mode():
            # Logger deve estar em DEBUG
            assert logger_sicoob.level == logging.DEBUG

        # Nível restaurado
        assert logger_sicoob.level == original_level

    def test_debug_mode_handles_exceptions(self):
        """Testa que configurações são restauradas mesmo com exceção."""
        original_debug = SicoobConfig.get_current_config().debug_mode

        try:
            with debug_mode():
                # Força uma exceção
                raise ValueError('Test error')
        except ValueError:
            pass

        # Configuração deve ter sido restaurada mesmo com exceção
        assert SicoobConfig.get_current_config().debug_mode == original_debug


class TestSuppressSicoobLogs:
    """Testes para o context manager suppress_sicoob_logs()."""

    def test_suppress_logs_sets_critical_level(self):
        """Testa que suppress_sicoob_logs define nível CRITICAL."""
        logger_sicoob = logging.getLogger('sicoob')
        original_level = logger_sicoob.level

        with suppress_sicoob_logs():
            # Logger deve estar em CRITICAL (suprimido)
            assert logger_sicoob.level == logging.CRITICAL

        # Nível restaurado
        assert logger_sicoob.level == original_level

    def test_suppress_logs_restores_on_exception(self):
        """Testa que nível é restaurado mesmo com exceção."""
        logger_sicoob = logging.getLogger('sicoob')
        original_level = logger_sicoob.level

        try:
            with suppress_sicoob_logs():
                raise RuntimeError('Test error')
        except RuntimeError:
            pass

        # Nível restaurado
        assert logger_sicoob.level == original_level


class TestEnableHttpLogging:
    """Testes para enable_http_logging() e disable_http_logging()."""

    @patch('logging.getLogger')
    @patch('sicoob.debug.SicoobConfig')
    @patch('builtins.print')
    def test_enable_http_logging_configures_loggers(
        self, mock_print, mock_config, mock_get_logger
    ):
        """Testa que enable_http_logging configura todos os loggers."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        enable_http_logging()

        # Verifica que loggers do aiohttp foram configurados
        calls = mock_get_logger.call_args_list
        logger_names = [call[0][0] for call in calls]

        assert 'aiohttp' in logger_names
        assert 'aiohttp.client' in logger_names
        assert 'aiohttp.access' in logger_names

        # Verifica que setLevel foi chamado
        assert mock_logger.setLevel.called

        # Verifica que enable_debug foi chamado
        mock_config.enable_debug.assert_called_once()

        # Verifica que print foi chamado
        mock_print.assert_called_once()

    @patch('logging.getLogger')
    @patch('sicoob.debug.SicoobConfig')
    @patch('builtins.print')
    def test_disable_http_logging_restores_loggers(
        self, mock_print, mock_config, mock_get_logger
    ):
        """Testa que disable_http_logging restaura loggers."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        disable_http_logging()

        # Verifica que loggers foram configurados para WARNING
        calls = mock_get_logger.call_args_list
        logger_names = [call[0][0] for call in calls]

        assert 'aiohttp' in logger_names
        assert 'aiohttp.client' in logger_names
        assert 'aiohttp.access' in logger_names

        # Verifica que setLevel foi chamado com WARNING
        mock_logger.setLevel.assert_called_with(logging.WARNING)

        # Verifica que disable_debug foi chamado
        mock_config.disable_debug.assert_called_once()

        # Verifica que print foi chamado
        mock_print.assert_called_once()


class TestDebugIntegration:
    """Testes de integração para módulo debug."""

    def test_nested_debug_contexts(self):
        """Testa que contexts aninhados funcionam corretamente."""
        original_level = logging.getLogger('sicoob').level

        with debug_mode():
            level_outer = logging.getLogger('sicoob').level

            with suppress_sicoob_logs():
                level_inner = logging.getLogger('sicoob').level
                # Deve estar em CRITICAL
                assert level_inner == logging.CRITICAL

            # Deve ter restaurado para DEBUG
            assert logging.getLogger('sicoob').level == level_outer

        # Deve ter restaurado para original
        assert logging.getLogger('sicoob').level == original_level

    def test_debug_mode_multiple_times(self):
        """Testa que debug_mode pode ser usado múltiplas vezes."""
        original_level = logging.getLogger('sicoob').level

        # Primeira vez
        with debug_mode():
            assert logging.getLogger('sicoob').level == logging.DEBUG

        assert logging.getLogger('sicoob').level == original_level

        # Segunda vez
        with debug_mode():
            assert logging.getLogger('sicoob').level == logging.DEBUG

        assert logging.getLogger('sicoob').level == original_level
