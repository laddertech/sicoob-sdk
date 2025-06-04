"""Exemplo de uso do SDK Sicoob

Este módulo demonstra como utilizar o SDK Sicoob para consultar informações bancárias.
Certifique-se de configurar as variáveis de ambiente necessárias antes de executar.
"""

from sicoob import Sicoob
import os

# Configuração do cliente
client = Sicoob(
    client_id=os.getenv("SICOOB_CLIENT_ID"),
    client_secret=os.getenv("SICOOB_CLIENT_SECRET"),
    certificado=os.getenv("SICOOB_CERT_PATH"),
    chave_privada=os.getenv("SICOOB_KEY_PATH")
)

# Exemplo: consulta de saldo
try:
    saldo = client.conta_corrente.saldo(
        numero_conta=os.getenv("SICOOB_CONTA_NUMERO")
    )
    print(f"Saldo atual: R$ {saldo['saldo']:.2f}")
except ValueError as e:
    print(f"Dados inválidos: {e}")
except ConnectionError as e:
    print(f"Erro de conexão: {e}")
except Exception as e:
    print(f"Erro inesperado: {e}")
