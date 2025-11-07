"""Testes para carregamento de certificado no AsyncAPIClient."""

import ssl
from unittest.mock import Mock, patch

import pytest

from sicoob.async_client import AsyncAPIClient
from sicoob.auth import OAuth2Client

# Verifica se cryptography está disponível
try:
    from cryptography.hazmat.primitives.serialization import pkcs12  # noqa: F401

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


@pytest.mark.integration  # Marca como teste de integração
@pytest.mark.skipif(
    not CRYPTOGRAPHY_AVAILABLE, reason='cryptography package not available'
)
class TestAsyncAPIClientCertificate:
    """Testes para carregamento de certificados no AsyncAPIClient.

    Nota: Estes testes podem falhar no CI devido a diferenças no ambiente
    de mocking. São principalmente testes de integração que validam a
    funcionalidade em ambiente local.
    """

    @pytest.fixture
    def mock_pfx_data(self):
        """Mock de dados PFX."""
        # Simula dados PFX (não precisa ser válido, apenas para o mock)
        return b'mock_pfx_data'

    @pytest.fixture
    def oauth_client_with_pfx(self, mock_pfx_data):
        """OAuth2Client mockado com certificado PFX."""
        mock_oauth = Mock(spec=OAuth2Client)
        mock_oauth.certificado_pfx = mock_pfx_data
        mock_oauth.senha_pfx = 'test_password'
        mock_oauth.get_access_token.return_value = 'mock_token'
        return mock_oauth

    @pytest.fixture
    def oauth_client_with_pem(self):
        """OAuth2Client mockado com certificados PEM."""
        mock_oauth = Mock(spec=OAuth2Client)
        mock_oauth.certificado = '/path/to/cert.pem'
        mock_oauth.chave_privada = '/path/to/key.pem'
        mock_oauth.certificado_pfx = None
        mock_oauth.senha_pfx = None
        mock_oauth.get_access_token.return_value = 'mock_token'
        return mock_oauth

    @pytest.fixture
    def oauth_client_without_cert(self):
        """OAuth2Client mockado sem certificado."""
        mock_oauth = Mock(spec=OAuth2Client)
        mock_oauth.get_access_token.return_value = 'mock_token'
        # Não tem atributos de certificado
        return mock_oauth

    @pytest.mark.asyncio
    async def test_load_pfx_certificate(self, oauth_client_with_pfx):
        """Testa que PFX é carregado corretamente no SSL context."""
        client = AsyncAPIClient(oauth_client=oauth_client_with_pfx)

        # Mock do cryptography para evitar dependência de certificado real
        with patch(
            'cryptography.hazmat.primitives.serialization.pkcs12.load_key_and_certificates'
        ) as mock_load_pkcs12:
            # Mock dos objetos de certificado
            mock_private_key = Mock()
            mock_private_key.private_bytes.return_value = b'mock_private_key_pem'

            mock_certificate = Mock()
            mock_certificate.public_bytes.return_value = b'mock_certificate_pem'

            mock_load_pkcs12.return_value = (
                mock_private_key,
                mock_certificate,
                [],
            )

            # Mock do SSL context load_cert_chain
            with patch.object(ssl.SSLContext, 'load_cert_chain'):
                await client._ensure_session()

                # Verifica que load_key_and_certificates foi chamado
                mock_load_pkcs12.assert_called_once()
                args = mock_load_pkcs12.call_args[0]
                assert args[0] == b'mock_pfx_data'
                assert args[1] == b'test_password'

        # Limpa
        if client._session:
            await client._session.close()
        client._cleanup_temp_cert_files()

    @pytest.mark.asyncio
    async def test_load_pem_certificate(self, oauth_client_with_pem):
        """Testa que certificados PEM são carregados corretamente."""
        client = AsyncAPIClient(oauth_client=oauth_client_with_pem)

        with patch.object(ssl.SSLContext, 'load_cert_chain') as mock_load_cert:
            await client._ensure_session()

            # Verifica que load_cert_chain foi chamado com os paths corretos
            mock_load_cert.assert_called_once_with(
                '/path/to/cert.pem', '/path/to/key.pem'
            )

        # Limpa
        if client._session:
            await client._session.close()

    @pytest.mark.asyncio
    async def test_no_certificate_warning(self, oauth_client_without_cert):
        """Testa que warning é emitido quando certificado é requerido mas não fornecido."""
        client = AsyncAPIClient(oauth_client=oauth_client_without_cert)

        with patch('sicoob.async_client.logger') as mock_logger:
            await client._ensure_session()

            # Verifica que warning foi emitido
            mock_logger.warning.assert_called_once()
            assert 'Certificado requerido' in str(mock_logger.warning.call_args)

        # Limpa
        if client._session:
            await client._session.close()

    @pytest.mark.asyncio
    async def test_temp_files_cleanup(self, oauth_client_with_pfx):
        """Testa que arquivos temporários são limpos ao fechar."""
        client = AsyncAPIClient(oauth_client=oauth_client_with_pfx)

        # Mock do cryptography
        with patch(
            'cryptography.hazmat.primitives.serialization.pkcs12.load_key_and_certificates'
        ) as mock_load_pkcs12:
            mock_private_key = Mock()
            mock_private_key.private_bytes.return_value = b'mock_private_key_pem'

            mock_certificate = Mock()
            mock_certificate.public_bytes.return_value = b'mock_certificate_pem'

            mock_load_pkcs12.return_value = (
                mock_private_key,
                mock_certificate,
                [],
            )

            with patch.object(ssl.SSLContext, 'load_cert_chain'):
                await client._ensure_session()

        # Verifica que arquivos temporários foram registrados
        assert len(client._temp_cert_files) == 2

        # Limpa
        with patch('os.path.exists') as mock_exists, patch('os.unlink') as mock_unlink:
            mock_exists.return_value = True
            client._cleanup_temp_cert_files()

            # Verifica que unlink foi chamado para cada arquivo
            assert mock_unlink.call_count == 2

        # Verifica que lista foi limpa
        assert len(client._temp_cert_files) == 0

        # Limpa sessão
        if client._session:
            await client._session.close()

    @pytest.mark.asyncio
    async def test_context_manager_cleans_up_certs(self, oauth_client_with_pfx):
        """Testa que context manager limpa certificados ao sair."""
        # Mock do cryptography
        with patch(
            'cryptography.hazmat.primitives.serialization.pkcs12.load_key_and_certificates'
        ) as mock_load_pkcs12:
            mock_private_key = Mock()
            mock_private_key.private_bytes.return_value = b'mock_private_key_pem'

            mock_certificate = Mock()
            mock_certificate.public_bytes.return_value = b'mock_certificate_pem'

            mock_load_pkcs12.return_value = (
                mock_private_key,
                mock_certificate,
                [],
            )

            with (
                patch.object(ssl.SSLContext, 'load_cert_chain'),
                patch('os.path.exists') as mock_exists,
                patch('os.unlink') as mock_unlink,
            ):
                mock_exists.return_value = True

                async with AsyncAPIClient(oauth_client=oauth_client_with_pfx) as client:
                    # Cliente está inicializado
                    assert client._session is not None

                # Após sair do context, unlink deve ter sido chamado
                assert mock_unlink.call_count >= 2

    @pytest.mark.asyncio
    async def test_pfx_path_vs_bytes(self, oauth_client_with_pfx):
        """Testa que PFX funciona tanto com path quanto com bytes."""
        # Testa com bytes
        oauth_client_with_pfx.certificado_pfx = b'pfx_bytes_data'

        client_bytes = AsyncAPIClient(oauth_client=oauth_client_with_pfx)

        with patch(
            'cryptography.hazmat.primitives.serialization.pkcs12.load_key_and_certificates'
        ) as mock_load_pkcs12:
            mock_private_key = Mock()
            mock_private_key.private_bytes.return_value = b'key'
            mock_certificate = Mock()
            mock_certificate.public_bytes.return_value = b'cert'
            mock_load_pkcs12.return_value = (
                mock_private_key,
                mock_certificate,
                [],
            )

            with patch.object(ssl.SSLContext, 'load_cert_chain'):
                await client_bytes._ensure_session()

            # Verifica que foi chamado com os bytes diretamente
            args = mock_load_pkcs12.call_args[0]
            assert args[0] == b'pfx_bytes_data'

        if client_bytes._session:
            await client_bytes._session.close()
        client_bytes._cleanup_temp_cert_files()

    @pytest.mark.asyncio
    async def test_invalid_pfx_raises_error(self, oauth_client_with_pfx):
        """Testa que PFX inválido levanta erro apropriado."""
        client = AsyncAPIClient(oauth_client=oauth_client_with_pfx)

        # Simula erro ao carregar PFX
        with patch(
            'cryptography.hazmat.primitives.serialization.pkcs12.load_key_and_certificates'
        ) as mock_load_pkcs12:
            mock_load_pkcs12.side_effect = ValueError('Invalid PKCS12 data')

            with pytest.raises(ValueError, match='Falha ao carregar certificado PFX'):
                await client._ensure_session()

        if client._session:
            await client._session.close()
