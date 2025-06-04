# Sicoob SDK Python

SDK Python para integração com a API do Banco Sicoob

## Instalação

```bash
pip install -r requirements.txt
# ou
pip install -e .
```

## Configuração

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```ini
SICOOB_CLIENT_ID=seu_client_id
SICOOB_CLIENT_SECRET=seu_client_secret
SICOOB_CERTIFICADO=caminho/para/certificado.pem
SICOOB_CHAVE_PRIVADA=caminho/para/chave_privada.key
```

## Uso Básico

```python
from sicoob import Sicoob

# Inicializa o cliente
cliente = Sicoob(
    client_id="seu_client_id",
    client_secret="seu_client_secret",
    certificado="caminho/para/certificado.pem",
    chave_privada="caminho/para/chave_privada.key"
)

# Exemplo: consulta de extratos
extrato = cliente.consulta_extrato(conta="12345", data_inicio="2023-01-01", data_fim="2023-01-31")
```

## API de Boletos

A classe `BoletoAPI` permite emitir e consultar boletos bancários:

```python
from sicoob.boleto import BoletoAPI

# Obtém instância do BoletoAPI
boleto_api = cliente.boleto()

# Emitir boleto
dados_boleto = {
    "numeroContrato": 123456,
    "modalidade": 1,
    "valor": 100.50,
    "beneficiario": {
        "nome": "Nome Beneficiário",
        "documento": "12345678901"
    }
}
boleto = boleto_api.emitir_boleto(dados_boleto)

# Consultar boleto
nosso_numero = boleto["nossoNumero"]
boleto_consultado = boleto_api.consultar_boleto(nosso_numero)
```

### Tratamento de Erros

A API trata os seguintes casos de erro:
- **404 Not Found**: Retorna `None` quando o boleto não existe
- **Erros HTTP (400, 500, etc)**: Levanta exceção com código e mensagem
- **Erros de conexão**: Levanta exceção com detalhes do erro

## Links Úteis

- [Documentação API Sicoob](https://developers.sicoob.com.br)
- [Portal de Desenvolvedores](https://developers.sicoob.com.br/portal)
