Primeiros Passos
================

Este guia irá ajudá-lo a começar com o Sicoob SDK rapidamente.

Instalação
----------

Requisitos
~~~~~~~~~~~

* Python 3.10 ou superior
* Certificado digital do Sicoob (PEM/key ou PFX)
* Client ID fornecido pelo Sicoob

Instalação via pip
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install sicoob-sdk

Instalação para Desenvolvimento
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git clone https://github.com/LadderTech/sicoob-sdk
   cd sicoob-sdk
   pip install -e ".[dev]"

Configuração
------------

Certificado PEM/Key
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sicoob import Sicoob

   cliente = Sicoob(
       client_id="seu_client_id",
       certificate_path="/path/to/certificate.pem",
       private_key_path="/path/to/private_key.key",
       sandbox_mode=True  # Para testes
   )

Certificado PFX
~~~~~~~~~~~~~~

.. code-block:: python

   from sicoob import Sicoob

   cliente = Sicoob(
       client_id="seu_client_id",
       pfx_path="/path/to/certificate.pfx",
       pfx_password="senha_do_certificado",
       sandbox_mode=True  # Para testes
   )

Variáveis de Ambiente
~~~~~~~~~~~~~~~~~~~~

Você pode configurar as credenciais via variáveis de ambiente:

.. code-block:: bash

   export SICOOB_CLIENT_ID="seu_client_id"
   export SICOOB_CERTIFICATE_PATH="/path/to/certificate.pem"
   export SICOOB_PRIVATE_KEY_PATH="/path/to/private_key.key"
   export SICOOB_SANDBOX_MODE="true"

.. code-block:: python

   from sicoob import Sicoob

   # Carrega automaticamente das variáveis de ambiente
   cliente = Sicoob()

Primeiro Uso
-----------

Teste de Conectividade
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sicoob import Sicoob

   try:
       cliente = Sicoob(
           client_id="seu_client_id",
           certificate_path="/path/to/certificate.pem",
           private_key_path="/path/to/private_key.key",
           sandbox_mode=True
       )

       # Testa autenticação
       print("✅ Cliente configurado com sucesso!")

   except Exception as e:
       print(f"❌ Erro na configuração: {e}")

Exemplo Completo PIX
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sicoob import Sicoob
   import uuid

   # Inicializar cliente
   cliente = Sicoob(
       client_id="seu_client_id",
       certificate_path="/path/to/certificate.pem",
       private_key_path="/path/to/private_key.key",
       sandbox_mode=True
   )

   # Gerar TXID único
   txid = str(uuid.uuid4()).replace('-', '')[:35]

   try:
       # Criar cobrança PIX
       cobranca = cliente.pix.criar_cobranca_imediata(
           txid=txid,
           dados={
               "calendario": {"expiracao": 3600},  # 1 hora
               "valor": {"original": "100.50"},
               "chave": "usuario@exemplo.com",
               "solicitacaoPagador": "Pagamento do pedido #123"
           }
       )

       print(f"QR Code: {cobranca['qrcode']}")
       print(f"PIX Copia e Cola: {cobranca['pixCopiaECola']}")

   except Exception as e:
       print(f"Erro: {e}")

Próximos Passos
--------------

* Consulte a :doc:`api_reference` para referência completa da API
* Veja mais :doc:`examples` de uso
* Configure logging adequado para produção

Suporte
-------

* GitHub Issues: https://github.com/LadderTech/sicoob-sdk/issues
* Documentação oficial do Sicoob: https://developers.sicoob.com.br/
