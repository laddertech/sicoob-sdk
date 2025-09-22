"""Sistema de cache multi-camada para o Sicoob SDK.

Este módulo fornece um sistema de cache sofisticado com múltiplas estratégias
de armazenamento, TTL configurável, invalidação inteligente e métricas de
performance para otimizar operações frequentes.

Características:
    - Cache em memória com TTL configurável
    - Cache persistente opcional (arquivo/Redis)
    - Invalidação inteligente baseada em padrões
    - Compressão automática para dados grandes
    - Métricas detalhadas de hit/miss
    - Thread-safe para uso concorrente
    - Limpeza automática de entradas expiradas

Example:
    >>> from sicoob.cache import CacheManager, CacheConfig
    >>>
    >>> # Configuração básica
    >>> config = CacheConfig(
    ...     default_ttl=300,  # 5 minutos
    ...     max_size=1000,
    ...     enable_compression=True
    ... )
    >>>
    >>> cache = CacheManager(config)
    >>>
    >>> # Usar cache
    >>> @cache.cached(ttl=600, key_prefix="boletos")
    >>> def consultar_boleto(convenio, nosso_numero):
    ...     return api.consultar_boleto(convenio, nosso_numero)
"""

import builtins
import hashlib
import pickle
import threading
import time
import zlib
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar
from weakref import WeakSet

from sicoob.exceptions import (
    CacheConfigurationError,
    CacheError,
    CacheInvalidationError,
)
from sicoob.logging_config import get_logger

T = TypeVar('T')


class CacheStrategy(Enum):
    """Estratégias de cache disponíveis"""

    MEMORY_ONLY = 'memory_only'  # Apenas na memória
    MEMORY_WITH_DISK = 'memory_disk'  # Memória + persistência em disco
    MEMORY_WITH_REDIS = 'memory_redis'  # Memória + Redis (futuro)


class EvictionPolicy(Enum):
    """Políticas de remoção quando cache atinge limite"""

    LRU = 'lru'  # Least Recently Used
    LFU = 'lfu'  # Least Frequently Used
    FIFO = 'fifo'  # First In, First Out
    TTL_BASED = 'ttl'  # Remove por TTL primeiro


@dataclass
class CacheConfig:
    """Configuração do sistema de cache

    Attributes:
        strategy: Estratégia de armazenamento
        default_ttl: TTL padrão em segundos (0 = sem expiração)
        max_size: Tamanho máximo do cache (0 = ilimitado)
        eviction_policy: Política de remoção
        enable_compression: Se deve comprimir dados grandes
        compression_threshold: Tamanho mínimo para comprimir (bytes)
        persist_path: Caminho para persistência em disco
        cleanup_interval: Interval da limpeza automática (segundos)
        enable_metrics: Se deve coletar métricas
        thread_safe: Se deve ser thread-safe
    """

    strategy: CacheStrategy = CacheStrategy.MEMORY_ONLY
    default_ttl: int = 300  # 5 minutos
    max_size: int = 1000
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    enable_compression: bool = False
    compression_threshold: int = 1024  # 1KB
    persist_path: str | None = None
    cleanup_interval: int = 60  # 1 minuto
    enable_metrics: bool = True
    thread_safe: bool = True

    def __post_init__(self) -> None:
        """Valida configuração"""
        if self.default_ttl < 0:
            raise CacheConfigurationError('default_ttl deve ser >= 0')
        if self.max_size < 0:
            raise CacheConfigurationError('max_size deve ser >= 0')
        if self.cleanup_interval <= 0:
            raise CacheConfigurationError('cleanup_interval deve ser > 0')


@dataclass
class CacheEntry:
    """Entrada do cache com metadados"""

    key: str
    value: Any
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    compressed: bool = False
    size_bytes: int = 0

    @property
    def is_expired(self) -> bool:
        """Verifica se entrada expirou"""
        return self.expires_at > 0 and time.time() > self.expires_at

    @property
    def age_seconds(self) -> float:
        """Idade da entrada em segundos"""
        return time.time() - self.created_at

    def mark_accessed(self) -> None:
        """Marca entrada como acessada"""
        self.access_count += 1
        self.last_accessed = time.time()


