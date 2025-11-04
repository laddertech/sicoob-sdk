"""Testes para o sistema de exceções do Sicoob SDK"""

from unittest.mock import Mock

from sicoob.exceptions import (
    AutenticacaoError,
    BoletoAlteracaoError,
    BoletoAlteracaoPagadorError,
    BoletoBaixaError,
    BoletoConsultaError,
    BoletoConsultaFaixaError,
    BoletoConsultaPagadorError,
    BoletoEmissaoError,
    BoletoError,
    BoletoNaoEncontradoError,
    BoletoWebhookError,
    CobrancaPixNaoEncontradaError,
    ContaCorrenteError,
    ExtratoError,
    PixError,
    RespostaInvalidaError,
    SaldoError,
    SicoobError,
    TransferenciaError,
    WebhookPixNaoEncontradoError,
)


class TestSicoobError:
    """Testes para exceção base SicoobError"""

    def test_basic_error(self):
        """Testa criação básica de erro"""
        error = SicoobError('Erro básico')
        assert str(error) == 'Erro básico'
        assert error.message == 'Erro básico'
        assert error.code is None
        assert error.response is None

    def test_error_with_code(self):
        """Testa erro com código"""
        error = SicoobError('Erro com código', code=400)
        assert error.code == 400

    def test_error_with_response(self):
        """Testa erro com resposta HTTP"""
        mock_response = Mock()
        mock_response.status_code = 500

        error = SicoobError('Erro com resposta', response=mock_response)
        assert error.response == mock_response

    def test_error_inheritance(self):
        """Testa se SicoobError herda de Exception"""
        error = SicoobError('Test')
        assert isinstance(error, Exception)


class TestAutenticacaoError:
    """Testes para AutenticacaoError"""

    def test_auth_error_basic(self):
        """Testa erro de autenticação básico"""
        error = AutenticacaoError('Falha na autenticação')
        assert isinstance(error, SicoobError)
        assert str(error) == 'Falha na autenticação'

    def test_auth_error_with_details(self):
        """Testa erro de autenticação com detalhes"""
        error = AutenticacaoError('Token inválido', code=401)
        assert error.code == 401
        assert 'Token inválido' in str(error)


class TestRespostaInvalidaError:
    """Testes para RespostaInvalidaError"""

    def test_resposta_invalida_basic(self):
        """Testa erro de resposta inválida básico"""
        error = RespostaInvalidaError('JSON malformado')
        assert isinstance(error, SicoobError)


class TestBoletoErrors:
    """Testes para exceções de boleto"""

    def test_boleto_error_hierarchy(self):
        """Testa hierarquia das exceções de boleto"""
        errors = [
            BoletoError('Erro genérico'),
            BoletoEmissaoError('Erro de emissão'),
            BoletoConsultaError('Erro de consulta'),
            BoletoNaoEncontradoError('123456'),
            BoletoWebhookError('Erro de webhook'),
            BoletoAlteracaoError('Erro de alteração'),
            BoletoBaixaError('Erro de baixa'),
            BoletoAlteracaoPagadorError('Erro alteração pagador'),
            BoletoConsultaFaixaError('Erro consulta faixa'),
            BoletoConsultaPagadorError('Erro consulta pagador'),
        ]

        for error in errors:
            assert isinstance(error, SicoobError)
            # Todos exceto BoletoError devem herdar de BoletoError
            if not isinstance(error, BoletoError):
                assert isinstance(error, BoletoError)

    def test_boleto_emissao_error_with_dados(self):
        """Testa erro de emissão com dados do boleto"""
        dados_boleto = {'valor': 100.0, 'pagador': 'João'}
        error = BoletoEmissaoError('Erro na emissão', dados_boleto=dados_boleto)

        assert error.dados_boleto == dados_boleto

    def test_boleto_nao_encontrado_with_id(self):
        """Testa erro de boleto não encontrado com ID"""
        error = BoletoNaoEncontradoError('123456')
        assert error.nosso_numero == '123456'
        assert '123456' in str(error)

    def test_boleto_webhook_error_with_url(self):
        """Testa erro de webhook com URL"""
        webhook_data = {'url': 'https://webhook.test.com'}
        error = BoletoWebhookError(
            'Erro no webhook',
            url='https://webhook.test.com',
            dados_webhook=webhook_data,
        )

        assert error.url == 'https://webhook.test.com'
        assert error.dados_webhook == webhook_data

    def test_boleto_alteracao_with_details(self):
        """Testa erro de alteração com detalhes"""
        dados = {'novo_valor': 200.0}
        error = BoletoAlteracaoError(
            'Erro na alteração', nosso_numero='123456', dados_alteracao=dados
        )

        assert error.nosso_numero == '123456'
        assert error.dados_alteracao == dados

    def test_boleto_consulta_faixa_with_params(self):
        """Testa erro de consulta de faixa"""
        error = BoletoConsultaFaixaError('Erro consulta faixa', numero_cliente=123456)

        assert error.numero_cliente == 123456

    def test_boleto_consulta_pagador_with_params(self):
        """Testa erro de consulta por pagador"""
        error = BoletoConsultaPagadorError(
            'Erro consulta pagador', numero_cpf_cnpj='12345678901'
        )

        assert error.numero_cpf_cnpj == '12345678901'


