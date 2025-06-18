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
    with patch.dict('os.environ', {}, clear=True):  # Limpa variáveis de ambiente
        with pytest.raises(ValueError):
            Sicoob(client_id='test_id')  # Sem certificado


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
