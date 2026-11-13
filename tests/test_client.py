from unittest.mock import Mock, patch

import pytest

from sicoob.client import Sicoob


def test_client_init(sicoob_client: Sicoob) -> None:
    """Testa a inicialização do cliente com certificado PEM"""
    if sicoob_client.client_id != 'test_id':
        raise ValueError('client_id não corresponde ao esperado')
    if sicoob_client.certificado != 'test_cert.pem':
        raise ValueError('certificado não corresponde ao esperado')
    if sicoob_client.chave_privada != 'test_key.key':
        raise ValueError('chave_privada não corresponde ao esperado')


def test_client_init_pfx() -> None:
    """Testa a inicialização do cliente com certificado PFX"""
    with (
        patch('sicoob.auth.oauth.requests_pkcs12.Pkcs12Adapter') as mock_adapter,
        patch('sicoob.auth.oauth.requests.Session') as mock_session,
    ):
        mock_adapter_instance = Mock()
        mock_adapter.return_value = mock_adapter_instance

        client = Sicoob(
            client_id='test_id',
            certificado_pfx='test_cert.pfx',
            senha_pfx='test_password',
            environment='production',  # Força production para requer certificado
        )

        if client.client_id != 'test_id':
            raise ValueError('client_id não corresponde ao esperado')
        if client.certificado_pfx != 'test_cert.pfx':
            raise ValueError('certificado_pfx não corresponde ao esperado')
        if client.senha_pfx != 'test_password':
            raise ValueError('senha_pfx não corresponde ao esperado')

        mock_adapter.assert_called_once_with(
            pkcs12_data=None,
            pkcs12_filename='test_cert.pfx',
            pkcs12_password='test_password',
        )
        mock_session.return_value.mount.assert_called_once_with(
            'https://', mock_adapter_instance
        )


def test_client_init_invalid() -> None:
    """Testa a inicialização com parâmetros inválidos"""
    with pytest.raises(ValueError):
        Sicoob(client_id='test_id')  # Sem certificado


CERT_ENV = {
    'SICOOB_CLIENT_ID': 'client-do-ambiente',
    'SICOOB_CERTIFICADO_PFX': 'outro.pfx',
    'SICOOB_SENHA_PFX': 'senha-do-ambiente',
    'SICOOB_ENVIRONMENT': 'sandbox',
}


@pytest.mark.parametrize('client_id', [None, '', '   ', 123])
def test_client_id_ausente_nao_usa_ambiente(client_id) -> None:
    """client_id vazio é erro: nunca cai na credencial do ambiente"""
    with patch.dict('os.environ', CERT_ENV):
        with pytest.raises(ValueError, match='client_id'):
            Sicoob(
                client_id=client_id,
                certificado_pfx=b'pfx',
                senha_pfx='s',
                environment='production',
            )


def test_certificado_ausente_nao_usa_ambiente() -> None:
    """Sem certificado explícito em produção é erro, mesmo com env definida"""
    with patch.dict('os.environ', CERT_ENV):
        with pytest.raises(ValueError, match='certificado'):
            Sicoob(client_id='id', environment='production')


def test_ambiente_desconhecido_e_erro() -> None:
    with pytest.raises(ValueError, match='Ambiente desconhecido'):
        Sicoob(client_id='id', environment='producao')


@patch('sicoob.auth.oauth.requests_pkcs12.Pkcs12Adapter')
def test_instancias_tem_ambientes_independentes(_adapter) -> None:
    """Criar um cliente sandbox não muda o ambiente de outro, nem o global"""
    from sicoob.config import Environment, SicoobConfig

    prod = Sicoob(client_id='a', certificado_pfx=b'x', senha_pfx='s')
    sandbox = Sicoob(client_id='b', environment='sandbox', sandbox_token='t')
    assert prod.config.environment is Environment.PRODUCTION
    assert prod.oauth_client.config.base_url == 'https://api.sicoob.com.br'
    assert sandbox.oauth_client.config.is_sandbox
    assert sandbox.oauth_client.sandbox_token == 't'
    assert SicoobConfig.get_current_config().environment is Environment.PRODUCTION
    assert prod.cobranca.boleto._get_base_url() == 'https://api.sicoob.com.br'
    assert sandbox.cobranca.boleto._get_base_url().startswith(
        'https://sandbox.sicoob.com.br'
    )


def test_from_env_le_variaveis_explicitamente() -> None:
    with patch.dict('os.environ', {**CERT_ENV, 'SICOOB_SANDBOX_TOKEN': 'tk'}):
        client = Sicoob.from_env(dotenv=False)
    assert client.client_id == 'client-do-ambiente'
    assert client.config.is_sandbox
    assert client.oauth_client.sandbox_token == 'tk'


def test_from_env_overrides_prevalecem() -> None:
    with patch.dict('os.environ', CERT_ENV):
        client = Sicoob.from_env(dotenv=False, client_id='explicito')
    assert client.client_id == 'explicito'


def test_get_token(sicoob_client: Sicoob, mock_oauth_client: Mock) -> None:
    """Testa a obtenção de token"""
    # Configura o mock para retornar o token esperado
    mock_oauth_client.get_access_token.return_value = 'mock_access_token'

    # Testa através da interface pública
    token = sicoob_client._get_token()
    if token != {'access_token': 'mock_access_token'}:
        raise ValueError('Token não corresponde ao esperado')
    mock_oauth_client.get_access_token.assert_called_once()


def test_saldo(sicoob_client: Sicoob) -> None:
    """Testa a consulta de saldo"""
    mock_response = Mock()
    mock_response.json.return_value = {'saldo': 1000.00}
    sicoob_client.session.get.return_value = mock_response

    saldo = sicoob_client.conta_corrente.saldo(numero_conta='12345')

    if saldo != {'saldo': 1000.00}:
        raise ValueError('Saldo não corresponde ao esperado')
    sicoob_client.session.get.assert_called_once()