@dataclass
class CacheMetrics:
    """Métricas de performance do cache"""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expired_removals: int = 0
    size_bytes: int = 0
    entry_count: int = 0

    @property
    def hit_rate(self) -> float:
        """Taxa de acerto (0.0 a 1.0)"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """Taxa de erro (0.0 a 1.0)"""
        return 1.0 - self.hit_rate


class CacheBackend(ABC):
    """Interface para backends de cache"""

    @abstractmethod
    def get(self, key: str) -> CacheEntry | None:
        """Obtém entrada do cache"""
        pass

    @abstractmethod
    def set(self, key: str, entry: CacheEntry) -> None:
        """Define entrada no cache"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Remove entrada do cache"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Limpa todo o cache"""
        pass

    @abstractmethod
    def keys(self) -> list[str]:
        """Lista todas as chaves"""
        pass

    @abstractmethod
    def size(self) -> int:
        """Retorna número de entradas"""
        pass


class MemoryCacheBackend(CacheBackend):
    """Backend de cache em memória"""

    def __init__(self, thread_safe: bool = True) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock() if thread_safe else None

    def _with_lock(self, func: Callable[[], T]) -> T:
        """Executa função com lock se necessário"""
        if self._lock:
            with self._lock:
                return func()
        return func()

    def get(self, key: str) -> CacheEntry | None:
        def _get() -> CacheEntry | None:
            return self._cache.get(key)

        return self._with_lock(_get)

    def set(self, key: str, entry: CacheEntry) -> None:
        def _set() -> None:
            self._cache[key] = entry

        self._with_lock(_set)

    def delete(self, key: str) -> bool:
        def _delete() -> bool:
            return self._cache.pop(key, None) is not None

        return self._with_lock(_delete)

    def clear(self) -> None:
        def _clear() -> None:
            self._cache.clear()

        self._with_lock(_clear)

    def keys(self) -> list[str]:
        def _keys() -> list[str]:
            return list(self._cache.keys())

        return self._with_lock(_keys)

    def size(self) -> int:
        def _size() -> int:
            return len(self._cache)

        return self._with_lock(_size)


class DiskCacheBackend(CacheBackend):
    """Backend de cache persistente em disco"""

    def __init__(self, cache_dir: str, thread_safe: bool = True) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock() if thread_safe else None

    def _key_to_path(self, key: str) -> Path:
        """Converte chave em caminho de arquivo"""
        # Hash da chave para evitar problemas com caracteres especiais
        hashed = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f'{hashed}.cache'

    def _with_lock(self, func: Callable[[], T]) -> T:
        """Executa função com lock se necessário"""
        if self._lock:
            with self._lock:
                return func()
        return func()

    def get(self, key: str) -> CacheEntry | None:
        def _get() -> CacheEntry | None:
            path = self._key_to_path(key)
            if not path.exists():
                return None

            try:
                with open(path, 'rb') as f:
                    # nosec B301 - pickle usado para cache interno controlado
                    return pickle.load(f)
            except (pickle.PickleError, FileNotFoundError, EOFError):
                # Remove arquivo corrompido
                path.unlink(missing_ok=True)
                return None

        return self._with_lock(_get)

    def set(self, key: str, entry: CacheEntry) -> None:
        def _set() -> None:
            path = self._key_to_path(key)
            try:
                with open(path, 'wb') as f:
                    pickle.dump(entry, f)
            except (pickle.PickleError, OSError) as e:
                raise CacheError(f'Erro ao salvar cache no disco: {e}') from e

        self._with_lock(_set)

    def delete(self, key: str) -> bool:
        def _delete() -> bool:
            path = self._key_to_path(key)
            if path.exists():
                path.unlink()
                return True
            return False

        return self._with_lock(_delete)

    def clear(self) -> None:
        def _clear() -> None:
            for cache_file in self.cache_dir.glob('*.cache'):
                cache_file.unlink(missing_ok=True)

        self._with_lock(_clear)

    def keys(self) -> list[str]:
        """Nota: Não conseguimos recuperar chaves originais do disco facilmente"""

        def _keys() -> list[str]:
            return [f.stem for f in self.cache_dir.glob('*.cache')]

        return self._with_lock(_keys)

    def size(self) -> int:
        def _size() -> int:
            return len(list(self.cache_dir.glob('*.cache')))

        return self._with_lock(_size)


class CacheManager:
    """Gerenciador principal do sistema de cache"""

    def __init__(self, config: CacheConfig) -> None:
        self.config = config
        self.logger = get_logger(__name__)

        # Inicializa backend principal
        self.memory_backend = MemoryCacheBackend(config.thread_safe)
        self.disk_backend = None

        if config.strategy == CacheStrategy.MEMORY_WITH_DISK:
            if not config.persist_path:
                raise CacheConfigurationError(
                    'persist_path é obrigatório para MEMORY_WITH_DISK'
                )
            self.disk_backend = DiskCacheBackend(
                config.persist_path, config.thread_safe
            )

        # Métricas
        self.metrics = CacheMetrics()

        # Cleanup automático
        self._cleanup_thread = None
        self._shutdown = False
        if config.cleanup_interval > 0:
            self._start_cleanup_thread()

        # Observadores para invalidação
        self._invalidation_patterns: dict[str, set[str]] = {}
        self._observers: WeakSet = WeakSet()

    def _start_cleanup_thread(self) -> None:
        """Inicia thread de limpeza automática"""

        def cleanup_loop() -> None:
            while not self._shutdown:
                try:
                    self._cleanup_expired()
                    time.sleep(self.config.cleanup_interval)
                except Exception as e:
                    self.logger.error(f'Erro na limpeza do cache: {e}', exc_info=True)

        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def _cleanup_expired(self) -> None:
        """Remove entradas expiradas"""
        removed_count = 0

        for key in self.memory_backend.keys():
            entry = self.memory_backend.get(key)
            if entry and entry.is_expired:
                self.memory_backend.delete(key)
                if self.disk_backend:
                    self.disk_backend.delete(key)
                removed_count += 1

        if removed_count > 0:
            self.metrics.expired_removals += removed_count
            self.logger.debug(
                f'Limpeza automática: {removed_count} entradas expiradas removidas',
                extra={'operation': 'cache_cleanup', 'removed_count': removed_count},
            )

    def _calculate_entry_size(self, value: Any) -> int:
        """Calcula tamanho aproximado de uma entrada"""
        try:
            if hasattr(value, '__sizeof__'):
                return value.__sizeof__()
            return len(pickle.dumps(value))
        except Exception:
            return 0

    def _compress_if_needed(self, data: bytes) -> tuple[bytes, bool]:
        """Comprime dados se necessário"""
        if (
            self.config.enable_compression
            and len(data) >= self.config.compression_threshold
        ):
            compressed = zlib.compress(data)
            if len(compressed) < len(data):
                return compressed, True
        return data, False

    def _decompress_if_needed(self, data: bytes, compressed: bool) -> bytes:
        """Descomprime dados se necessário"""
        return zlib.decompress(data) if compressed else data

    def _evict_if_needed(self) -> None:
        """Remove entradas se cache está cheio"""
        if self.config.max_size <= 0:
            return

        while self.memory_backend.size() >= self.config.max_size:
            key_to_evict = self._select_eviction_key()
            if key_to_evict:
                self.memory_backend.delete(key_to_evict)
                self.metrics.evictions += 1
            else:
                break

    def _select_eviction_key(self) -> str | None:
        """Seleciona chave para remoção baseada na política"""
        keys = self.memory_backend.keys()
        if not keys:
            return None

        if self.config.eviction_policy == EvictionPolicy.LRU:
            # Remove menos recentemente usado
            oldest_key = None
            oldest_time = float('inf')

            for key in keys:
                entry = self.memory_backend.get(key)
                if entry and entry.last_accessed < oldest_time:
                    oldest_time = entry.last_accessed
                    oldest_key = key

            return oldest_key

        elif self.config.eviction_policy == EvictionPolicy.LFU:
            # Remove menos frequentemente usado
            least_used_key = None
            min_count = float('inf')

            for key in keys:
                entry = self.memory_backend.get(key)
                if entry and entry.access_count < min_count:
                    min_count = entry.access_count
                    least_used_key = key

            return least_used_key

        elif self.config.eviction_policy == EvictionPolicy.FIFO:
            # Remove mais antigo
            oldest_key = None
            oldest_time = float('inf')

            for key in keys:
                entry = self.memory_backend.get(key)
                if entry and entry.created_at < oldest_time:
                    oldest_time = entry.created_at
                    oldest_key = key

            return oldest_key

        elif self.config.eviction_policy == EvictionPolicy.TTL_BASED:
            # Remove que expira primeiro
            soonest_key = None
            soonest_expiry = float('inf')

            for key in keys:
                entry = self.memory_backend.get(key)
                if entry and 0 < entry.expires_at < soonest_expiry:
                    soonest_expiry = entry.expires_at
                    soonest_key = key

            return soonest_key or keys[0]  # Fallback para primeiro

        return keys[0]  # Fallback

    def get(self, key: str) -> Any | None:
        """Obtém valor do cache"""
        # Primeiro tenta memória
        entry = self.memory_backend.get(key)

        # Se não encontrou, tenta disco
        if not entry and self.disk_backend:
            entry = self.disk_backend.get(key)
            if entry:
                # Move para memória (cache warming)
                self.memory_backend.set(key, entry)

        # Verifica se encontrou e está válido
        if not entry:
            self.metrics.misses += 1
            return None

        if entry.is_expired:
            self.delete(key)
            self.metrics.misses += 1
            return None

        # Hit - atualiza métricas e metadados
        entry.mark_accessed()
        self.metrics.hits += 1

        # Descomprime se necessário
        value = entry.value
        if entry.compressed and isinstance(value, bytes):
            # nosec B301 - pickle usado para cache interno controlado
            value = pickle.loads(self._decompress_if_needed(value, True))

        return value

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Define valor no cache"""
        ttl = ttl if ttl is not None else self.config.default_ttl
        expires_at = time.time() + ttl if ttl > 0 else 0

        # Serializa e comprime se necessário
        serialized = pickle.dumps(value)
        compressed_data, is_compressed = self._compress_if_needed(serialized)

        entry = CacheEntry(
            key=key,
            value=compressed_data if is_compressed else value,
            created_at=time.time(),
            expires_at=expires_at,
            compressed=is_compressed,
            size_bytes=len(compressed_data)
            if is_compressed
            else self._calculate_entry_size(value),
        )

        # Verifica se precisa remover entradas
        self._evict_if_needed()

        # Salva em memória
        self.memory_backend.set(key, entry)

        # Salva em disco se configurado
        if self.disk_backend:
            try:
                self.disk_backend.set(key, entry)
            except Exception as e:
                self.logger.warning(f'Erro ao salvar no cache de disco: {e}')

        # Registra tags para invalidação
        if tags:
            for tag in tags:
                if tag not in self._invalidation_patterns:
                    self._invalidation_patterns[tag] = set()
                self._invalidation_patterns[tag].add(key)

        # Atualiza métricas
        self.metrics.entry_count = self.memory_backend.size()
        self.metrics.size_bytes += entry.size_bytes

    def delete(self, key: str) -> bool:
        """Remove entrada do cache"""
        # Remove da memória
        removed = self.memory_backend.delete(key)

        # Remove do disco
        if self.disk_backend:
            self.disk_backend.delete(key)

        # Remove das tags de invalidação
        for tag_keys in self._invalidation_patterns.values():
            tag_keys.discard(key)

        if removed:
            self.metrics.entry_count = self.memory_backend.size()

        return removed

    def clear(self) -> None:
        """Limpa todo o cache"""
        self.memory_backend.clear()
        if self.disk_backend:
            self.disk_backend.clear()

        self._invalidation_patterns.clear()
        self.metrics = CacheMetrics()

    def invalidate_by_tag(self, tag: str) -> int:
        """Invalida entradas por tag"""
        if tag not in self._invalidation_patterns:
            return 0

        keys_to_remove = list(self._invalidation_patterns[tag])
        removed_count = 0

        for key in keys_to_remove:
            if self.delete(key):
                removed_count += 1

        del self._invalidation_patterns[tag]

        self.logger.info(
            f"Invalidação por tag '{tag}': {removed_count} entradas removidas",
            extra={
                'operation': 'cache_invalidate_tag',
                'tag': tag,
                'removed': removed_count,
            },
        )

        return removed_count

    def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalida entradas que correspondem ao padrão"""
        import re

        try:
            regex = re.compile(pattern)
        except re.error as e:
            raise CacheInvalidationError(
                f"Padrão regex inválido '{pattern}': {e}",
                pattern=pattern,
                original_error=e,
            )

        keys_to_remove = []

        for key in self.memory_backend.keys():
            if regex.match(key):
                keys_to_remove.append(key)

        removed_count = 0
        for key in keys_to_remove:
            if self.delete(key):
                removed_count += 1

        self.logger.info(
            f"Invalidação por padrão '{pattern}': {removed_count} entradas removidas",
            extra={
                'operation': 'cache_invalidate_pattern',
                'pattern': pattern,
                'removed': removed_count,
            },
        )

        return removed_count

    def invalidate_by_keys(self, keys: list[str]) -> int:
        """Invalida múltiplas chaves específicas"""
        removed_count = 0

        for key in keys:
            if self.delete(key):
                removed_count += 1

        self.logger.info(
            f'Invalidação por chaves: {removed_count}/{len(keys)} entradas removidas',
            extra={
                'operation': 'cache_invalidate_keys',
                'requested_keys': len(keys),
                'removed': removed_count,
            },
        )

        return removed_count

    def invalidate_by_prefix(self, prefix: str) -> int:
        """Invalida todas as entradas que começam com o prefixo"""
        keys_to_remove = []

        for key in self.memory_backend.keys():
            if key.startswith(prefix):
                keys_to_remove.append(key)

        removed_count = 0
        for key in keys_to_remove:
            if self.delete(key):
                removed_count += 1

        self.logger.info(
            f"Invalidação por prefixo '{prefix}': {removed_count} entradas removidas",
            extra={
                'operation': 'cache_invalidate_prefix',
                'prefix': prefix,
                'removed': removed_count,
            },
        )

        return removed_count

    def invalidate_expired(self) -> int:
        """Remove manualmente todas as entradas expiradas"""
        current_time = time.time()
        keys_to_remove = []

        for key in self.memory_backend.keys():
            entry = self.memory_backend.get(key)
            if entry and entry.expires_at > 0 and current_time >= entry.expires_at:
                keys_to_remove.append(key)

        removed_count = 0
        for key in keys_to_remove:
            if self.delete(key):
                removed_count += 1
                self.metrics.expired_removals += 1

        self.logger.debug(
            f'Limpeza manual de expirados: {removed_count} entradas removidas',
            extra={'operation': 'cache_cleanup_expired', 'removed': removed_count},
        )

        return removed_count

    def invalidate_conditional(self, predicate: Callable[[str, Any], bool]) -> int:
        """Invalida entradas baseado em predicado personalizado

        Args:
            predicate: Função que recebe (chave, valor) e retorna True para remover

        Returns:
            Número de entradas removidas

        Example:
            >>> # Remove cobranças PIX com valor acima de 1000
            >>> cache.invalidate_conditional(
            ...     lambda key, value:
            ...         key.startswith("pix:cobranca:") and
            ...         value.get("valor", {}).get("original", 0) > 1000
            ... )
        """
        keys_to_remove = []

        for key in self.memory_backend.keys():
            entry = self.memory_backend.get(key)
            if entry and not entry.is_expired:
                try:
                    value = entry.deserialize()
                    if predicate(key, value):
                        keys_to_remove.append(key)
                except Exception as e:
                    self.logger.warning(
                        f"Erro ao avaliar predicado para chave '{key}': {e}",
                        extra={'operation': 'cache_conditional_error', 'key': key},
                    )

        removed_count = 0
        for key in keys_to_remove:
            if self.delete(key):
                removed_count += 1

        self.logger.info(
            f'Invalidação condicional: {removed_count} entradas removidas',
            extra={
                'operation': 'cache_invalidate_conditional',
                'removed': removed_count,
            },
        )

        return removed_count

    def get_keys_by_tag(self, tag: str) -> builtins.set[str]:
        """Obtém todas as chaves associadas a uma tag"""
        return self._invalidation_patterns.get(tag, set()).copy()

    def get_keys_by_pattern(self, pattern: str) -> list[str]:
        """Obtém chaves que correspondem a um padrão regex"""
        import re

        try:
            regex = re.compile(pattern)
            matching_keys = []

            for key in self.memory_backend.keys():
                if regex.match(key):
                    matching_keys.append(key)

            return matching_keys

        except re.error as e:
            raise CacheInvalidationError(
                f"Padrão regex inválido '{pattern}': {e}",
                pattern=pattern,
                original_error=e,
            )

    def get_keys_by_prefix(self, prefix: str) -> list[str]:
        """Obtém todas as chaves que começam com o prefixo"""
        matching_keys = []

        for key in self.memory_backend.keys():
            if key.startswith(prefix):
                matching_keys.append(key)

        return matching_keys

    def bulk_invalidate(
        self,
        tags: list[str] | None = None,
        patterns: list[str] | None = None,
        prefixes: list[str] | None = None,
        keys: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """Invalidação em lote com múltiplos critérios

        Args:
            tags: Lista de tags para invalidar
            patterns: Lista de padrões regex
            prefixes: Lista de prefixos
            keys: Lista de chaves específicas
            dry_run: Se True, apenas conta o que seria removido sem remover

        Returns:
            Dicionário com contagens por tipo de invalidação
        """
        results = {'tags': 0, 'patterns': 0, 'prefixes': 0, 'keys': 0, 'total': 0}

        all_keys_to_remove = set()

        # Coleta chaves por tags
        if tags:
            for tag in tags:
                tag_keys = self.get_keys_by_tag(tag)
                all_keys_to_remove.update(tag_keys)
                results['tags'] += len(tag_keys)

        # Coleta chaves por padrões
        if patterns:
            for pattern in patterns:
                try:
                    pattern_keys = self.get_keys_by_pattern(pattern)
                    all_keys_to_remove.update(pattern_keys)
                    results['patterns'] += len(pattern_keys)
                except CacheInvalidationError as e:
                    self.logger.error(
                        f"Erro no padrão '{pattern}': {e}",
                        extra={
                            'operation': 'cache_bulk_invalidate_error',
                            'pattern': pattern,
                        },
                    )

        # Coleta chaves por prefixos
        if prefixes:
            for prefix in prefixes:
                prefix_keys = self.get_keys_by_prefix(prefix)
                all_keys_to_remove.update(prefix_keys)
                results['prefixes'] += len(prefix_keys)

        # Adiciona chaves específicas
        if keys:
            all_keys_to_remove.update(keys)
            results['keys'] = len(keys)

        results['total'] = len(all_keys_to_remove)

        # Remove duplicatas e executa se não for dry run
        if not dry_run and all_keys_to_remove:
            removed_count = self.invalidate_by_keys(list(all_keys_to_remove))
            results['actual_removed'] = removed_count

        self.logger.info(
            f'Invalidação em lote: {results["total"]} chaves identificadas'
            + (
                f', {results.get("actual_removed", 0)} removidas'
                if not dry_run
                else ' (dry run)'
            ),
            extra={
                'operation': 'cache_bulk_invalidate',
                'results': results,
                'dry_run': dry_run,
            },
        )

        return results

    def create_invalidation_group(self, name: str, rules: dict[str, Any]) -> None:
        """Cria um grupo de regras de invalidação reutilizável

        Args:
            name: Nome do grupo
            rules: Dicionário com regras (tags, patterns, prefixes, etc.)

        Example:
            >>> cache.create_invalidation_group("pix_operations", {
            ...     "tags": ["pix", "cobranca"],
            ...     "patterns": [r"^pix:.*"],
            ...     "prefixes": ["webhook:pix:"]
            ... })
        """
        if not hasattr(self, '_invalidation_groups'):
            self._invalidation_groups = {}

        self._invalidation_groups[name] = rules

        self.logger.info(
            f"Grupo de invalidação '{name}' criado",
            extra={
                'operation': 'cache_create_invalidation_group',
                'group': name,
                'rules': rules,
            },
        )

    def invalidate_group(
        self, group_name: str, dry_run: bool = False
    ) -> dict[str, int]:
        """Aplica invalidação usando um grupo predefinido"""
        if (
            not hasattr(self, '_invalidation_groups')
            or group_name not in self._invalidation_groups
        ):
            raise CacheInvalidationError(
                f"Grupo de invalidação '{group_name}' não encontrado"
            )

        rules = self._invalidation_groups[group_name]

        return self.bulk_invalidate(
            tags=rules.get('tags'),
            patterns=rules.get('patterns'),
            prefixes=rules.get('prefixes'),
            keys=rules.get('keys'),
            dry_run=dry_run,
        )

    def cached(
        self,
        ttl: int | None = None,
        key_prefix: str = '',
        tags: list[str] | None = None,
        key_func: Callable | None = None,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator para cache automático de funções"""

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                # Gera chave do cache
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Chave padrão baseada em função e argumentos
                    args_str = str(args) + str(sorted(kwargs.items()))
                    key_hash = hashlib.sha256(args_str.encode()).hexdigest()[:16]
                    cache_key = f'{key_prefix}{func.__name__}:{key_hash}'

                # Tenta obter do cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # Executa função e cacheia resultado
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl=ttl, tags=tags)

                return result

            return wrapper

        return decorator

    def get_stats(self) -> dict[str, Any]:
        """Retorna estatísticas do cache"""
        return {
            'hits': self.metrics.hits,
            'misses': self.metrics.misses,
            'hit_rate': self.metrics.hit_rate,
            'evictions': self.metrics.evictions,
            'expired_removals': self.metrics.expired_removals,
            'entry_count': self.metrics.entry_count,
            'size_bytes': self.metrics.size_bytes,
            'invalidation_tags': len(self._invalidation_patterns),
            'backend_strategy': self.config.strategy.value,
        }

    def shutdown(self) -> None:
        """Para threads e limpa recursos"""
        self._shutdown = True
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)


# Instância global padrão (lazy loading)
_default_cache: CacheManager | None = None


def get_default_cache() -> CacheManager:
    """Obtém instância padrão do cache"""
    global _default_cache
    if _default_cache is None:
        config = CacheConfig(
            default_ttl=300,  # 5 minutos
            max_size=1000,
            enable_compression=True,
            enable_metrics=True,
        )
        _default_cache = CacheManager(config)
    return _default_cache


def cached(
    ttl: int | None = None,
    key_prefix: str = '',
    tags: list[str] | None = None,
    key_func: Callable | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator de conveniência usando cache padrão"""
    return get_default_cache().cached(
        ttl=ttl, key_prefix=key_prefix, tags=tags, key_func=key_func
    )
