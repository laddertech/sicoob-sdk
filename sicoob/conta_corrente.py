import requests

from .api_client import APIClientBase
from .auth import OAuth2Client
from .exceptions import ExtratoError, SaldoError, TransferenciaError


class ContaCorrenteAPI(APIClientBase):
    """Classe para operações de conta corrente no Sicoob."""

    def __init__(
        self,
        oauth_client: OAuth2Client,
        session: requests.Session,
        sandbox_mode: bool = False,
    ) -> None:
        """Inicializa a API de conta corrente.

        Args:
            oauth_client: Cliente OAuth2 para autenticação
            session: Sessão HTTP existente
            sandbox_mode: Se True, usa URL de sandbox (default: False)
        """
        super().__init__(oauth_client, session, sandbox_mode)
        self.base_path = '/conta-corrente/v4'

    def extrato(
        self,
        mes: int,
        ano: int,
        dia_inicial: int,
        dia_final: int,
        numero_conta_corrente: int,
        agrupar_cnab: bool = False,
    ) -> list[dict]:
        """Obtém o extrato da conta corrente por período.

        Args:
            mes: Mês do extrato (1-12)
            ano: Ano do extrato (4 dígitos)
            dia_inicial: Dia inicial para o extrato (1-31)
            dia_final: Dia final para o extrato (1-31)
            numero_conta_corrente: Número da conta corrente (obrigatório)
            agrupar_cnab: Se deve agrupar movimento proveniente do CNAB (opcional)

        Returns:
            Lista de dicts com as transações do período

        Raises:
            ExtratoError: Em caso de falha na requisição de extrato
        """
        try:
            headers = self._get_headers(scope='cco_consulta')
            headers['client_id'] = str(self.oauth_client.client_id)

            params = {
                'diaInicial': dia_inicial,
                'diaFinal': dia_final,
                'numeroContaCorrente': numero_conta_corrente,
                'agruparCNAB': str(agrupar_cnab).lower(),
            }

            url = f'{self._get_base_url()}{self.base_path}/extrato/{mes}/{ano}'
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ExtratoError(
                    f'Extrato não encontrado - Status: {e.response.status_code}',
                    code=e.response.status_code,
                    periodo=f'{dia_inicial}/{mes}/{ano}',
                ) from e
            raise ExtratoError(
                f'Falha ao consultar extrato - Status: {e.response.status_code}',
                code=e.response.status_code,
                periodo=f'{dia_inicial}/{mes}/{ano}',
            ) from e
        except Exception as e:
            raise ExtratoError(f'Erro ao consultar extrato: {e!s}') from e

    def saldo(self, numero_conta: str | None = None) -> dict:
        """Obtém o saldo atual da conta corrente.

        Args:
            numero_conta: Número da conta (opcional se já configurado no cliente)

        Returns:
            Dict com informações de saldo

        Raises:
            SaldoError: Em caso de falha na consulta de saldo
        """
        try:
            params = {}
            if numero_conta:
                params['numeroConta'] = numero_conta

            url = f'{self._get_base_url()}{self.base_path}/saldo'
            response = self.session.get(
                url, params=params, headers=self._get_headers(scope='cco_consulta')
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            raise SaldoError(
                f'Falha na consulta de saldo - Status: {e.response.status_code}',
                code=e.response.status_code,
                conta=numero_conta,
            ) from e
        except Exception as e:
            raise SaldoError(
                f'Erro ao consultar saldo: {e!s}', conta=numero_conta
            ) from e

    def transferencia(
        self,
        valor: float,
        conta_destino: str,
        tipo_transferencia: str = 'TED',
        descricao: str | None = None,
        numero_conta: str | None = None,
    ) -> dict:
        """Realiza uma transferência entre contas.

        Args:
            valor: Valor da transferência
            conta_destino: Número da conta destino
            tipo_transferencia: Tipo de transferência (TED/DOC/PIX)
            descricao: Descrição opcional da transferência
            numero_conta: Número da conta origem (opcional se já configurado)

        Returns:
            Dict com informações da transferência

        Raises:
            TransferenciaError: Em caso de falha na transferência
        """
        try:
            payload = {
                'valor': valor,
                'contaDestino': conta_destino,
                'tipoTransferencia': tipo_transferencia,
            }
            if descricao:
                payload['descricao'] = descricao
            if numero_conta:
                payload['numeroConta'] = numero_conta

            url = f'{self._get_base_url()}{self.base_path}/transferencia'
            response = self.session.post(
                url, json=payload, headers=self._get_headers(scope='cco_transferencias')
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            raise TransferenciaError(
                f'Falha na transferência - Status: {e.response.status_code}',
                code=e.response.status_code,
                dados=payload,
            ) from e
        except Exception as e:
            raise TransferenciaError(
                f'Erro na transferência: {e!s}', dados=payload
            ) from e
