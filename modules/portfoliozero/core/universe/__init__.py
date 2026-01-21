# -*- coding: utf-8 -*-
"""
PortfolioZero — Módulo Universe

Este módulo contém funcionalidades para gerenciamento do universo de ativos:
- UNIVERSE_CANDIDATES: Pré-lista de 60-80 candidatos
- UNIVERSE_SUPERVISED: Seleção final de ~30 ativos supervisionados
"""

from .universe_supervised_selector import (
    load_supervised_selection_config,
    select_supervised_universe,
    build_universe_supervised,
    SelectionResult,
    SelectionLogEntry,
)

__all__ = [
    "load_supervised_selection_config",
    "select_supervised_universe",
    "build_universe_supervised",
    "SelectionResult",
    "SelectionLogEntry",
]



