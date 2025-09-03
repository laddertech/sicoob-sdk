"""Testes para funcionalidades assíncronas do Sicoob SDK."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

import pytest
import aiohttp

from sicoob.async_client import (
    AsyncAPIClient,
    AsyncSicoob,
    AsyncContaCorrenteAPI,
    AsyncCobrancaAPI,
    gather_with_concurrency,
    async_batch_processor,
)
from sicoob.auth import OAuth2Client
from sicoob.exceptions import SicoobError, RespostaInvalidaError


class TestAsyncAPIClient:
    """Testes para cliente HTTP assíncrono."""

    @pytest.fixture
    async def mock_oauth_client(self):
        """Mock do cliente OAuth2."""
        oauth = MagicMock(spec=OAuth2Client)
        oauth.get_access_token.return_value = "test_token"
        oauth.client_id = "test_client_id"
        return oauth

    @pytest.fixture
    async def api_client(self, mock_oauth_client):
        """Instância do cliente API para testes."""
        client = AsyncAPIClient(
            oauth_client=mock_oauth_client,
            max_concurrent_requests=5,
            request_timeout=10
        )
        await client._ensure_session()
        yield client
        await client._session.close()

    @pytest.mark.asyncio
    async def test_api_client_initialization(self, mock_oauth_client):
        """Testa inicialização do cliente API."""
        client = AsyncAPIClient(
            oauth_client=mock_oauth_client,
            max_concurrent_requests=10,
            request_timeout=30
        )
        
        assert client.oauth_client is mock_oauth_client
        assert client.max_concurrent_requests == 10
        assert client.request_timeout == 30
        assert client._semaphore._value == 10

    @pytest.mark.asyncio
    async def test_session_management(self, mock_oauth_client):
        """Testa gerenciamento de sessão."""
        # Context manager
        async with AsyncAPIClient(oauth_client=mock_oauth_client) as client:
            await client._ensure_session()
            assert client._session is not None
            assert isinstance(client._session, aiohttp.ClientSession)

    @pytest.mark.asyncio
    async def test_headers_generation(self, api_client):
        """Testa geração de headers."""
        with patch('sicoob.config.SicoobConfig.is_sandbox', return_value=False):
            headers = api_client._get_headers("test_scope")
            
            assert 'Authorization' in headers
            assert headers['Authorization'] == 'Bearer test_token'
            assert headers['Content-Type'] == 'application/json'
            assert headers['client_id'] == 'test_client_id'
            assert 'SicoobAsyncAPIClient' in headers['User-Agent']

    @pytest.mark.asyncio
    async def test_sandbox_headers(self, api_client):
        """Testa headers em modo sandbox."""
        with patch('sicoob.config.SicoobConfig.is_sandbox', return_value=True), \
             patch.dict('os.environ', {
                 'SICOOB_SANDBOX_TOKEN': 'sandbox_token',
                 'SICOOB_SANDBOX_CLIENT_ID': 'sandbox_client'
             }):
            headers = api_client._get_headers("test_scope")
            
            assert headers['Authorization'] == 'Bearer sandbox_token'
            assert headers['client_id'] == 'sandbox_client'

    @pytest.mark.asyncio
    async def test_successful_request(self, api_client):
        """Testa requisição bem-sucedida."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content_type = 'application/json'
        mock_response.text.return_value = '{"success": true}'
        mock_response.json.return_value = {"success": True}

        with patch.object(api_client._session, 'request') as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response
            mock_request.return_value.__aexit__.return_value = None
            
            result = await api_client._make_request(
                'GET',
                'https://api.sicoob.com.br/test',
                'test_scope'
            )
            
            assert result == {"success": True}
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_http_error_handling(self, api_client):
        """Testa tratamento de erros HTTP."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text.return_value = '{"error": "Not found"}'
        mock_response.json.return_value = {"message": "Resource not found"}

        with patch.object(api_client._session, 'request') as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response
            mock_request.return_value.__aexit__.return_value = None
            
            with pytest.raises(SicoobError) as exc_info:
                await api_client._make_request(
                    'GET',
                    'https://api.sicoob.com.br/test',
                    'test_scope'
                )
            
            assert "Resource not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_json_decode_error(self, api_client):
        """Testa erro de decodificação JSON."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content_type = 'application/json'
        mock_response.text.return_value = 'invalid json'
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch.object(api_client._session, 'request') as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response
            mock_request.return_value.__aexit__.return_value = None
            
            with pytest.raises(RespostaInvalidaError):
                await api_client._make_request(
                    'GET',
                    'https://api.sicoob.com.br/test',
                    'test_scope'
                )

    @pytest.mark.asyncio
    async def test_timeout_error(self, api_client):
        """Testa timeout de requisição."""
        with patch.object(api_client._session, 'request') as mock_request:
            mock_request.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(SicoobError) as exc_info:
                await api_client._make_request(
                    'GET',
                    'https://api.sicoob.com.br/test',
                    'test_scope'
                )
            
            assert "Timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_concurrency_control(self, mock_oauth_client):
        """Testa controle de concorrência."""
        client = AsyncAPIClient(
            oauth_client=mock_oauth_client,
            max_concurrent_requests=2
        )
        
        async with client:
            # Simula requisições que demoram
            async def slow_request():
                async with client._semaphore:
                    await asyncio.sleep(0.1)
                    return "result"
            
            start_time = time.time()
            
            # 4 requisições com limite de 2 concorrentes
            tasks = [slow_request() for _ in range(4)]
            results = await asyncio.gather(*tasks)
            
            duration = time.time() - start_time
            
            # Deve levar pelo menos 0.2s (2 lotes de 0.1s cada)
            assert duration >= 0.2
            assert len(results) == 4
            assert all(r == "result" for r in results)


