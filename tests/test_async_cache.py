"""Testes para sistema de cache assíncrono."""

import asyncio
import shutil
import tempfile
import time

import pytest
import pytest_asyncio

from sicoob.async_cache import (
    AsyncCacheManager,
    AsyncMemoryCacheBackend,
    async_cached,
    get_default_async_cache,
)
from sicoob.cache import CacheConfig, CacheEntry, EvictionPolicy
from sicoob.exceptions import (
    CacheError,
    CacheSerializationError,
)


class TestAsyncMemoryCacheBackend:
    """Testes para backend de memória assíncrono."""

    @pytest_asyncio.fixture
    async def backend(self):
        """Instância do backend para testes."""
        return AsyncMemoryCacheBackend()

    @pytest.mark.asyncio
    async def test_basic_operations(self, backend):
        """Testa operações básicas."""
        # Set e get
        entry = CacheEntry(
            key='test_key', value='test_value', created_at=time.time(), expires_at=0
        )

        await backend.set('test_key', entry)
        retrieved = await backend.get('test_key')

        assert retrieved is not None
        assert retrieved.value == 'test_value'
        assert retrieved.access_count == 1  # mark_accessed foi chamado

    @pytest.mark.asyncio
    async def test_delete(self, backend):
        """Testa remoção."""
        entry = CacheEntry(
            key='test_key', value='test_value', created_at=time.time(), expires_at=0
        )

        await backend.set('test_key', entry)
        assert await backend.get('test_key') is not None

        assert await backend.delete('test_key') is True
        assert await backend.get('test_key') is None
        assert await backend.delete('nonexistent') is False

    @pytest.mark.asyncio
    async def test_clear(self, backend):
        """Testa limpeza completa."""
        entry1 = CacheEntry(
            key='key1', value='value1', created_at=time.time(), expires_at=0
        )
        entry2 = CacheEntry(
            key='key2', value='value2', created_at=time.time(), expires_at=0
        )

        await backend.set('key1', entry1)
        await backend.set('key2', entry2)

        assert await backend.size() == 2

        await backend.clear()
        assert await backend.size() == 0
        assert await backend.keys() == []

    @pytest.mark.asyncio
    async def test_keys_and_size(self, backend):
        """Testa listagem de chaves e tamanho."""
        # Inicialmente vazio
        assert await backend.size() == 0
        assert await backend.keys() == []

        # Adiciona entradas
        for i in range(3):
            entry = CacheEntry(
                key=f'key_{i}', value=f'value_{i}', created_at=time.time(), expires_at=0
            )
            await backend.set(f'key_{i}', entry)

        assert await backend.size() == 3
        keys = await backend.keys()
        assert len(keys) == 3
        assert all(k.startswith('key_') for k in keys)

    @pytest.mark.asyncio
    async def test_concurrent_access(self, backend):
        """Testa acesso concorrente."""
        entry = CacheEntry(
            key='concurrent_key',
            value='concurrent_value',
            created_at=time.time(),
            expires_at=0,
        )

        async def writer():
            await backend.set('concurrent_key', entry)

        async def reader():
            result = await backend.get('concurrent_key')
            return result.value if result else None

        # Executa operações concorrentes
        tasks = [writer()] + [reader() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # Pelo menos algumas leituras devem ter sucesso
        read_results = results[1:]  # Remove resultado do writer (None)
        successful_reads = [r for r in read_results if r == 'concurrent_value']
        assert len(successful_reads) > 0


class TestAsyncCacheManager:
    """Testes para gerenciador de cache assíncrono."""

    @pytest_asyncio.fixture
    async def cache_manager(self):
        """Instância do cache manager para testes."""
        config = CacheConfig(
            default_ttl=300, max_size=100, enable_compression=True, cleanup_interval=1
        )
        manager = AsyncCacheManager(config)
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_basic_cache_operations(self, cache_manager):
        """Testa operações básicas do cache."""
        # Set e get
        await cache_manager.set('key1', 'value1')
        assert await cache_manager.get('key1') == 'value1'

        # Chave inexistente
        assert await cache_manager.get('nonexistent') is None

        # Delete
        assert await cache_manager.delete('key1') is True
        assert await cache_manager.get('key1') is None
        assert await cache_manager.delete('key1') is False

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache_manager):
        """Testa expiração por TTL."""
        await cache_manager.set('expires', 'value', ttl=0.1)

        assert await cache_manager.get('expires') == 'value'
        await asyncio.sleep(0.2)
        assert await cache_manager.get('expires') is None

    @pytest.mark.asyncio
    async def test_compression(self, cache_manager):
        """Testa compressão de dados grandes."""
        large_data = {'data': 'x' * 1000, 'numbers': list(range(100))}

        await cache_manager.set('large_key', large_data)
        retrieved = await cache_manager.get('large_key')

        assert retrieved == large_data

    @pytest.mark.asyncio
    async def test_tag_invalidation(self, cache_manager):
        """Testa invalidação por tags."""
        await cache_manager.set('key1', 'value1', tags=['group1', 'group2'])
        await cache_manager.set('key2', 'value2', tags=['group1'])
        await cache_manager.set('key3', 'value3', tags=['group2'])
        await cache_manager.set('key4', 'value4')  # Sem tags

        # Invalida group1
        removed = await cache_manager.invalidate_by_tag('group1')
        assert removed == 2

        assert await cache_manager.get('key1') is None
        assert await cache_manager.get('key2') is None
        assert await cache_manager.get('key3') == 'value3'
        assert await cache_manager.get('key4') == 'value4'

    @pytest.mark.asyncio
    async def test_pattern_invalidation(self, cache_manager):
        """Testa invalidação por padrão regex."""
        await cache_manager.set('user:123:profile', 'profile1')
        await cache_manager.set('user:456:profile', 'profile2')
        await cache_manager.set('user:123:settings', 'settings1')
        await cache_manager.set('order:789', 'order1')

        # Invalida todos os profiles de usuário
        removed = await cache_manager.invalidate_by_pattern(r'^user:\d+:profile$')
        assert removed == 2

        assert await cache_manager.get('user:123:profile') is None
        assert await cache_manager.get('user:456:profile') is None
        assert await cache_manager.get('user:123:settings') == 'settings1'
        assert await cache_manager.get('order:789') == 'order1'

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_automatic_cleanup(self, cache_manager):
        """Testa limpeza automática."""
        # Para task de limpeza para controlar quando ela executa
        await cache_manager.shutdown()

        # Adiciona entrada que expira rapidamente
        await cache_manager.set('expires_soon', 'value', ttl=0.1)

        # Força limpeza manual
        await asyncio.sleep(0.2)
        await cache_manager._cleanup_expired()

        assert await cache_manager.get('expires_soon') is None

    @pytest.mark.asyncio
    async def test_async_decorator(self, cache_manager):
        """Testa decorator assíncrono."""
        call_count = 0

        @cache_manager.cached(ttl=300, key_prefix='func:')
        async def expensive_async_function(x: int, y: int) -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simula operação assíncrona
            return x + y

        # Primeira chamada
        result1 = await expensive_async_function(1, 2)
        assert result1 == 3
        assert call_count == 1

        # Segunda chamada (deveria usar cache)
        result2 = await expensive_async_function(1, 2)
        assert result2 == 3
        assert call_count == 1  # Não deveria ter chamado a função novamente

        # Chamada com argumentos diferentes
        result3 = await expensive_async_function(2, 3)
        assert result3 == 5
        assert call_count == 2

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_stats(self, cache_manager):
        """Testa estatísticas do cache."""
        # Gera hits e misses
        await cache_manager.get('nonexistent')  # miss
        await cache_manager.set('key', 'value')
        await cache_manager.get('key')  # hit

        stats = await cache_manager.get_stats()

        assert stats['hits'] >= 1
        assert stats['misses'] >= 1
        assert stats['hit_rate'] > 0
        assert stats['entry_count'] >= 1

    @pytest.mark.asyncio
    async def test_error_handling(self, cache_manager):
        """Testa tratamento de erros."""
        # Teste de padrão regex inválido
        with pytest.raises(CacheError):
            await cache_manager.invalidate_by_pattern('(invalid[regex')


