"""Sistema de cache assíncrono para o Sicoob SDK.

Este módulo fornece funcionalidades de cache assíncrono otimizadas para
operações de alta concorrência, permitindo cache não-bloqueante em
cenários de high-throughput.

Classes:
    AsyncCacheManager: Gerenciador de cache assíncrono
    AsyncCacheBackend: Interface para backends assíncronos
    AsyncMemoryCacheBackend: Backend de memória assíncrono
    AsyncDiskCacheBackend: Backend de disco assíncrono

Example:
    >>> import asyncio
    >>> from sicoob.async_cache import AsyncCacheManager
    >>>
    >>> async def exemplo_cache():
    ...     cache = AsyncCacheManager()
    ...
    ...     # Cache assíncrono com decorator
    ...     @cache.cached(ttl=300)
    ...     async def consultar_dados_api(txid):
    ...         # Simula consulta à API
    ...         return await client.pix.consultar_cobranca(txid)
    ...
    ...     # Uso paralelo do cache
    ...     tasks = [consultar_dados_api(f"txid_{i}") for i in range(100)]
    ...     results = await asyncio.gather(*tasks)
"""

import asyncio
import pickle
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

try:
    import aiofiles

    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False

from sicoob.cache import CacheConfig, CacheEntry, CacheMetrics, EvictionPolicy
from sicoob.exceptions import (
    CacheBackendError,
    CacheError,
    CacheSerializationError,
)

# from sicoob.logging_config import get_logger  # Temporariamente comentado

T = TypeVar('T')


class AsyncCacheBackend(ABC):
    """Interface para backends de cache assíncronos."""

    @abstractmethod
    async def get(self, key: str) -> CacheEntry | None:
        """Obtém entrada do cache de forma assíncrona."""
        pass

    @abstractmethod
    async def set(self, key: str, entry: CacheEntry) -> None:
        """Define entrada no cache de forma assíncrona."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Remove entrada do cache de forma assíncrona."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Limpa todo o cache de forma assíncrona."""
        pass

    @abstractmethod
    async def keys(self) -> list[str]:
        """Lista todas as chaves de forma assíncrona."""
        pass

    @abstractmethod
    async def size(self) -> int:
        """Retorna número de entradas de forma assíncrona."""
        pass


