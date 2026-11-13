"""Testes para configuração de retry global do AsyncSicoob.

Este módulo testa a funcionalidade de retry automático implementada
no AsyncAPIClient, incluindo exponential backoff, jitter e tratamento
de diferentes códigos HTTP.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from aiohttp import ClientResponse

from sicoob.async_client import AsyncAPIClient, AsyncSicoob
from sicoob.auth import OAuth2Client
from sicoob.exceptions import SicoobError


class TestAsyncAPIClientRetry:
    """Testes para retry automático no AsyncAPIClient."""

    @pytest.fixture
    def oauth_client(self):
        """Fixture para OAuth2Client mockado."""
        mock_oauth = Mock(spec=OAuth2Client)
        mock_oauth.get_access_token.return_value = 'mock_token'
        return mock_oauth

    @pytest.fixture
    def retry_config(self):
        """Fixture para configuração de retry padrão."""
        return {
            'max_tentativas': 3,
            'delay_inicial': 0.1,  # Delay pequeno para testes rápidos
            'backoff_exponencial': True,
            'codigos_retry': [500, 502, 503, 504, 429],
        }

    @pytest_asyncio.fixture
    async def api_client_with_retry(self, oauth_client, retry_config):
        """Fixture para AsyncAPIClient com retry configurado."""
        client = AsyncAPIClient(
            oauth_client=oauth_client,
            retry_config=retry_config,
        )
        await client._ensure_session()
        yield client
        if client._session:
            await client._session.close()

    @pytest.mark.asyncio
    async def test_retry_em_erro_500(self, api_client_with_retry):
        """Testa que retry é feito em erro 500."""
        # Mock response que falha 2x e depois sucede
        call_count = 0

        async def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_response = AsyncMock(spec=ClientResponse)
            mock_response.status = 500 if call_count < 3 else 200
            mock_response.text = AsyncMock(
                return_value='{"error": "server error"}'
                if call_count < 3
                else '{"data": "success"}'
            )
            mock_response.json = AsyncMock(
                return_value={'error': 'server error'}
                if call_count < 3
                else {'data': 'success'}
            )
            return mock_response

        with patch.object(api_client_with_retry._session, 'request') as mock_request:
            mock_request.return_value.__aenter__.side_effect = mock_request_side_effect

            # Deve fazer retry e eventualmente suceder
            result = await api_client_with_retry._make_request(
                'GET', 'https://api.test.com/endpoint', 'test_scope'
            )

            assert call_count == 3
            assert result == {'data': 'success'}

    @pytest.mark.asyncio
    async def test_retry_esgotado_em_erro_500(self, api_client_with_retry):
        """Testa que erro é lançado após esgotar tentativas."""
        call_count = 0

        async def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_response = AsyncMock(spec=ClientResponse)
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value='{"message": "Server Error"}')
            mock_response.headers = {}  # Mock headers para não quebrar
            return mock_response

        with patch.object(api_client_with_retry._session, 'request') as mock_request:
            mock_request.return_value.__aenter__.side_effect = mock_request_side_effect

            # Deve fazer 3 tentativas e falhar
            with pytest.raises(SicoobError) as exc_info:
                await api_client_with_retry._make_request(
                    'GET', 'https://api.test.com/endpoint', 'test_scope'
                )

            assert call_count == 3
            assert 'Server Error' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retry_em_erro_429_rate_limit(self, api_client_with_retry):
        """Testa que retry é feito em erro 429 (rate limit)."""
        call_count = 0

        async def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_response = AsyncMock(spec=ClientResponse)
            mock_response.status = 429 if call_count == 1 else 200
            mock_response.text = AsyncMock(
                return_value='{"error": "rate limit"}'
                if call_count == 1
                else '{"data": "success"}'
            )
            mock_response.json = AsyncMock(
                return_value={'error': 'rate limit'}
                if call_count == 1
                else {'data': 'success'}
            )
            return mock_response

        with patch.object(api_client_with_retry._session, 'request') as mock_request:
            mock_request.return_value.__aenter__.side_effect = mock_request_side_effect

            result = await api_client_with_retry._make_request(
                'GET', 'https://api.test.com/endpoint', 'test_scope'
            )

            assert call_count == 2
            assert result == {'data': 'success'}

    @pytest.mark.asyncio
    async def test_sem_retry_em_erro_400(self, api_client_with_retry):
        """Testa que NÃO faz retry em erro 400 (bad request)."""
        call_count = 0

        async def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_response = AsyncMock(spec=ClientResponse)
            mock_response.status = 400
            mock_response.text = AsyncMock(return_value='{"error": "bad request"}')
            mock_response.json = AsyncMock(return_value={'message': 'Bad Request'})
            return mock_response

        with patch.object(api_client_with_retry._session, 'request') as mock_request:
            mock_request.return_value.__aenter__.side_effect = mock_request_side_effect

            # Deve falhar imediatamente sem retry
            with pytest.raises(SicoobError):
                await api_client_with_retry._make_request(
                    'GET', 'https://api.test.com/endpoint', 'test_scope'
                )

            assert call_count == 1  # Apenas uma tentativa

    @pytest.mark.asyncio
    async def test_sem_retry_em_erro_404(self, api_client_with_retry):
        """Testa que NÃO faz retry em erro 404."""
        call_count = 0

        async def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_response = AsyncMock(spec=ClientResponse)
            mock_response.status = 404
            mock_response.text = AsyncMock(return_value='{"error": "not found"}')
            mock_response.json = AsyncMock(return_value={'message': 'Not Found'})
            return mock_response

        with patch.object(api_client_with_retry._session, 'request') as mock_request:
            mock_request.return_value.__aenter__.side_effect = mock_request_side_effect

            with pytest.raises(SicoobError):
                await api_client_with_retry._make_request(
                    'GET', 'https://api.test.com/endpoint', 'test_scope'
                )

            assert call_count == 1  # Apenas uma tentativa

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, oauth_client, retry_config):
        """Testa que o exponential backoff está funcionando."""
        client = AsyncAPIClient(
            oauth_client=oauth_client,
            retry_config=retry_config,
        )

        delays = []
        for tentativa in range(3):
            delay = client._calcular_delay_retry(tentativa)
            delays.append(delay)

        # Com backoff exponencial: delay_inicial * (2 ** tentativa)
        # Tentativa 0: ~0.1s, Tentativa 1: ~0.2s, Tentativa 2: ~0.4s
        # (com jitter de ±25%)

        assert delays[0] >= 0.075 and delays[0] <= 0.125  # 0.1 ± 25%
        assert delays[1] >= 0.15 and delays[1] <= 0.25  # 0.2 ± 25%
        assert delays[2] >= 0.30 and delays[2] <= 0.50  # 0.4 ± 25%

    @pytest.mark.asyncio
    async def test_sem_retry_quando_max_tentativas_1(self, oauth_client):
        """Testa que não faz retry quando max_tentativas=1."""
        retry_config = {
            'max_tentativas': 1,
            'delay_inicial': 0.1,
            'backoff_exponencial': True,
            'codigos_retry': [500, 502, 503, 504, 429],
        }

        client = AsyncAPIClient(
            oauth_client=oauth_client,
            retry_config=retry_config,
        )
        await client._ensure_session()

        call_count = 0

        async def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_response = AsyncMock(spec=ClientResponse)
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value='{"message": "Server Error"}')
            mock_response.headers = {}  # Mock headers para não quebrar
            return mock_response

        try:
            with patch.object(client._session, 'request') as mock_request:
                mock_request.return_value.__aenter__.side_effect = (
                    mock_request_side_effect
                )

                with pytest.raises(SicoobError):
                    await client._make_request(
                        'GET', 'https://api.test.com/endpoint', 'test_scope'
                    )

                assert call_count == 1  # Apenas uma tentativa
        finally:
            await client._session.close()

    @pytest.mark.asyncio
    async def test_should_retry_logic(self, oauth_client, retry_config):
        """Testa a lógica de should_retry."""
        client = AsyncAPIClient(
            oauth_client=oauth_client,
            retry_config=retry_config,
        )

        # Deve fazer retry em 500, 502, 503, 504, 429
        assert client._should_retry(500, 0) is True
        assert client._should_retry(502, 0) is True
        assert client._should_retry(503, 0) is True
        assert client._should_retry(504, 0) is True
        assert client._should_retry(429, 0) is True

        # NÃO deve fazer retry em 400, 401, 404, etc
        assert client._should_retry(400, 0) is False
        assert client._should_retry(401, 0) is False
        assert client._should_retry(404, 0) is False

        # NÃO deve fazer retry quando esgota tentativas
        assert (
            client._should_retry(500, 2) is False
        )  # max_tentativas=3, tentativa=2 (última)

    @pytest.mark.asyncio
    async def test_async_sicoob_com_retry_config(self):
        """Testa que AsyncSicoob aceita retry_config e o passa para AsyncAPIClient."""
        retry_config = {
            'max_tentativas': 5,
            'delay_inicial': 0.5,
            'backoff_exponencial': False,
            'codigos_retry': [500, 503],
        }

        with patch('sicoob.async_client.OAuth2Client'):
            client = AsyncSicoob(
                client_id='test_client',
                certificado_pfx=b'test_cert',
                senha_pfx='test_password',
                retry_config=retry_config,
            )

            # Verifica que retry_config foi passado para AsyncAPIClient
            assert client._api_client.retry_config == retry_config


class TestAsyncAPIClientRetryIntegration:
    """Testes de integração para retry global."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_retry_em_timeout(self):
        """Testa que retry funciona em caso de timeout."""
        oauth_client = Mock(spec=OAuth2Client)
        oauth_client.get_access_token.return_value = 'mock_token'

        retry_config = {
            'max_tentativas': 2,
            'delay_inicial': 0.1,
            'backoff_exponencial': True,
            'codigos_retry': [500, 502, 503, 504, 429],
        }

        client = AsyncAPIClient(
            oauth_client=oauth_client,
            retry_config=retry_config,
        )
        await client._ensure_session()

        call_count = 0

        async def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                raise asyncio.TimeoutError('Request timeout')

            # Segunda tentativa sucede
            mock_response = AsyncMock(spec=ClientResponse)
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"data": "success"}')
            mock_response.json = AsyncMock(return_value={'data': 'success'})
            return mock_response

        try:
            with patch.object(client._session, 'request') as mock_request:
                mock_request.return_value.__aenter__.side_effect = (
                    mock_request_side_effect
                )

                result = await client._make_request(
                    'GET', 'https://api.test.com/endpoint', 'test_scope'
                )

                assert call_count == 2
                assert result == {'data': 'success'}
        finally:
            await client._session.close()


