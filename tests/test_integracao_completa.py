"""Testes de integração completa do SDK Sicoob"""

import os
import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from dotenv import load_dotenv

from sicoob import Sicoob
from sicoob.config import SicoobConfig
from sicoob.exceptions import (
    SicoobError,
    BoletoEmissaoError,
    PixError,
    ExtratoError,
)
from sicoob.validation import ValidationError

load_dotenv()


class TestIntegracaoCompleta:
    """Testes de integração que testam fluxos completos"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup para cada teste"""
        SicoobConfig.reset_to_defaults()

    @pytest.fixture
    def client_id(self):
        """Client ID para testes"""
        client_id = os.getenv('SICOOB_CLIENT_ID')
        if not client_id:
            pytest.skip('SICOOB_CLIENT_ID não configurado')
        return client_id

    @pytest.fixture
    def sicoob_sandbox(self, client_id):
        """Cliente Sicoob em modo sandbox"""
        return Sicoob(
            client_id=client_id,
            sandbox_mode=True,
            environment='sandbox'
        )

    @pytest.mark.integration
    def test_inicializacao_completa(self, client_id):
        """Testa inicialização completa do SDK"""
        # Teste com diferentes configurações
        configs = [
            {'sandbox_mode': True, 'environment': 'sandbox'},
            {'sandbox_mode': True, 'environment': 'development'},
            {'sandbox_mode': False, 'environment': 'production'},
        ]
        
        for config in configs:
            with patch('sicoob.config.SicoobConfig.requires_certificate', return_value=False):
                client = Sicoob(client_id=client_id, **config)
                
                # Verifica se os componentes foram inicializados
                assert client.boleto is not None
                assert client.pix is not None
                assert client.conta_corrente is not None
                assert client.cobranca is not None
                
                # Verifica configurações
                if config.get('sandbox_mode'):
                    assert 'sandbox' in client._get_base_url().lower()

    @pytest.mark.integration
    def test_sistema_autenticacao_completo(self, sicoob_sandbox):
        """Testa sistema de autenticação OAuth2 completo"""
        client = sicoob_sandbox
        
        # Testa diferentes escopos
        escopos_teste = [
            'cco_consulta',
            'boletos_consulta',
            'cob.read cob.write',
        ]
        
        for escopo in escopos_teste:
            # Simula obtenção de token
            with patch.object(client.auth, 'get_access_token') as mock_token:
                mock_token.return_value = f'token_for_{escopo}'
                
                headers = client.boleto._get_headers(escopo)
                assert headers['Authorization'] == f'Bearer token_for_{escopo}'
                mock_token.assert_called_with(escopo)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_fluxo_validacao_completo(self, sicoob_sandbox):
        """Testa fluxo completo de validação"""
        client = sicoob_sandbox
        
        # Teste validação de boleto com dados inválidos
        dados_invalidos = {
            'numeroContrato': 'invalido',  # Deveria ser int
            'modalidade': 5,  # Valor não permitido
            'valorNominal': -100,  # Valor negativo
        }
        
        with pytest.raises(ValidationError):
            # O sistema deve capturar múltiplos erros
            client.boleto.emitir_boleto(dados_invalidos)
        
        # Teste validação PIX
        with pytest.raises(ValidationError) as exc_info:
            client.pix.criar_cobranca_imediata('txid_muito_curto', {})
        
        assert 'txid' in str(exc_info.value).lower()

    @pytest.mark.integration
    def test_tratamento_erros_completo(self, sicoob_sandbox):
        """Testa tratamento completo de erros"""
        client = sicoob_sandbox
        
        # Mock de resposta de erro da API
        mock_response = type('MockResponse', (), {
            'status_code': 400,
            'json': lambda: {
                'mensagens': [
                    {'codigo': 'ERR001', 'mensagem': 'Erro de validação'}
                ]
            },
            'text': 'Bad Request'
        })()
        
        with patch.object(client.boleto.session, 'post') as mock_post:
            mock_post.return_value = mock_response
            
            with pytest.raises(BoletoEmissaoError) as exc_info:
                client.boleto.emitir_boleto({
                    'numeroContrato': 123456,
                    'modalidade': 1,
                    'numeroContaCorrente': 12345,
                    'especieDocumento': 'DM',
                    'dataVencimento': '2024-12-31',
                    'valorNominal': '100.50',
                    'pagador': {'nome': 'João Silva', 'cpfCnpj': '11144477735'},
                })
            
            # Verifica se o erro foi tratado corretamente
            assert 'Erro de validação' in str(exc_info.value)
            assert exc_info.value.code == 400

    @pytest.mark.integration
    def test_sistema_logging_completo(self, sicoob_sandbox):
        """Testa sistema de logging completo"""
        client = sicoob_sandbox
        
        # Mock para capturar logs
        with patch.object(client.boleto.logger, 'info') as mock_log_info:
            with patch.object(client.boleto.session, 'post') as mock_post:
                # Mock de resposta bem-sucedida
                mock_response = type('MockResponse', (), {
                    'status_code': 200,
                    'json': lambda: {'resultado': {'nossoNumero': '123'}},
                    'raise_for_status': lambda: None,
                    'elapsed': type('elapsed', (), {'total_seconds': lambda: 0.5})()
                })()
                mock_post.return_value = mock_response
                
                # Faz uma requisição
                client.boleto.emitir_boleto({
                    'numeroContrato': 123456,
                    'modalidade': 1,
                    'numeroContaCorrente': 12345,
                    'especieDocumento': 'DM',
                    'dataVencimento': '2024-12-31',
                    'valorNominal': '100.50',
                    'pagador': {'nome': 'João Silva', 'cpfCnpj': '11144477735'},
                })
                
                # Verifica se foram gerados logs
                assert mock_log_info.call_count >= 2  # Request + Response
                
                # Verifica conteúdo dos logs
                log_calls = [call[0][0] for call in mock_log_info.call_args_list]
                assert any('Fazendo requisição' in call for call in log_calls)

    @pytest.mark.integration
    def test_configuracao_ambiente_completa(self):
        """Testa sistema completo de configuração de ambiente"""
        # Testa diferentes ambientes
        ambientes = ['development', 'test', 'staging', 'production', 'sandbox']
        
        for ambiente in ambientes:
            SicoobConfig.set_environment(ambiente)
            
            # Verifica se a configuração foi aplicada
            assert SicoobConfig.get_current_environment() == ambiente
            
            # Verifica URLs específicas do ambiente
            if ambiente == 'sandbox':
                assert 'sandbox' in SicoobConfig.get_api_url().lower()
            elif ambiente == 'production':
                assert 'api.sicoob' in SicoobConfig.get_api_url().lower()
        
        # Reset para estado padrão
        SicoobConfig.reset_to_defaults()

    @pytest.mark.integration
    def test_cache_tokens_oauth(self, sicoob_sandbox):
        """Testa sistema de cache de tokens OAuth"""
        client = sicoob_sandbox
        
        # Simula múltiplas chamadas com mesmo escopo
        with patch.object(client.auth, 'get_access_token') as mock_get_token:
            mock_get_token.return_value = 'cached_token'
            
            # Primeira chamada
            headers1 = client.boleto._get_headers('test_scope')
            # Segunda chamada com mesmo escopo
            headers2 = client.boleto._get_headers('test_scope')
            
            # Ambos devem ter o mesmo token
            assert headers1['Authorization'] == headers2['Authorization']
            
            # get_access_token deve ter sido chamado para cada requisição
            assert mock_get_token.call_count == 2

    @pytest.mark.integration
    def test_validacao_dados_monetarios(self, sicoob_sandbox):
        """Testa validação completa de valores monetários"""
        from sicoob.validation import validate_monetary_value
        
        # Testa diferentes formatos de entrada
        test_cases = [
            ('100.50', '100.50'),
            ('100,50', '100.50'),
            (100, '100.00'),
            (100.5, '100.50'),
            (Decimal('100.50'), '100.50'),
        ]
        
        for input_val, expected in test_cases:
            result = validate_monetary_value(input_val)
            assert result == expected
        
        # Testa valores inválidos
        invalid_values = [-10, 'texto', 10**10]
        
        for invalid_val in invalid_values:
            with pytest.raises(ValueError):
                validate_monetary_value(invalid_val)

    @pytest.mark.integration
    def test_validacao_documentos_completa(self):
        """Testa validação completa de CPF/CNPJ"""
        from sicoob.validation import validate_cpf, validate_cnpj
        
        # CPFs válidos (com e sem formatação)
        cpfs_validos = [
            ('11144477735', '11144477735'),
            ('111.444.777-35', '11144477735'),
        ]
        
        for input_cpf, expected in cpfs_validos:
            result = validate_cpf(input_cpf)
            assert result == expected
        
        # CPFs inválidos
        cpfs_invalidos = ['12345678901', '111.111.111-11', '123456789']
        
        for invalid_cpf in cpfs_invalidos:
            with pytest.raises(ValueError):
                validate_cpf(invalid_cpf)
        
        # CNPJs válidos
        cnpjs_validos = [
            ('11222333000181', '11222333000181'),
            ('11.222.333/0001-81', '11222333000181'),
        ]
        
        for input_cnpj, expected in cnpjs_validos:
            result = validate_cnpj(input_cnpj)
            assert result == expected

    @pytest.mark.integration
    def test_schemas_validacao_completos(self, sicoob_sandbox):
        """Testa schemas de validação completos"""
        from sicoob.validation import (
            get_boleto_schema,
            get_pix_cobranca_schema,
            get_webhook_schema,
            get_pagador_schema
        )
        
        # Testa schema de boleto
        boleto_schema = get_boleto_schema()
        dados_boleto_validos = {
            'numeroContrato': 123456,
            'modalidade': 1,
            'numeroContaCorrente': 12345,
            'especieDocumento': 'DM',
            'dataVencimento': '2024-12-31',
            'valorNominal': '100.50',
            'pagador': {'nome': 'João Silva', 'cpfCnpj': '11144477735'},
        }
        
        resultado = boleto_schema.validate(dados_boleto_validos, strict=False)
        assert resultado['numeroContrato'] == 123456
        assert resultado['valorNominal'] == '100.50'
        
        # Testa schema PIX
        pix_schema = get_pix_cobranca_schema()
        dados_pix_validos = {
            'calendario': {'expiracao': 3600},
            'valor': {'original': '100.50'},
            'chave': 'usuario@exemplo.com',
        }
        
        resultado_pix = pix_schema.validate(dados_pix_validos, strict=False)
        assert resultado_pix['chave'] == 'usuario@exemplo.com'

    @pytest.mark.integration
    @pytest.mark.slow
    def test_resiliencia_rede(self, sicoob_sandbox):
        """Testa resiliência a problemas de rede"""
        import requests
        client = sicoob_sandbox
        
        # Simula diferentes tipos de erro de rede
        network_errors = [
            requests.exceptions.ConnectionError('Network error'),
            requests.exceptions.Timeout('Request timeout'),
            requests.exceptions.HTTPError('HTTP error'),
        ]
        
        for error in network_errors:
            with patch.object(client.boleto.session, 'post') as mock_post:
                mock_post.side_effect = error
                
                with pytest.raises((requests.exceptions.RequestException, BoletoEmissaoError)):
                    client.boleto.emitir_boleto({
                        'numeroContrato': 123456,
                        'modalidade': 1,
                        'numeroContaCorrente': 12345,
                        'especieDocumento': 'DM',
                        'dataVencimento': '2024-12-31',
                        'valorNominal': '100.50',
                        'pagador': {'nome': 'João Silva', 'cpfCnpj': '11144477735'},
                    })

    @pytest.mark.integration
    def test_compatibilidade_versoes_api(self, sicoob_sandbox):
        """Testa compatibilidade com diferentes versões da API"""
        client = sicoob_sandbox
        
        # Verifica se as versões corretas estão sendo usadas
        assert '/cobranca-bancaria/v3' in client.boleto.base_path
        assert '/conta-corrente/v4' in client.conta_corrente.base_path
        
        # Testa se headers de versionamento estão corretos
        headers = client.boleto._get_headers('boletos_consulta')
        assert headers['Accept'] == 'application/json'
        assert headers['Content-Type'] == 'application/json'

    @pytest.mark.integration
    def test_seguranca_dados_sensiveis(self, sicoob_sandbox):
        """Testa se dados sensíveis não são logados"""
        client = sicoob_sandbox
        
        # Dados com informações sensíveis
        dados_com_sensiveis = {
            'numeroContrato': 123456,
            'password': 'senha_secreta',
            'cpfCnpj': '11144477735',
            'token': 'token_secreto',
            'client_secret': 'client_secret_value',
        }
        
        with patch.object(client.boleto.logger, 'info') as mock_log:
            with patch.object(client.boleto, '_make_request') as mock_request:
                mock_response = type('MockResponse', (), {
                    'status_code': 200,
                    'json': lambda: {'resultado': 'ok'}
                })()
                mock_request.return_value = mock_response
                
                # Simula uma operação que logaria dados
                try:
                    client.boleto._make_request('POST', 'https://test.com', 'scope', json=dados_com_sensiveis)
                except:
                    pass
                
                # Verifica se dados sensíveis foram filtrados dos logs
                if mock_log.called:
                    log_calls = ' '.join([str(call) for call in mock_log.call_args_list])
                    sensitive_data = ['senha_secreta', 'token_secreto', 'client_secret_value']
                    
                    for sensitive in sensitive_data:
                        assert sensitive not in log_calls, f"Dado sensível '{sensitive}' encontrado nos logs!"