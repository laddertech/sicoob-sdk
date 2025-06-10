from unittest.mock import Mock

import pytest

from sicoob import Sicoob


@pytest.fixture
def mock_oauth_client() -> Mock:
    """Fixture para mock do OAuth2Client"""
    mock = Mock()
    mock.get_access_token.return_value = 'mock_access_token'
    return mock


@pytest.fixture
def sicoob_client(mock_oauth_client: Mock) -> Sicoob:
    """Fixture para cliente Sicoob com autenticação mockada"""
    client = Sicoob(
        client_id='test_id', certificado='test_cert.pem', chave_privada='test_key.key'
    )
    client.oauth_client = mock_oauth_client
    client.session = Mock()
    return client