class TestAsyncSicoob:
    """Testes para cliente principal assíncrono."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Testa inicialização do cliente."""
        with patch.dict('os.environ', {
            'SICOOB_CLIENT_ID': 'test_client',
            'SICOOB_CERTIFICADO_PFX': '/path/to/cert.pfx',
            'SICOOB_SENHA_PFX': 'password'
        }):
            async with AsyncSicoob() as client:
                assert client.client_id == 'test_client'
                assert client.certificado_pfx == '/path/to/cert.pfx'
                assert client.senha_pfx == 'password'

    @pytest.mark.asyncio
    async def test_client_validation(self):
        """Testa validação de credenciais."""
        with pytest.raises(ValueError, match="client_id é obrigatório"):
            AsyncSicoob()

    @pytest.mark.asyncio
    async def test_api_properties(self):
        """Testa propriedades das APIs."""
        with patch.dict('os.environ', {'SICOOB_CLIENT_ID': 'test'}):
            async with AsyncSicoob() as client:
                assert hasattr(client, 'conta_corrente')
                assert hasattr(client, 'cobranca')
                assert isinstance(client.conta_corrente, AsyncContaCorrenteAPI)
                assert isinstance(client.cobranca, AsyncCobrancaAPI)


class TestAsyncContaCorrenteAPI:
    """Testes para API de conta corrente assíncrona."""

    @pytest.fixture
    async def api_client(self):
        """Mock do cliente API."""
        client = AsyncMock(spec=AsyncAPIClient)
        client._get_base_url.return_value = "https://api.sicoob.com.br"
        return client

    @pytest.fixture
    def conta_api(self, api_client):
        """Instância da API de conta corrente."""
        return AsyncContaCorrenteAPI(api_client)

    @pytest.mark.asyncio
    async def test_get_extrato(self, conta_api, api_client):
        """Testa consulta de extrato."""
        expected_response = {
            "movimentos": [
                {"data": "2024-01-01", "valor": 100.00, "descricao": "PIX"}
            ]
        }
        api_client._make_request.return_value = expected_response

        result = await conta_api.get_extrato("2024-01-01", "2024-01-31")

        assert result == expected_response
        api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/conta-corrente/extrato',
            scope='cco_extrato cco_consulta',
            params={'dataInicio': '2024-01-01', 'dataFim': '2024-01-31'}
        )

    @pytest.mark.asyncio
    async def test_get_extrato_com_conta(self, conta_api, api_client):
        """Testa consulta de extrato com número da conta."""
        api_client._make_request.return_value = {"extrato": "data"}

        await conta_api.get_extrato("2024-01-01", "2024-01-31", "123456")

        api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/conta-corrente/extrato',
            scope='cco_extrato cco_consulta',
            params={
                'dataInicio': '2024-01-01',
                'dataFim': '2024-01-31',
                'numeroConta': '123456'
            }
        )

    @pytest.mark.asyncio
    async def test_get_saldo(self, conta_api, api_client):
        """Testa consulta de saldo."""
        expected_response = {"saldo": 1500.50}
        api_client._make_request.return_value = expected_response

        result = await conta_api.get_saldo()

        assert result == expected_response
        api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/conta-corrente/saldo',
            scope='cco_consulta',
            params={}
        )