class TestAsyncCacheGlobal:
    """Testes para cache global assíncrono."""

    @pytest.mark.asyncio
    async def test_default_cache_instance(self):
        """Testa instância padrão do cache."""
        cache1 = await get_default_async_cache()
        cache2 = await get_default_async_cache()

        assert cache1 is cache2  # Deve ser a mesma instância

    @pytest.mark.asyncio
    async def test_global_decorator(self):
        """Testa decorator global."""
        call_count = 0

        @async_cached(ttl=300, key_prefix='global:')
        async def test_async_function(value: str) -> str:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return f'processed_{value}'

        # Primeira chamada
        result1 = await test_async_function('test')
        assert result1 == 'processed_test'
        assert call_count == 1

        # Segunda chamada (cache hit)
        result2 = await test_async_function('test')
        assert result2 == 'processed_test'
        assert call_count == 1


class TestAsyncCacheIntegration:
    """Testes de integração para cache assíncrono."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_cache_with_disk_persistence(self):
        """Testa cache com persistência em disco."""
        temp_dir = tempfile.mkdtemp()

        try:
            config = CacheConfig(default_ttl=300, max_size=5, persist_path=temp_dir)

            # Primeira instância
            cache1 = AsyncCacheManager(config)

            # Adiciona dados que forçam despejo para disco
            for i in range(10):
                await cache1.set(f'key_{i}', f'value_{i}')

            await cache1.shutdown()

            # Segunda instância (simulando reinício)
            cache2 = AsyncCacheManager(config)

            # Alguns dados devem estar disponíveis (seja na memória ou disco)
            recovered_count = 0
            for i in range(10):
                value = await cache2.get(f'key_{i}')
                if value == f'value_{i}':
                    recovered_count += 1

            assert recovered_count > 0  # Pelo menos alguns dados foram recuperados

            await cache2.shutdown()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Testa eficiência de memória com compressão."""
        config = CacheConfig(
            max_size=50, enable_compression=True, eviction_policy=EvictionPolicy.LFU
        )
        cache = AsyncCacheManager(config)

        # Dados grandes compressíveis
        large_compressible = 'A' * 10000

        # Adiciona muitos dados para forçar despejo
        for i in range(100):
            if i % 10 == 0:
                await cache.set(f'large_{i}', large_compressible)
            else:
                await cache.set(f'item_{i}', f'value_{i}')

        # Verifica que cache não excedeu limite
        stats = await cache.get_stats()
        assert stats['entry_count'] <= 50

        # Verifica que alguns dados grandes ainda existem (compressão funcionou)
        large_items_found = 0
        for i in range(0, 100, 10):
            value = await cache.get(f'large_{i}')
            if value == large_compressible:
                large_items_found += 1

        assert large_items_found > 0

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Testa recuperação de erros."""
        cache = AsyncCacheManager()

        # Simula erro de serialização
        class UnserializableObject:
            def __reduce__(self):
                raise TypeError('Cannot serialize this object')

        with pytest.raises(CacheSerializationError):
            await cache.set('bad_key', UnserializableObject())

        # Cache deve continuar funcionando normalmente
        await cache.set('good_key', 'good_value')
        assert await cache.get('good_key') == 'good_value'

        await cache.shutdown()