class AsyncMemoryCacheBackend(AsyncCacheBackend):
    """Backend de cache em memória com suporte assíncrono."""

    def __init__(self) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> CacheEntry | None:
        """Obtém entrada do cache."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry:
                entry.mark_accessed()
            return entry

    async def set(self, key: str, entry: CacheEntry) -> None:
        """Define entrada no cache."""
        async with self._lock:
            self._cache[key] = entry

    async def delete(self, key: str) -> bool:
        """Remove entrada do cache."""
        async with self._lock:
            return self._cache.pop(key, None) is not None

    async def clear(self) -> None:
        """Limpa todo o cache."""
        async with self._lock:
            self._cache.clear()

    async def keys(self) -> list[str]:
        """Lista todas as chaves."""
        async with self._lock:
            return list(self._cache.keys())

    async def size(self) -> int:
        """Retorna número de entradas."""
        async with self._lock:
            return len(self._cache)


class AsyncDiskCacheBackend(AsyncCacheBackend):
    """Backend de cache em disco com suporte assíncrono."""

    def __init__(self, cache_dir: str = '.cache') -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()

    async def _get_lock(self, key: str) -> asyncio.Lock:
        """Obtém lock específico para uma chave."""
        async with self._locks_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    def _get_cache_path(self, key: str) -> Path:
        """Retorna o caminho do arquivo de cache para uma chave."""
        # Hash da chave para evitar problemas com caracteres especiais
        import hashlib

        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.cache_dir / f'{key_hash}.cache'

    async def get(self, key: str) -> CacheEntry | None:
        """Obtém entrada do cache em disco."""
        lock = await self._get_lock(key)
        async with lock:
            cache_path = self._get_cache_path(key)

            if not cache_path.exists():
                return None

            try:
                if HAS_AIOFILES:
                    async with aiofiles.open(cache_path, 'rb') as f:
                        data = await f.read()
                        # nosec B301 - pickle usado para cache interno controlado
                        entry = pickle.loads(data)
                        entry.mark_accessed()
                        return entry
                else:
                    # Fallback para operações síncronas
                    def read_cache() -> CacheEntry:
                        with open(cache_path, 'rb') as f:
                            # nosec B301 - pickle usado para cache interno controlado
                            return pickle.load(f)

                    entry = await asyncio.to_thread(read_cache)
                    entry.mark_accessed()
                    return entry
            except Exception:
                # Remove arquivo corrompido
                try:
                    cache_path.unlink(missing_ok=True)
                except (FileNotFoundError, PermissionError, OSError):
                    pass
                return None

    async def set(self, key: str, entry: CacheEntry) -> None:
        """Define entrada no cache em disco."""
        lock = await self._get_lock(key)
        async with lock:
            cache_path = self._get_cache_path(key)

            try:
                data = pickle.dumps(entry)
                if HAS_AIOFILES:
                    async with aiofiles.open(cache_path, 'wb') as f:
                        await f.write(data)
                else:
                    # Fallback para operações síncronas
                    def write_cache() -> None:
                        with open(cache_path, 'wb') as f:
                            f.write(data)

                    await asyncio.to_thread(write_cache)
            except Exception as e:
                raise CacheBackendError(
                    f'Erro ao salvar no cache de disco: {e!s}',
                    backend='disk',
                    original_error=e,
                ) from e

    async def delete(self, key: str) -> bool:
        """Remove entrada do cache em disco."""
        lock = await self._get_lock(key)
        async with lock:
            cache_path = self._get_cache_path(key)

            if cache_path.exists():
                try:
                    cache_path.unlink()
                    return True
                except Exception:
                    return False
            return False

    async def clear(self) -> None:
        """Limpa todo o cache em disco."""
        cache_files = list(self.cache_dir.glob('*.cache'))

        # Remove arquivos em paralelo (com limite de concorrência)
        semaphore = asyncio.Semaphore(10)

        async def remove_file(file_path: Path) -> None:
            async with semaphore:
                try:
                    file_path.unlink(missing_ok=True)
                except Exception:
                    # Log ignorado - remoção de cache é best-effort
                    pass

        if cache_files:
            await asyncio.gather(*[remove_file(f) for f in cache_files])

    async def keys(self) -> list[str]:
        """Lista todas as chaves."""
        # Para simplificar, retornamos os hashes dos arquivos
        cache_files = list(self.cache_dir.glob('*.cache'))
        return [f.stem for f in cache_files]

    async def size(self) -> int:
        """Retorna número de entradas."""
        cache_files = list(self.cache_dir.glob('*.cache'))
        return len(cache_files)


class AsyncCacheManager:
    """Gerenciador de cache assíncrono com múltiplas funcionalidades."""

    def __init__(self, config: CacheConfig | None = None) -> None:
        """Inicializa o gerenciador de cache assíncrono.

        Args:
            config: Configuração do cache
        """
        self.config = config or CacheConfig()
        # self.logger = get_logger(__name__)  # Temporariamente comentado

        # Inicializa backends
        self.memory_backend = AsyncMemoryCacheBackend()
        self.disk_backend = None

        if self.config.persist_path:
            self.disk_backend = AsyncDiskCacheBackend(self.config.persist_path)

        # Métricas e controle
        self.metrics = CacheMetrics()
        self._invalidation_patterns: dict[str, set] = {}
        self._invalidation_groups: dict[str, dict[str, Any]] = {}

        # Limpeza automática
        self._cleanup_task: asyncio.Task | None = None
        self._shutdown = False

        if self.config.cleanup_interval > 0:
            self._start_cleanup_task()

    def _start_cleanup_task(self) -> None:
        """Inicia task de limpeza automática."""

        async def cleanup_loop() -> None:
            while not self._shutdown:
                try:
                    await asyncio.sleep(self.config.cleanup_interval)
                    if not self._shutdown:
                        await self._cleanup_expired()
                except Exception:
                    # self.logger.error(f"Erro na limpeza automática: {e!s}")  # Temporariamente comentado
                    pass

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def _cleanup_expired(self) -> None:
        """Remove entradas expiradas."""
        current_time = time.time()
        keys_to_remove = []

        # Verifica entradas expiradas
        for key in await self.memory_backend.keys():
            entry = await self.memory_backend.get(key)
            if entry and entry.expires_at > 0 and current_time >= entry.expires_at:
                keys_to_remove.append(key)

        # Remove em lote
        for key in keys_to_remove:
            await self.delete(key)
            self.metrics.expired_removals += 1

    async def get(self, key: str) -> Any | None:
        """Obtém valor do cache de forma assíncrona."""
        # Tenta memória primeiro
        entry = await self.memory_backend.get(key)

        # Se não encontrou e tem disco, tenta disco
        if not entry and self.disk_backend:
            entry = await self.disk_backend.get(key)
            if entry and not entry.is_expired:
                # Move para memória (cache warming)
                await self.memory_backend.set(key, entry)

        # Verifica validade
        if not entry:
            self.metrics.misses += 1
            return None

        if entry.is_expired:
            await self.delete(key)
            self.metrics.misses += 1
            self.metrics.expired_removals += 1
            return None

        self.metrics.hits += 1

        # Desserializa dados se necessário
        try:
            if entry.compressed:
                import zlib

                decompressed = zlib.decompress(entry.value)
                # nosec B301 - pickle usado para cache interno controlado
                return pickle.loads(decompressed)
            elif isinstance(entry.value, bytes):
                # nosec B301 - pickle usado para cache interno controlado
                return pickle.loads(entry.value)
            else:
                return entry.value
        except Exception as e:
            await self.delete(key)
            raise CacheSerializationError(
                f'Erro ao deserializar dados do cache: {e!s}', key=key, original_error=e
            ) from e

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Define valor no cache de forma assíncrona."""
        if ttl is None:
            ttl = self.config.default_ttl

        # Calcula expiração
        expires_at = time.time() + ttl if ttl > 0 else 0

        # Serializa e opcionalmente comprime
        try:
            serialized = pickle.dumps(value)
            compressed_data = serialized
            is_compressed = False

            if self.config.enable_compression and len(serialized) > 1000:
                import zlib

                compressed = zlib.compress(serialized)
                if len(compressed) < len(serialized):
                    compressed_data = compressed
                    is_compressed = True
        except Exception as e:
            raise CacheSerializationError(
                f'Erro ao serializar dados para cache: {e!s}',
                key=key,
                data_type=type(value).__name__,
                original_error=e,
            ) from e

        # Cria entrada
        entry = CacheEntry(
            key=key,
            value=compressed_data,
            created_at=time.time(),
            expires_at=expires_at,
            compressed=is_compressed,
            size_bytes=len(compressed_data),
        )

        # Remove entradas se necessário
        await self._evict_if_needed()

        # Salva em memória
        await self.memory_backend.set(key, entry)

        # Salva em disco se configurado
        if self.disk_backend:
            try:
                await self.disk_backend.set(key, entry)
            except Exception:
                # self.logger.warning(f"Erro ao salvar no cache de disco: {e!s}")  # Temporariamente comentado
                pass

        # Registra tags
        if tags:
            for tag in tags:
                if tag not in self._invalidation_patterns:
                    self._invalidation_patterns[tag] = set()
                self._invalidation_patterns[tag].add(key)

        # Atualiza métricas
        self.metrics.entry_count = await self.memory_backend.size()
        self.metrics.size_bytes += entry.size_bytes

    async def delete(self, key: str) -> bool:
        """Remove entrada do cache de forma assíncrona."""
        # Remove da memória
        removed_memory = await self.memory_backend.delete(key)

        # Remove do disco
        removed_disk = False
        if self.disk_backend:
            removed_disk = await self.disk_backend.delete(key)

        # Remove das tags
        for tag_keys in self._invalidation_patterns.values():
            tag_keys.discard(key)

        if removed_memory or removed_disk:
            self.metrics.entry_count = await self.memory_backend.size()
            return True

        return False

    async def clear(self) -> None:
        """Limpa todo o cache de forma assíncrona."""
        await self.memory_backend.clear()

        if self.disk_backend:
            await self.disk_backend.clear()

        self._invalidation_patterns.clear()
        self.metrics = CacheMetrics()

    async def _evict_if_needed(self) -> None:
        """Remove entradas se cache está cheio."""
        if self.config.max_size <= 0:
            return

        current_size = await self.memory_backend.size()
        while current_size >= self.config.max_size:
            key_to_evict = await self._select_eviction_key()
            if key_to_evict:
                await self.memory_backend.delete(key_to_evict)
                self.metrics.evictions += 1
                current_size = await self.memory_backend.size()
            else:
                break

    async def _select_eviction_key(self) -> str | None:
        """Seleciona chave para remoção baseada na política."""
        keys = await self.memory_backend.keys()
        if not keys:
            return None

        if self.config.eviction_policy == EvictionPolicy.LRU:
            # Remove menos recentemente usado
            oldest_key = None
            oldest_time = float('inf')

            for key in keys:
                entry = await self.memory_backend.get(key)
                if entry and entry.last_accessed < oldest_time:
                    oldest_time = entry.last_accessed
                    oldest_key = key

            return oldest_key

        elif self.config.eviction_policy == EvictionPolicy.LFU:
            # Remove menos frequentemente usado
            least_used_key = None
            min_count = float('inf')

            for key in keys:
                entry = await self.memory_backend.get(key)
                if entry and entry.access_count < min_count:
                    min_count = entry.access_count
                    least_used_key = key

            return least_used_key

        # Fallback para primeiro
        return keys[0]

    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalida entradas por tag de forma assíncrona."""
        if tag not in self._invalidation_patterns:
            return 0

        keys_to_remove = list(self._invalidation_patterns[tag])
        removed_count = 0

        # Remove em paralelo (com limite de concorrência)
        semaphore = asyncio.Semaphore(10)

        async def remove_key(key: str) -> None:
            nonlocal removed_count
            async with semaphore:
                if await self.delete(key):
                    removed_count += 1

        if keys_to_remove:
            await asyncio.gather(*[remove_key(key) for key in keys_to_remove])

        del self._invalidation_patterns[tag]

        # self.logger.info(f"Invalidação assíncrona por tag '{tag}': {removed_count} entradas removidas")  # Temporariamente comentado

        return removed_count

    async def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalida entradas por padrão regex de forma assíncrona."""
        import re

        try:
            regex = re.compile(pattern)
        except re.error as e:
            raise CacheError(f'Padrão regex inválido: {e!s}') from e

        keys = await self.memory_backend.keys()
        keys_to_remove = [key for key in keys if regex.match(key)]

        removed_count = 0
        # Remove em paralelo
        semaphore = asyncio.Semaphore(10)

        async def remove_key(key: str) -> None:
            nonlocal removed_count
            async with semaphore:
                if await self.delete(key):
                    removed_count += 1

        if keys_to_remove:
            await asyncio.gather(*[remove_key(key) for key in keys_to_remove])

        return removed_count

    def cached(
        self,
        ttl: int | None = None,
        key_prefix: str = '',
        tags: list[str] | None = None,
        key_func: Callable | None = None,
    ) -> Callable:
        """Decorator para cache assíncrono de funções."""

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                # Gera chave do cache
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    import hashlib

                    args_str = str(args) + str(sorted(kwargs.items()))
                    key_hash = hashlib.sha256(args_str.encode()).hexdigest()[:16]
                    cache_key = f'{key_prefix}{func.__name__}:{key_hash}'

                # Tenta obter do cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # Executa função e cacheia resultado
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl=ttl, tags=tags)

                return result

            return wrapper

        return decorator

    async def get_stats(self) -> dict[str, Any]:
        """Retorna estatísticas do cache de forma assíncrona."""
        return {
            'hits': self.metrics.hits,
            'misses': self.metrics.misses,
            'hit_rate': self.metrics.hit_rate,
            'evictions': self.metrics.evictions,
            'expired_removals': self.metrics.expired_removals,
            'entry_count': await self.memory_backend.size(),
            'size_bytes': self.metrics.size_bytes,
            'invalidation_tags': len(self._invalidation_patterns),
            'disk_enabled': self.disk_backend is not None,
        }

    async def shutdown(self) -> None:
        """Para tasks e limpa recursos de forma assíncrona."""
        self._shutdown = True

        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


# Instância global para uso conveniente
_default_async_cache: AsyncCacheManager | None = None


async def get_default_async_cache() -> AsyncCacheManager:
    """Obtém instância padrão do cache assíncrono."""
    global _default_async_cache
    if _default_async_cache is None:
        config = CacheConfig(
            default_ttl=300, max_size=1000, enable_compression=True, cleanup_interval=60
        )
        _default_async_cache = AsyncCacheManager(config)
    return _default_async_cache


def async_cached(
    ttl: int | None = None,
    key_prefix: str = '',
    tags: list[str] | None = None,
    key_func: Callable | None = None,
) -> Callable:
    """Decorator de conveniência usando cache assíncrono padrão."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache = await get_default_async_cache()
            cached_func = cache.cached(
                ttl=ttl, key_prefix=key_prefix, tags=tags, key_func=key_func
            )(func)
            return await cached_func(*args, **kwargs)

        return wrapper

    return decorator