class TestAsyncSicoobCredenciaisExplicitas:
    """AsyncSicoob não lê credenciais nem ambiente do processo."""

    @pytest.mark.parametrize('client_id', [None, '', '  '])
    def test_client_id_ausente_nao_usa_ambiente(self, client_id):
        with patch.dict('os.environ', {'SICOOB_CLIENT_ID': 'do-ambiente'}):
            with pytest.raises(ValueError, match='client_id'):
                AsyncSicoob(client_id=client_id, certificado_pfx=b'x', senha_pfx='s')

    def test_ambiente_desconhecido_e_erro(self):
        with pytest.raises(ValueError, match='Ambiente desconhecido'):
            AsyncSicoob(client_id='id', environment='prd')

    def test_ambiente_por_instancia(self):
        from sicoob.config import Environment, SicoobConfig

        with patch('sicoob.async_client.OAuth2Client') as oauth:
            client = AsyncSicoob(client_id='id', environment='sandbox')
        assert client.config.is_sandbox
        assert oauth.call_args.kwargs['config'] is client.config
        assert SicoobConfig.get_current_config().environment is Environment.PRODUCTION

    def test_from_env(self):
        env = {'SICOOB_CLIENT_ID': 'cid', 'SICOOB_ENVIRONMENT': 'sandbox'}
        with patch.dict('os.environ', env):
            with patch('sicoob.async_client.OAuth2Client'):
                client = AsyncSicoob.from_env(dotenv=False)
        assert client.client_id == 'cid'
        assert client.config.is_sandbox


