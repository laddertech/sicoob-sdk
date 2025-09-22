"""API assíncrona para operações de boleto bancário.

Este módulo fornece funcionalidades assíncronas para emissão, consulta e
gerenciamento de boletos bancários, permitindo alto throughput em operações
em lote.

Classes:
    AsyncBoletoAPI: API assíncrona para boletos bancários

Example:
    >>> import asyncio
    >>> from sicoob.async_client import AsyncSicoob
    >>>
    >>> async def processar_boletos():
    ...     async with AsyncSicoob(client_id="123") as client:
    ...         # Emissão em lote
    ...         tasks = [
    ...             client.cobranca.boleto.emitir_boleto(dados)
    ...             for dados in lista_dados_boletos
    ...         ]
    ...         boletos = await asyncio.gather(*tasks)
    ...         return boletos
"""

from datetime import date
from typing import Any

from sicoob.async_client import AsyncAPIClient
from sicoob.exceptions import BoletoError, BoletoNaoEncontradoError
from sicoob.validation import validate_cnpj, validate_cpf


class AsyncBoletoAPI:
    """API assíncrona para operações de boleto bancário."""

    def __init__(self, api_client: AsyncAPIClient) -> None:
        """Inicializa API de boleto assíncrona.

        Args:
            api_client: Cliente HTTP assíncrono
        """
        self.api_client = api_client

    async def emitir_boleto(
        self, dados: dict[str, Any], nosso_numero: str | None = None
    ) -> dict[str, Any]:
        """Emite um boleto bancário de forma assíncrona.

        Args:
            dados: Dados do boleto
            nosso_numero: Nosso número específico (opcional)

        Returns:
            Dados do boleto emitido

        Raises:
            BoletoError: Em caso de erro na emissão
        """
        try:
            base_url = self.api_client._get_base_url()

            if nosso_numero:
                url = f'{base_url}/cobranca-bancaria/boleto/{nosso_numero}'
                method = 'PUT'
            else:
                url = f'{base_url}/cobranca-bancaria/boleto'
                method = 'POST'

            response = await self.api_client._make_request(
                method, url, scope='boletos_inclusao', json=dados
            )

            return response

        except Exception as e:
            raise BoletoError(f'Erro ao emitir boleto: {e!s}') from e

    async def consultar_boleto(self, nosso_numero: str) -> dict[str, Any]:
        """Consulta um boleto por nosso número de forma assíncrona.

        Args:
            nosso_numero: Nosso número do boleto

        Returns:
            Dados do boleto

        Raises:
            BoletoNaoEncontradoError: Se o boleto não foi encontrado
            BoletoError: Em caso de erro na consulta
        """
        try:
            base_url = self.api_client._get_base_url()
            url = f'{base_url}/cobranca-bancaria/boleto/{nosso_numero}'

            response = await self.api_client._make_request(
                'GET', url, scope='boletos_consulta'
            )

            return response

        except Exception as e:
            if '404' in str(e) or 'não encontrado' in str(e).lower():
                raise BoletoNaoEncontradoError(nosso_numero) from e
            raise BoletoError(f'Erro ao consultar boleto: {e!s}') from e

    async def listar_boletos(
        self,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        situacao: str | None = None,
        **filtros: Any,
    ) -> dict[str, Any]:
        """Lista boletos com filtros de forma assíncrona.

        Args:
            data_inicio: Data de início (YYYY-MM-DD)
            data_fim: Data de fim (YYYY-MM-DD)
            situacao: Situação do boleto
            **filtros: Filtros adicionais

        Returns:
            Lista de boletos
        """
        base_url = self.api_client._get_base_url()
        url = f'{base_url}/cobranca-bancaria/boleto'

        params = {}
        if data_inicio:
            params['dataInicio'] = data_inicio
        if data_fim:
            params['dataFim'] = data_fim
        if situacao:
            params['situacao'] = situacao

        params.update(filtros)

        return await self.api_client._make_request(
            'GET', url, scope='boletos_consulta', params=params
        )

    async def consultar_por_pagador(
        self,
        cpf_cnpj: str,
        data_inicio: str | None = None,
        data_fim: str | None = None,
    ) -> dict[str, Any]:
        """Consulta boletos por CPF/CNPJ do pagador de forma assíncrona.

        Args:
            cpf_cnpj: CPF ou CNPJ do pagador
            data_inicio: Data de início (YYYY-MM-DD)
            data_fim: Data de fim (YYYY-MM-DD)

        Returns:
            Lista de boletos do pagador
        """
        # Valida CPF/CNPJ
        import re

        cpf_cnpj_limpo = re.sub(r'[^\\d]', '', cpf_cnpj)
        if len(cpf_cnpj_limpo) == 11:
            cpf_cnpj_limpo = validate_cpf(cpf_cnpj)
        else:
            cpf_cnpj_limpo = validate_cnpj(cpf_cnpj)

        base_url = self.api_client._get_base_url()
        url = f'{base_url}/cobranca-bancaria/boleto/pagador'

        params = {'cpfCnpj': cpf_cnpj_limpo}

        if data_inicio:
            params['dataInicio'] = data_inicio
        if data_fim:
            params['dataFim'] = data_fim

        return await self.api_client._make_request(
            'GET', url, scope='boletos_consulta', params=params
        )

    async def alterar_boleto(
        self, nosso_numero: str, dados_alteracao: dict[str, Any]
    ) -> dict[str, Any]:
        """Altera dados de um boleto de forma assíncrona.

        Args:
            nosso_numero: Nosso número do boleto
            dados_alteracao: Dados a serem alterados

        Returns:
            Dados do boleto alterado
        """
        base_url = self.api_client._get_base_url()
        url = f'{base_url}/cobranca-bancaria/boleto/{nosso_numero}'

        return await self.api_client._make_request(
            'PATCH', url, scope='boletos_alteracao', json=dados_alteracao
        )

    async def baixar_boleto(
        self, nosso_numero: str, dados_baixa: dict[str, Any]
    ) -> dict[str, Any]:
        """Realiza baixa de um boleto de forma assíncrona.

        Args:
            nosso_numero: Nosso número do boleto
            dados_baixa: Dados da baixa

        Returns:
            Confirmação da baixa
        """
        base_url = self.api_client._get_base_url()
        url = f'{base_url}/cobranca-bancaria/boleto/{nosso_numero}/baixa'

        return await self.api_client._make_request(
            'POST', url, scope='boletos_alteracao', json=dados_baixa
        )

    async def emitir_boletos_lote(
        self, lista_dados: list[dict[str, Any]], max_concorrencia: int = 10
    ) -> list[dict[str, Any]]:
        """Emite múltiplos boletos de forma assíncrona e concorrente.

        Args:
            lista_dados: Lista de dados dos boletos
            max_concorrencia: Número máximo de requisições concorrentes

        Returns:
            Lista de boletos emitidos

        Example:
            >>> dados_boletos = [
            ...     {"valor": 100.50, "pagador": {...}},
            ...     {"valor": 200.75, "pagador": {...}},
            ... ]
            >>> boletos = await api.emitir_boletos_lote(dados_boletos)
        """
        from sicoob.async_client import gather_with_concurrency

        tasks = [self.emitir_boleto(dados) for dados in lista_dados]

        return await gather_with_concurrency(tasks, max_concorrencia)

    async def consultar_boletos_lote(
        self, nossos_numeros: list[str], max_concorrencia: int = 10
    ) -> list[dict[str, Any]]:
        """Consulta múltiplos boletos de forma assíncrona e concorrente.

        Args:
            nossos_numeros: Lista de nossos números
            max_concorrencia: Número máximo de requisições concorrentes

        Returns:
            Lista de dados dos boletos

        Example:
            >>> boletos = await api.consultar_boletos_lote([
            ...     "12345678901",
            ...     "12345678902",
            ...     "12345678903"
            ... ])
        """
        from sicoob.async_client import gather_with_concurrency

        tasks = [self.consultar_boleto(nosso_numero) for nosso_numero in nossos_numeros]

        return await gather_with_concurrency(tasks, max_concorrencia)

    async def processar_vencimentos_hoje(
        self, incluir_vencidos: bool = True
    ) -> dict[str, Any]:
        """Processa boletos com vencimento hoje de forma otimizada.

        Args:
            incluir_vencidos: Se True, inclui boletos já vencidos

        Returns:
            Estatísticas e dados dos boletos processados
        """
        hoje = date.today()
        data_hoje = hoje.strftime('%Y-%m-%d')

        # Consulta boletos do dia
        if incluir_vencidos:
            # Inclui últimos 7 dias para pegar vencidos
            from datetime import timedelta

            data_inicio = (hoje - timedelta(days=7)).strftime('%Y-%m-%d')
            boletos_response = await self.listar_boletos(
                data_inicio=data_inicio, data_fim=data_hoje
            )
        else:
            boletos_response = await self.listar_boletos(
                data_inicio=data_hoje, data_fim=data_hoje
            )

        boletos = boletos_response.get('content', [])

        # Estatísticas
        stats = {
            'total_boletos': len(boletos),
            'valor_total': sum(float(b.get('valor', 0)) for b in boletos),
            'vencimento_hoje': sum(
                1 for b in boletos if b.get('dataVencimento', '').startswith(data_hoje)
            ),
            'data_processamento': data_hoje,
            'boletos': boletos,
        }

        return stats
