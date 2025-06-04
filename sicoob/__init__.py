"""Módulo principal do SDK Sicoob"""

from .client import Sicoob
from .conta_corrente import ContaCorrenteAPI

__version__ = "0.1.0"
__all__ = ["Sicoob", "ContaCorrenteAPI"]
