"""API assíncrona para operações PIX.

Este módulo fornece funcionalidades assíncronas para criação, consulta e
gerenciamento de cobranças PIX, permitindo alto throughput em operações
em lote e processamento paralelo.

Classes:
    AsyncPixAPI: API assíncrona para operações PIX

Example:
    >>> import asyncio
    >>> from sicoob.async_client import AsyncSicoob
    >>>
    >>> async def processar_cobrancas_pix():
    ...     async with AsyncSicoob(client_id="123") as client:
    ...         # Criação em lote
    ...         tasks = [
    ...             client.cobranca.pix.criar_cobranca_imediata(f"txid_{i}", dados)
    ...             for i, dados in enumerate(lista_dados_pix)
    ...         ]
    ...         cobrancas = await asyncio.gather(*tasks)
    ...         return cobrancas
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from sicoob.async_client import AsyncAPIClient, gather_with_concurrency
from sicoob.exceptions import (
    CobrancaPixNaoEncontradaError,
    PixError,
    WebhookPixNaoEncontradoError,
)
from sicoob.validation import validate_txid, validate_url


class AsyncPixAPI:
    """API assíncrona para operações PIX."""

    def __init__(self, api_client: AsyncAPIClient) -> None:
        """Inicializa API PIX assíncrona.

        Args:
            api_client: Cliente HTTP assíncrono
        """
        self.api_client = api_client

    async def criar_cobranca_imediata(
        self, txid: str, dados: dict[str, Any]
    ) -> dict[str, Any]:
        """Cria cobrança PIX imediata de forma assíncrona.

        Args:
            txid: Identificador da transação (26-35 caracteres alfanuméricos)
            dados: Dados da cobrança

        Returns:
            Dados da cobrança criada

        Raises:
            PixError: Em caso de erro na criação
        """
        try:
            # Valida TXID
            txid = validate_txid(txid)

            base_url = self.api_client._get_base_url()
            url = f'{base_url}/pix/cob/{txid}'

            response = await self.api_client._make_request(
                'PUT', url, scope='cob.write', json=dados
            )

            return response

        except Exception as e:
            raise PixError(f'Erro ao criar cobrança PIX: {e!s}') from e

    async def consultar_cobranca_imediata(self, txid: str) -> dict[str, Any]:
        """Consulta cobrança PIX imediata de forma assíncrona.

        Args:
            txid: Identificador da transação

        Returns:
            Dados da cobrança

        Raises:
            CobrancaPixNaoEncontradaError: Se a cobrança não foi encontrada
        """
        try:
            # Valida TXID
            txid = validate_txid(txid)

            base_url = self.api_client._get_base_url()
            url = f'{base_url}/pix/cob/{txid}'

            response = await self.api_client._make_request('GET', url, scope='cob.read')

            return response

        except Exception as e:
            if '404' in str(e) or 'não encontrada' in str(e).lower():
                raise CobrancaPixNaoEncontradaError(txid) from e
            raise PixError(f'Erro ao consultar cobrança PIX: {e!s}') from e

    async def listar_cobrancas(
        self, inicio: str, fim: str, **filtros: Any
    ) -> dict[str, Any]:
        """Lista cobranças PIX em período de forma assíncrona.

        Args:
            inicio: Data/hora inicial (ISO 8601)
            fim: Data/hora final (ISO 8601)
            **filtros: Filtros adicionais (status, cpf, etc.)

        Returns:
            Lista de cobranças
        """
        base_url = self.api_client._get_base_url()
        url = f'{base_url}/pix/cob'

        params = {'inicio': inicio, 'fim': fim, **filtros}

        return await self.api_client._make_request(
            'GET', url, scope='cob.read', params=params
        )

    async def criar_cobranca_com_vencimento(
        self, txid: str, dados: dict[str, Any]
    ) -> dict[str, Any]:
        """Cria cobrança PIX com vencimento de forma assíncrona.

        Args:
            txid: Identificador da transação
            dados: Dados da cobrança com vencimento

        Returns:
            Dados da cobrança criada
        """
        # Valida TXID
        txid = validate_txid(txid)

        base_url = self.api_client._get_base_url()
        url = f'{base_url}/pix/cobv/{txid}'

        return await self.api_client._make_request(
            'PUT', url, scope='cobv.write', json=dados
        )

    async def consultar_cobranca_com_vencimento(
        self, txid: str, revisao: int = 0
    ) -> dict[str, Any]:
        """Consulta cobrança PIX com vencimento de forma assíncrona.

        Args:
            txid: Identificador da transação
            revisao: Revisão da cobrança

        Returns:
            Dados da cobrança
        """
        # Valida TXID
        txid = validate_txid(txid)

        base_url = self.api_client._get_base_url()
        url = f'{base_url}/pix/cobv/{txid}'

        params = {'revisao': revisao} if revisao > 0 else {}

        return await self.api_client._make_request(
            'GET', url, scope='cobv.read', params=params
        )

    async def cadastrar_webhook(self, chave: str, url_webhook: str) -> dict[str, Any]:
        """Cadastra webhook PIX de forma assíncrona.

        Args:
            chave: Chave PIX
            url_webhook: URL do webhook

        Returns:
            Dados do webhook cadastrado
        """
        # Valida URL
        url_webhook = validate_url(url_webhook)

        base_url = self.api_client._get_base_url()
        url = f'{base_url}/pix/webhook/{chave}'

        dados = {'webhookUrl': url_webhook}

        return await self.api_client._make_request(
            'PUT', url, scope='webhook.write', json=dados
        )

    async def consultar_webhook(self, chave: str) -> dict[str, Any]:
        """Consulta webhook PIX de forma assíncrona.

        Args:
            chave: Chave PIX

        Returns:
            Dados do webhook

        Raises:
            WebhookPixNaoEncontradoError: Se o webhook não foi encontrado
        """
        try:
            base_url = self.api_client._get_base_url()
            url = f'{base_url}/pix/webhook/{chave}'

            return await self.api_client._make_request('GET', url, scope='webhook.read')

        except Exception as e:
            if '404' in str(e):
                raise WebhookPixNaoEncontradoError(chave) from e
            raise PixError(f'Erro ao consultar webhook: {e!s}') from e

    async def excluir_webhook(self, chave: str) -> dict[str, Any]:
        """Exclui webhook PIX de forma assíncrona.

        Args:
            chave: Chave PIX

        Returns:
            Confirmação da exclusão
        """
        base_url = self.api_client._get_base_url()
        url = f'{base_url}/pix/webhook/{chave}'

        return await self.api_client._make_request('DELETE', url, scope='webhook.write')

    async def criar_lote_cobranca(
        self, id_lote: int, dados: dict[str, Any]
    ) -> dict[str, Any]:
        """Cria lote de cobranças PIX de forma assíncrona.

        Args:
            id_lote: ID do lote
            dados: Dados do lote

        Returns:
            Dados do lote criado
        """
        base_url = self.api_client._get_base_url()
        url = f'{base_url}/pix/lotecobv/{id_lote}'

        return await self.api_client._make_request(
            'PUT', url, scope='lotecobv.write', json=dados
        )

    async def consultar_lote_cobranca(self, id_lote: int) -> dict[str, Any]:
        """Consulta lote de cobranças PIX de forma assíncrona.

        Args:
            id_lote: ID do lote

        Returns:
            Dados do lote
        """
        base_url = self.api_client._get_base_url()
        url = f'{base_url}/pix/lotecobv/{id_lote}'

        return await self.api_client._make_request('GET', url, scope='lotecobv.read')

    # Métodos otimizados para operações em lote

    async def criar_cobrancas_lote(
        self, cobrancas: list[tuple[str, dict[str, Any]]], max_concorrencia: int = 10
    ) -> list[dict[str, Any]]:
        """Cria múltiplas cobranças PIX de forma concorrente.

        Args:
            cobrancas: Lista de tuplas (txid, dados)
            max_concorrencia: Número máximo de requisições concorrentes

        Returns:
            Lista de cobranças criadas

        Example:
            >>> cobrancas = [
            ...     ("txid123", {"valor": {"original": "100.50"}}),
            ...     ("txid124", {"valor": {"original": "200.75"}}),
            ... ]
            >>> resultados = await api.criar_cobrancas_lote(cobrancas)
        """
        tasks = [self.criar_cobranca_imediata(txid, dados) for txid, dados in cobrancas]

        return await gather_with_concurrency(tasks, max_concorrencia)

    async def consultar_cobrancas_lote(
        self, txids: list[str], max_concorrencia: int = 10
    ) -> list[dict[str, Any]]:
        """Consulta múltiplas cobranças PIX de forma concorrente.

        Args:
            txids: Lista de TXIDs
            max_concorrencia: Número máximo de requisições concorrentes

        Returns:
            Lista de dados das cobranças

        Example:
            >>> txids = ["txid123", "txid124", "txid125"]
            >>> cobrancas = await api.consultar_cobrancas_lote(txids)
        """
        tasks = [self.consultar_cobranca_imediata(txid) for txid in txids]

        return await gather_with_concurrency(tasks, max_concorrencia)

    async def processar_cobrancas_periodo(
        self,
        data_inicio: datetime,
        data_fim: datetime,
        status_filtro: str | None = None,
        max_concorrencia: int = 5,
    ) -> dict[str, Any]:
        """Processa todas as cobranças de um período de forma otimizada.

        Args:
            data_inicio: Data de início
            data_fim: Data de fim
            status_filtro: Status para filtrar (opcional)
            max_concorrencia: Número máximo de requisições concorrentes

        Returns:
            Estatísticas e dados das cobranças processadas

        Example:
            >>> inicio = datetime.now() - timedelta(days=7)
            >>> fim = datetime.now()
            >>> stats = await api.processar_cobrancas_periodo(inicio, fim)
        """
        # Formato ISO 8601
        inicio_iso = data_inicio.isoformat() + 'Z'
        fim_iso = data_fim.isoformat() + 'Z'

        # Parâmetros de filtro
        filtros = {}
        if status_filtro:
            filtros['status'] = status_filtro

        # Lista cobranças
        response = await self.listar_cobrancas(inicio_iso, fim_iso, **filtros)
        cobrancas = response.get('cobs', [])

        # Estatísticas básicas
        stats = {
            'total_cobrancas': len(cobrancas),
            'periodo': {'inicio': inicio_iso, 'fim': fim_iso},
            'estatisticas': {},
            'cobrancas': cobrancas,
        }

        if cobrancas:
            # Calcula estatísticas
            valores = []
            status_count = {}

            for cobranca in cobrancas:
                # Valor
                valor_info = cobranca.get('valor', {})
                if 'original' in valor_info:
                    try:
                        valores.append(float(valor_info['original']))
                    except (ValueError, TypeError):
                        pass

                # Status
                status = cobranca.get('status', 'DESCONHECIDO')
                status_count[status] = status_count.get(status, 0) + 1

            stats['estatisticas'] = {
                'valor_total': sum(valores),
                'valor_medio': sum(valores) / len(valores) if valores else 0,
                'valor_maximo': max(valores) if valores else 0,
                'valor_minimo': min(valores) if valores else 0,
                'distribuicao_status': status_count,
            }

        return stats

    async def _buscar_cobrancas_periodo(self, chaves_pix: list[str]) -> list[dict]:
        """Busca cobranças das últimas horas para todas as chaves."""
        agora = datetime.now()
        inicio = agora - timedelta(hours=2)

        tasks = []
        for chave in chaves_pix:
            tasks.append(
                self.listar_cobrancas(
                    inicio.isoformat() + 'Z',
                    agora.isoformat() + 'Z',
                    chave=chave,
                )
            )

        return await gather_with_concurrency(tasks, 5)

    async def _processar_respostas_cobrancas(
        self, responses: list[dict], ultimas_cobrancas: set, callback_cobranca: Any
    ) -> tuple[set, list]:
        """Processa respostas e identifica novas cobranças."""
        cobrancas_atuais = set()
        novas_cobrancas = []

        for response in responses:
            cobrancas = response.get('cobs', [])
            for cobranca in cobrancas:
                txid = cobranca.get('txid')
                if txid:
                    cobrancas_atuais.add(txid)

                    if txid not in ultimas_cobrancas:
                        novas_cobrancas.append(cobranca)
                        await self._executar_callback(callback_cobranca, cobranca)

        return cobrancas_atuais, novas_cobrancas

    async def _executar_callback(self, callback_cobranca: Any, cobranca: dict) -> None:
        """Executa callback para nova cobrança."""
        if callback_cobranca:
            try:
                if asyncio.iscoroutinefunction(callback_cobranca):
                    await callback_cobranca(cobranca)
                else:
                    callback_cobranca(cobranca)
            except Exception as e:
                self.api_client.logger.error(f'Erro no callback: {e!s}')

    async def monitorar_cobrancas_tempo_real(
        self,
        chaves_pix: list[str],
        intervalo_segundos: int = 30,
        callback_cobranca: Any = None,
    ) -> Any:
        """Monitora cobranças PIX em tempo real através de polling."""
        ultimas_cobrancas = set()

        while True:
            try:
                responses = await self._buscar_cobrancas_periodo(chaves_pix)
                (
                    cobrancas_atuais,
                    novas_cobrancas,
                ) = await self._processar_respostas_cobrancas(
                    responses, ultimas_cobrancas, callback_cobranca
                )

                # Atualiza conjunto de cobranças conhecidas
                ultimas_cobrancas = cobrancas_atuais

                # Retorna estatísticas
                stats = {
                    'timestamp': datetime.now().isoformat(),
                    'chaves_monitoradas': len(chaves_pix),
                    'cobrancas_encontradas': len(cobrancas_atuais),
                    'novas_cobrancas': len(novas_cobrancas),
                    'cobrancas_novas': novas_cobrancas,
                }

                yield stats

                # Aguarda próxima verificação
                await asyncio.sleep(intervalo_segundos)

            except Exception as e:
                self.api_client.logger.error(
                    f'Erro no monitoramento: {e!s}', exc_info=True
                )
                # Aguarda um pouco antes de tentar novamente
                await asyncio.sleep(intervalo_segundos)

    async def gerar_relatorio_performance(
        self, txids: list[str], max_concorrencia: int = 10
    ) -> dict[str, Any]:
        """Gera relatório de performance para lista de TXIDs.

        Args:
            txids: Lista de TXIDs para analisar
            max_concorrencia: Número máximo de requisições concorrentes

        Returns:
            Relatório detalhado de performance
        """
        import time

        inicio_processamento = time.time()

        # Consulta todas as cobranças em paralelo
        start_time = time.time()
        cobrancas = await self.consultar_cobrancas_lote(txids, max_concorrencia)
        consulta_duration = time.time() - start_time

        # Análise dos resultados
        cobrancas_validas = [c for c in cobrancas if c is not None]
        erros = len(txids) - len(cobrancas_validas)

        # Métricas de performance
        tempo_total = time.time() - inicio_processamento
        throughput = len(txids) / tempo_total if tempo_total > 0 else 0

        relatorio = {
            'metricas_performance': {
                'total_txids': len(txids),
                'cobrancas_encontradas': len(cobrancas_validas),
                'erros': erros,
                'tempo_total_segundos': tempo_total,
                'tempo_consulta_segundos': consulta_duration,
                'throughput_txids_por_segundo': throughput,
                'concorrencia_utilizada': max_concorrencia,
                'taxa_sucesso': len(cobrancas_validas) / len(txids) * 100,
            },
            'distribuicao_status': {},
            'analise_valores': {},
            'timestamp': datetime.now().isoformat(),
        }

        if cobrancas_validas:
            # Análise de status
            status_count = {}
            valores = []

            for cobranca in cobrancas_validas:
                status = cobranca.get('status', 'DESCONHECIDO')
                status_count[status] = status_count.get(status, 0) + 1

                valor_info = cobranca.get('valor', {})
                if 'original' in valor_info:
                    try:
                        valores.append(float(valor_info['original']))
                    except (ValueError, TypeError):
                        pass

            relatorio['distribuicao_status'] = status_count

            if valores:
                relatorio['analise_valores'] = {
                    'total': sum(valores),
                    'media': sum(valores) / len(valores),
                    'maximo': max(valores),
                    'minimo': min(valores),
                    'quantidade_com_valor': len(valores),
                }

        return relatorio
