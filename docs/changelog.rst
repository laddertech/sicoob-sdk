Changelog
=========

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em `Keep a Changelog`_ e este projeto segue `Semantic Versioning`_.

.. _Keep a Changelog: https://keepachangelog.com/pt-BR/1.0.0/
.. _Semantic Versioning: https://semver.org/lang/pt-BR/

[Unreleased]
------------

Added
~~~~~
* Sistema de logging configurável com filtros de dados sensíveis
* Documentação técnica completa com Sphinx
* Cobertura de testes expandida para 76.52%
* Type hints completos em toda a base de código
* Validação de entrada robusta com schemas

Changed
~~~~~~~
* Melhorada documentação de docstrings seguindo padrão Google
* Atualizada configuração do Sphinx com tema Read the Docs
* Expandidos testes de integração e unitários

Fixed
~~~~~
* Correções na validação de TXID para PIX
* Melhorado tratamento de exceções específicas do domínio

[0.1.21] - 2025-01-15
---------------------

Changed
~~~~~~~
* Atualização da dependência pypix-api para 0.7.0

[0.1.20] - 2024-12-20
---------------------

Changed
~~~~~~~
* Atualização da dependência pypix-api para 0.4.0

[0.1.19] - 2024-12-15
---------------------

Added
~~~~~
* Melhorias na documentação
* Exemplos de uso expandidos

[0.1.18] - 2024-12-10
---------------------

Fixed
~~~~~
* Correções na autenticação OAuth2
* Melhorias na validação de entrada

[0.1.17] - 2024-12-05
---------------------

Added
~~~~~
* Suporte aprimorado para certificados PFX
* Validação de dados de entrada melhorada

[0.1.16] - 2024-11-30
---------------------

Changed
~~~~~~~
* Refatoração da estrutura de exceções
* Melhorias na API de conta corrente

[0.1.15] - 2024-11-25
---------------------

Added
~~~~~
* API de conta corrente completa
* Operações de transferência

[0.1.14] - 2024-11-20
---------------------

Fixed
~~~~~
* Correções na API PIX
* Melhorias na estabilidade

[0.1.13] - 2024-11-15
---------------------

Added
~~~~~
* Integração completa com pypix-api
* Suporte a webhooks PIX

[0.1.12] - 2024-11-10
---------------------

Changed
~~~~~~~
* Arquitetura modular aprimorada
* Melhor separação de responsabilidades

[0.1.11] - 2024-11-05
---------------------

Added
~~~~~
* API de boletos bancários
* Emissão e consulta de boletos

[0.1.10] - 2024-10-30
---------------------

Fixed
~~~~~
* Correções na autenticação
* Melhorias na gestão de tokens

[0.1.9] - 2024-10-25
---------------------

Added
~~~~~
* Suporte a modo sandbox
* Configuração via variáveis de ambiente

[0.1.8] - 2024-10-20
---------------------

Changed
~~~~~~~
* Melhorias na API PIX
* Documentação expandida

[0.1.7] - 2024-10-15
---------------------

Added
~~~~~
* Cliente OAuth2 robusto
* Cache de tokens por escopo

[0.1.6] - 2024-10-10
---------------------

Fixed
~~~~~
* Correções na validação de certificados
* Melhor tratamento de erros

[0.1.5] - 2024-10-05
---------------------

Added
~~~~~
* Suporte inicial a PIX
* Cobranças imediatas e com vencimento

[0.1.4] - 2024-09-30
---------------------

Changed
~~~~~~~
* Arquitetura base refatorada
* Melhor organização modular

[0.1.3] - 2024-09-25
---------------------

Added
~~~~~
* Sistema de exceções customizadas
* Validação de entrada básica

[0.1.2] - 2024-09-20
---------------------

Fixed
~~~~~
* Correções na autenticação
* Melhorias na estabilidade

[0.1.1] - 2024-09-15
---------------------

Added
~~~~~
* Documentação inicial
* Exemplos de uso

[0.1.0] - 2024-09-10
---------------------

Added
~~~~~
* Versão inicial do SDK
* Cliente principal Sicoob
* Autenticação OAuth2 com certificados
* Estrutura base do projeto