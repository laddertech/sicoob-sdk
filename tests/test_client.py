from unittest.mock import Mock

def test_client_init(sicoob_client):
    """Testa a inicialização do cliente"""
    assert sicoob_client.client_id == "test_id"
    assert sicoob_client.certificado == "test_cert.pem"
    assert sicoob_client.chave_privada == "test_key.key"

def test_get_token(sicoob_client, mock_oauth_client):
    """Testa a obtenção de token"""
    # Configura o mock para retornar o token esperado
    mock_oauth_client.get_access_token.return_value = "mock_access_token"

    # Testa através da interface pública
    token = sicoob_client._get_token()
    assert token == {"access_token": "mock_access_token"}
    mock_oauth_client.get_access_token.assert_called_once()

def test_saldo(sicoob_client):
    """Testa a consulta de saldo"""
    mock_response = Mock()
    mock_response.json.return_value = {"saldo": 1000.00}
    sicoob_client.session.get.return_value = mock_response

    saldo = sicoob_client.conta_corrente.saldo(
        numero_conta="12345"
    )

    assert saldo == {"saldo": 1000.00}
    sicoob_client.session.get.assert_called_once()