class TestAsyncHeadersSandbox:
    def _client(self, ambiente, token=None):
        from sicoob.config import SicoobConfig

        oauth = Mock()
        oauth.config = SicoobConfig.config_for(ambiente)
        oauth.client_id = 'cid'
        oauth.sandbox_token = token
        oauth.get_access_token.return_value = 'tok-oauth'
        return AsyncAPIClient(oauth_client=oauth), oauth

    def test_sandbox_usa_token_informado(self):
        client, oauth = self._client('sandbox', 'tok-sb')
        headers = client._get_headers('x')
        assert headers['Authorization'] == 'Bearer tok-sb'
        assert headers['client_id'] == 'cid'
        oauth.get_access_token.assert_not_called()

    def test_producao_usa_oauth(self):
        client, oauth = self._client('production')
        headers = client._get_headers('x')
        assert headers['Authorization'] == 'Bearer tok-oauth'
        assert client._get_base_url() == 'https://api.sicoob.com.br'


class TestAsyncLoggingPorInstancia:
    """Logs HTTP com prévia de resposta seguem a config da instância."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('ambiente', 'espera_log'), [('production', False), ('sandbox', True)]
    )
    async def test_log_de_resposta(self, ambiente, espera_log):
        import logging
        from dataclasses import replace

        from sicoob.config import SicoobConfig

        oauth = Mock()
        # Sem certificado real no teste: desliga só a exigência de mTLS.
        oauth.config = replace(
            SicoobConfig.config_for(ambiente), require_certificate=False
        )
        oauth.client_id = 'cid'
        oauth.sandbox_token = 'tok'
        oauth.get_access_token.return_value = 'tok'
        client = AsyncAPIClient(oauth_client=oauth)
        await client._ensure_session()
        resposta = AsyncMock(spec=ClientResponse)
        resposta.status = 200
        resposta.text = AsyncMock(return_value='{"saldo": 1}')
        resposta.json = AsyncMock(return_value={'saldo': 1})
        logger = logging.getLogger('sicoob.async_client')
        nivel = logger.level
        logger.setLevel(logging.DEBUG)  # nível global "vazado" de um sandbox
        try:
            with (
                patch.object(client._session, 'request') as req,
                patch.object(logger, 'debug') as debug,
            ):
                req.return_value.__aenter__.return_value = resposta
                await client._make_request('GET', 'https://x/y', 's')
            mensagens = [c.args[0] for c in debug.call_args_list]
            assert any('Resposta HTTP' in m for m in mensagens) is espera_log
        finally:
            logger.setLevel(nivel)
            await client._session.close()
