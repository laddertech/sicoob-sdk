Exemplos de Uso
===============

Esta seção apresenta exemplos práticos de uso do Sicoob SDK.

Autenticação
------------

Certificado PEM/Key
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sicoob import Sicoob

   cliente = Sicoob(
       client_id="seu_client_id",
       certificate_path="/path/to/certificate.pem",
       private_key_path="/path/to/private_key.key",
       sandbox_mode=True
   )

Certificado PFX
~~~~~~~~~~~~~~

.. code-block:: python

   from sicoob import Sicoob

   cliente = Sicoob(
       client_id="seu_client_id",
       pfx_path="/path/to/certificate.pfx",
       pfx_password="senha_do_certificado",
       sandbox_mode=True
   )

PIX
---

Cobrança Imediata
~~~~~~~~~~~~~~~~

.. code-block:: python

   import uuid
   from sicoob import Sicoob

   cliente = Sicoob(
       client_id="seu_client_id",
       certificate_path="/path/to/certificate.pem",
       private_key_path="/path/to/private_key.key",
       sandbox_mode=True
   )

   # Gerar TXID único
   txid = str(uuid.uuid4()).replace('-', '')[:35]

   cobranca = cliente.pix.criar_cobranca_imediata(
       txid=txid,
       dados={
           "calendario": {"expiracao": 3600},
           "valor": {"original": "123.45"},
           "chave": "usuario@exemplo.com",
           "solicitacaoPagador": "Pagamento do pedido #123"
       }
   )

   print(f"QR Code: {cobranca['qrcode']}")
   print(f"PIX Copia e Cola: {cobranca['pixCopiaECola']}")

Consultar Cobrança
~~~~~~~~~~~~~~~~~

.. code-block:: python

   cobranca = cliente.pix.consultar_cobranca_imediata(txid="seu_txid_aqui")

   print(f"Status: {cobranca['status']}")
   print(f"Valor: {cobranca['valor']['original']}")

Cobrança com Vencimento
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import uuid
   from datetime import datetime, timedelta

   txid = str(uuid.uuid4()).replace('-', '')[:35]
   vencimento = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

   cobranca = cliente.pix.criar_cobranca_com_vencimento(
       txid=txid,
       dados={
           "calendario": {"dataDeVencimento": vencimento},
           "valor": {"original": "500.00"},
           "chave": "usuario@exemplo.com",
           "solicitacaoPagador": "Fatura mensal - Janeiro 2024"
       }
   )

   print(f"QR Code: {cobranca['qrcode']}")

Webhook PIX
~~~~~~~~~~~

.. code-block:: python

   # Cadastrar webhook
   webhook = cliente.pix.cadastrar_webhook(
       chave="usuario@exemplo.com",
       url="https://seu-site.com/webhook/pix"
   )

   # Consultar webhook
   webhook_info = cliente.pix.consultar_webhook("usuario@exemplo.com")
   print(f"URL: {webhook_info['webhookUrl']}")

   # Excluir webhook
   cliente.pix.excluir_webhook("usuario@exemplo.com")

Listar Cobranças
~~~~~~~~~~~~~~~

.. code-block:: python

   from datetime import datetime, timedelta

   inicio = (datetime.now() - timedelta(days=30)).isoformat() + "Z"
   fim = datetime.now().isoformat() + "Z"

   cobrancas = cliente.pix.listar_cobrancas(
       inicio=inicio,
       fim=fim,
       status="ATIVA"
   )

   for cob in cobrancas['cobs']:
       print(f"TXID: {cob['txid']}, Valor: {cob['valor']['original']}")

Boletos
-------

Emitir Boleto
~~~~~~~~~~~~

.. code-block:: python

   from datetime import datetime, timedelta

   vencimento = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

   boleto = cliente.boleto.emitir_boleto({
       "numeroConvenio": "123456",
       "numeroCarteira": "1",
       "numeroVariacaoCarteira": "1",
       "codigoModalidade": "1",
       "dataVencimento": vencimento,
       "valorNominal": "100.50",
       "especieDocumento": "DM",
       "numeroConta": "12345",
       "numeroAgencia": "1234",
       "pagador": {
           "nome": "João Silva",
           "documento": "12345678901",
           "endereco": {
               "logradouro": "Rua das Flores, 123",
               "cidade": "São Paulo",
               "uf": "SP",
               "cep": "01234567"
           }
       }
   })

   print(f"Nosso Número: {boleto['nossoNumero']}")
   print(f"Linha Digitável: {boleto['linhaDigitavel']}")