class TestPixErrors:
    """Testes para exceções PIX"""

    def test_pix_error_hierarchy(self):
        """Testa hierarquia das exceções PIX"""
        errors = [
            PixError('Erro PIX genérico'),
            CobrancaPixNaoEncontradaError('abc123'),
            WebhookPixNaoEncontradoError('usuario@exemplo.com'),
        ]

        for error in errors:
            assert isinstance(error, SicoobError)
            if not isinstance(error, PixError):
                assert isinstance(error, PixError)

    def test_cobranca_pix_nao_encontrada_with_txid(self):
        """Testa erro de cobrança PIX não encontrada"""
        error = CobrancaPixNaoEncontradaError('abc123')
        assert error.txid == 'abc123'
        assert 'abc123' in str(error)

    def test_webhook_pix_nao_encontrado_with_chave(self):
        """Testa erro de webhook PIX não encontrado"""
        error = WebhookPixNaoEncontradoError('usuario@exemplo.com')
        assert error.chave == 'usuario@exemplo.com'
        assert 'usuario@exemplo.com' in str(error)


class TestContaCorrenteErrors:
    """Testes para exceções de conta corrente"""

    def test_conta_corrente_error_hierarchy(self):
        """Testa hierarquia das exceções de conta corrente"""
        errors = [
            ContaCorrenteError('Erro genérico'),
            ExtratoError('Erro de extrato'),
            SaldoError('Erro de saldo'),
            TransferenciaError('Erro de transferência'),
        ]

        for error in errors:
            assert isinstance(error, SicoobError)
            if not isinstance(error, ContaCorrenteError):
                assert isinstance(error, ContaCorrenteError)

    def test_extrato_error_with_periodo(self):
        """Testa erro de extrato com período"""
        error = ExtratoError('Erro no extrato', periodo='01/2024')
        assert error.periodo == '01/2024'

    def test_saldo_error_with_conta(self):
        """Testa erro de saldo com número da conta"""
        error = SaldoError('Erro consulta saldo', conta='12345')
        assert error.conta == '12345'

    def test_transferencia_error_with_dados(self):
        """Testa erro de transferência com dados"""
        dados = {'valor': 1000.0, 'conta_destino': '67890'}
        error = TransferenciaError('Erro na transferência', dados=dados)
        assert error.dados == dados


class TestErrorMessages:
    """Testes para mensagens de erro"""

    def test_error_string_representation(self):
        """Testa representação string dos erros"""
        errors_and_messages = [
            (SicoobError('Erro base'), 'Erro base'),
            (BoletoError('Erro boleto'), 'Erro boleto'),
            (PixError('Erro PIX'), 'Erro PIX'),
            (ContaCorrenteError('Erro conta'), 'Erro conta'),
        ]

        for error, expected_message in errors_and_messages:
            assert str(error) == expected_message

    def test_error_repr(self):
        """Testa representação repr dos erros"""
        error = SicoobError('Test error', code=400)
        repr_str = repr(error)

        assert 'SicoobError' in repr_str
        assert 'Test error' in repr_str


class TestErrorAttributes:
    """Testes para atributos específicos dos erros"""

    def test_error_with_mensagens(self):
        """Testa erro com mensagens da API"""
        mensagens = [
            {'codigo': 'ERR001', 'mensagem': 'Campo obrigatório'},
            {'codigo': 'ERR002', 'mensagem': 'Valor inválido'},
        ]

        error = BoletoEmissaoError('Erro validação', mensagens=mensagens)
        assert error.mensagens == mensagens

    def test_error_default_attributes(self):
        """Testa atributos padrão dos erros"""
        error = SicoobError('Test')

        # Verifica atributos padrão
        assert hasattr(error, 'message')
        assert hasattr(error, 'code')
        assert hasattr(error, 'response')

        # Valores padrão
        assert error.code is None
        assert error.response is None

    def test_error_custom_attributes(self):
        """Testa atributos customizados em erros específicos"""
        # BoletoNaoEncontradoError deve ter atributo nosso_numero
        error = BoletoNaoEncontradoError('123')
        assert hasattr(error, 'nosso_numero')
        assert error.nosso_numero == '123'

        # CobrancaPixNaoEncontradaError deve ter atributo txid
        error = CobrancaPixNaoEncontradaError('abc')
        assert hasattr(error, 'txid')
        assert error.txid == 'abc'