class TestAsyncCobrancaAPI:
    """Testes para API de cobrança assíncrona."""

    @pytest.fixture
    async def api_client(self):
        """Mock do cliente API."""
        client = AsyncMock(spec=AsyncAPIClient)
        client._get_base_url.return_value = "https://api.sicoob.com.br"
        return client

    @pytest.fixture
    def cobranca_api(self, api_client):
        """Instância da API de cobrança."""
        return AsyncCobrancaAPI(api_client)

    @pytest.mark.asyncio
    async def test_criar_cobranca_pix(self, cobranca_api, api_client):
        """Testa criação de cobrança PIX."""
        dados = {
            "valor": {"original": "100.50"},
            "calendario": {"expiracao": 3600}
        }
        expected_response = {"txid": "test123", "status": "ATIVA"}
        api_client._make_request.return_value = expected_response

        result = await cobranca_api.criar_cobranca_pix("test123", dados)

        assert result == expected_response
        api_client._make_request.assert_called_once_with(
            'PUT',
            'https://api.sicoob.com.br/pix/cob/test123',
            scope='cob.write',
            json=dados
        )

    @pytest.mark.asyncio
    async def test_consultar_cobranca_pix(self, cobranca_api, api_client):
        """Testa consulta de cobrança PIX."""
        expected_response = {"txid": "test123", "status": "PAGA"}
        api_client._make_request.return_value = expected_response

        result = await cobranca_api.consultar_cobranca_pix("test123")

        assert result == expected_response
        api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/pix/cob/test123',
            scope='cob.read'
        )

    @pytest.mark.asyncio
    async def test_listar_cobrancas_pix(self, cobranca_api, api_client):
        """Testa listagem de cobranças PIX."""
        expected_response = {"cobs": [{"txid": "test123"}]}
        api_client._make_request.return_value = expected_response

        result = await cobranca_api.listar_cobrancas_pix(
            "2024-01-01T00:00:00Z",
            "2024-01-31T23:59:59Z",
            status="ATIVA"
        )

        assert result == expected_response
        api_client._make_request.assert_called_once_with(
            'GET',
            'https://api.sicoob.com.br/pix/cob',
            scope='cob.read',
            params={
                'inicio': '2024-01-01T00:00:00Z',
                'fim': '2024-01-31T23:59:59Z',
                'status': 'ATIVA'
            }
        )


class TestAsyncUtilities:
    """Testes para utilitários assíncronos."""

    @pytest.mark.asyncio
    async def test_gather_with_concurrency(self):
        """Testa execução com limite de concorrência."""
        async def slow_task(delay, result):
            await asyncio.sleep(delay)
            return result

        start_time = time.time()
        
        # 4 tasks com limite de 2 concorrentes
        tasks = [
            slow_task(0.1, f"result_{i}")
            for i in range(4)
        ]
        
        results = await gather_with_concurrency(tasks, max_concurrency=2)
        
        duration = time.time() - start_time
        
        # Deve levar pelo menos 0.2s (2 lotes de 0.1s cada)
        assert duration >= 0.2
        assert len(results) == 4
        assert all(r.startswith("result_") for r in results)

    @pytest.mark.asyncio
    async def test_async_batch_processor(self):
        """Testa processamento em lote assíncrono."""
        async def process_item(item):
            await asyncio.sleep(0.01)
            return item * 2

        items = list(range(10))
        
        async with async_batch_processor(
            items,
            process_item,
            batch_size=3,
            max_concurrency=2
        ) as results:
            assert len(results) == 10
            assert results == [i * 2 for i in items]


class TestAsyncIntegration:
    """Testes de integração assíncrona."""

    @pytest.mark.asyncio
    async def test_high_concurrency_scenario(self):
        """Testa cenário de alta concorrência."""
        # Simula múltiplas requisições concorrentes
        async def mock_api_call(i):
            await asyncio.sleep(0.01)  # Simula latência de rede
            return {"id": i, "status": "processed"}

        start_time = time.time()
        
        # 50 requisições concorrentes
        tasks = [mock_api_call(i) for i in range(50)]
        results = await gather_with_concurrency(tasks, max_concurrency=10)
        
        duration = time.time() - start_time
        
        assert len(results) == 50
        assert all("id" in r and "status" in r for r in results)
        # Com concorrência de 10, deve ser mais rápido que execução sequencial
        assert duration < 0.5  # Muito mais rápido que 50 * 0.01 = 0.5s

    @pytest.mark.asyncio
    async def test_error_handling_in_batch(self):
        """Testa tratamento de erro em operações em lote."""
        async def task_with_error(i):
            if i == 5:
                raise ValueError(f"Error in task {i}")
            return f"success_{i}"

        tasks = [task_with_error(i) for i in range(10)]
        
        # Deve propagar o erro
        with pytest.raises(ValueError, match="Error in task 5"):
            await gather_with_concurrency(tasks, max_concurrency=3)

    @pytest.mark.asyncio
    async def test_mixed_response_times(self):
        """Testa tarefas com tempos de resposta variados."""
        async def variable_delay_task(delay):
            await asyncio.sleep(delay)
            return delay

        # Tarefas com delays diferentes
        delays = [0.1, 0.05, 0.15, 0.02, 0.08]
        tasks = [variable_delay_task(d) for d in delays]
        
        start_time = time.time()
        results = await gather_with_concurrency(tasks, max_concurrency=3)
        duration = time.time() - start_time
        
        # Resultados devem corresponder aos delays
        assert results == delays
        # Tempo total deve ser otimizado pela concorrência
        assert duration < sum(delays)  # Mais rápido que execução sequencial