Consultar Boleto
~~~~~~~~~~~~~~~

.. code-block:: python

   boleto = cliente.boleto.consultar_boleto(
       convenio="123456",
       nosso_numero="12345678901"
   )

   print(f"Situação: {boleto['situacao']}")
   print(f"Valor: {boleto['valor']}")

Conta Corrente
--------------

Consultar Saldo
~~~~~~~~~~~~~~

.. code-block:: python

   saldo = cliente.conta_corrente.consultar_saldo(
       agencia="1234",
       conta="567890"
   )

   print(f"Saldo Atual: R$ {saldo['saldoAtual']}")
   print(f"Saldo Bloqueado: R$ {saldo['saldoBloqueado']}")

Extrato
~~~~~~~

.. code-block:: python

   from datetime import datetime, timedelta

   data_inicio = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
   data_fim = datetime.now().strftime("%Y-%m-%d")

   extrato = cliente.conta_corrente.consultar_extrato(
       agencia="1234",
       conta="567890",
       data_inicio=data_inicio,
       data_fim=data_fim
   )

   for lancamento in extrato['lancamentos']:
       print(f"Data: {lancamento['data']}, Valor: {lancamento['valor']}")

Transferência
~~~~~~~~~~~~

.. code-block:: python

   transferencia = cliente.conta_corrente.realizar_transferencia({
       "contaOrigem": {
           "agencia": "1234",
           "conta": "567890"
       },
       "contaDestino": {
           "agencia": "5678",
           "conta": "901234",
           "banco": "756"
       },
       "valor": "100.00",
       "descricao": "Transferência de teste"
   })

   print(f"Status: {transferencia['status']}")

Tratamento de Erros
------------------

.. code-block:: python

   from sicoob import Sicoob
   from sicoob.exceptions import (
       SicoobError,
       PixError,
       BoletoError,
       ContaCorrenteError,
       ValidationError
   )

   cliente = Sicoob(
       client_id="seu_client_id",
       certificate_path="/path/to/certificate.pem",
       private_key_path="/path/to/private_key.key",
       sandbox_mode=True
   )

   try:
       cobranca = cliente.pix.criar_cobranca_imediata(
           txid="txid_invalido",  # TXID muito curto
           dados={"valor": {"original": "100.00"}}  # Dados incompletos
       )
   except ValidationError as e:
       print(f"Erro de validação: {e}")
       print(f"Campo: {e.field}, Valor: {e.value}")
   except PixError as e:
       print(f"Erro PIX: {e}")
   except SicoobError as e:
       print(f"Erro geral Sicoob: {e}")

Logging
-------

Configuração Básica
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import logging
   from sicoob.logging_config import SicoobLogger

   # Configurar logging
   SicoobLogger.configure(
       level="DEBUG",
       format_type="custom",
       log_requests=True,
       log_responses=True
   )

   # Usar logger
   logger = SicoobLogger.get_logger(__name__)
   logger.info("Iniciando aplicação")

Configuração via Ambiente
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   export SICOOB_LOG_LEVEL="DEBUG"
   export SICOOB_LOG_FORMAT="json"
   export SICOOB_LOG_FILE="logs/sicoob.log"
   export SICOOB_LOG_REQUESTS="true"
   export SICOOB_LOG_RESPONSES="true"

.. code-block:: python

   # Configuração é carregada automaticamente
   from sicoob import Sicoob

   cliente = Sicoob()  # Logs configurados automaticamente

Configuração Avançada
--------------------

Cliente Personalizado
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sicoob import Sicoob
   from sicoob.logging_config import SicoobLogger

   # Configurar logging detalhado
   SicoobLogger.configure(
       level="DEBUG",
       format_type="json",
       log_file="logs/sicoob-debug.log",
       log_requests=True,
       log_responses=True
   )

   # Cliente com configurações específicas
   cliente = Sicoob(
       client_id="seu_client_id",
       certificate_path="/path/to/certificate.pem",
       private_key_path="/path/to/private_key.key",
       sandbox_mode=True
   )

   # Operações serão logadas detalhadamente
   cobranca = cliente.pix.criar_cobranca_imediata(
       txid="abcd1234567890123456789012345",
       dados={
           "calendario": {"expiracao": 3600},
           "valor": {"original": "100.00"},
           "chave": "usuario@exemplo.com"
       }
   )
