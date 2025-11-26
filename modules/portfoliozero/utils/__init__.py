"""Namespace para utilitários gerais do PortfolioZero.

Este módulo exporta funções utilitárias:
- setup_logging: Configuração de logging
- set_global_seed: Configuração de seeds para reprodutibilidade
"""

from portfoliozero.utils.logging import setup_logging
from portfoliozero.utils.random import set_global_seed

__all__ = [
    "setup_logging",
    "set_global_seed",
]


