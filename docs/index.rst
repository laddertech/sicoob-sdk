Sicoob SDK Documentation
========================

O **Sicoob SDK** é uma biblioteca Python que fornece acesso simplificado às APIs do Banco Sicoob, incluindo funcionalidades de PIX, boletos bancários e conta corrente.

.. toctree::
   :maxdepth: 2
   :caption: Conteúdo:

   getting_started
   api_reference
   examples
   changelog

Início Rápido
=============

Instalação
----------

.. code-block:: bash

   pip install sicoob-sdk

Configuração Básica
------------------

.. code-block:: python

   from sicoob import Sicoob

   # Inicializar cliente
   cliente = Sicoob(
       client_id="seu_client_id",
       certificate_path="/path/to/certificate.pem",
       private_key_path="/path/to/private_key.key",
       sandbox_mode=True
   )

   # Ou com certificado PFX
   cliente = Sicoob(
       client_id="seu_client_id",
       pfx_path="/path/to/certificate.pfx",
       pfx_password="senha_do_certificado",
       sandbox_mode=True
   )

Funcionalidades Principais
==========================

PIX
---

.. code-block:: python

   # Criar cobrança PIX
   cobranca = cliente.pix.criar_cobranca_imediata(
       txid="abcd1234567890123456789012345",
       dados={
           "calendario": {"expiracao": 3600},
           "valor": {"original": "100.50"},
           "chave": "usuario@exemplo.com"
       }
   )

Boletos
-------

.. code-block:: python

   # Emitir boleto
   boleto = cliente.boleto.emitir_boleto({
       "numeroConvenio": "123456",
       "valor": "100.50",
       "dataVencimento": "2024-12-31"
   })

Conta Corrente
--------------

.. code-block:: python

   # Consultar saldo
   saldo = cliente.conta_corrente.consultar_saldo(
       agencia="1234",
       conta="567890"
   )

Referência da API
=================

Para referência completa da API, consulte :doc:`api_reference`.

Índices
=======

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
