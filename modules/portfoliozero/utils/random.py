"""Utilitários de seed e reprodutibilidade do PortfolioZero.

Este módulo fornece funções para garantir reprodutibilidade
dos experimentos através da configuração de seeds globais.
"""

from __future__ import annotations

import logging
import random

import numpy as np
import torch

logger = logging.getLogger(__name__)


def set_global_seed(seed: int) -> None:
    """Define seed global para numpy, torch e random, garantindo reprodutibilidade.

    Esta função configura as seeds de todos os geradores de números
    aleatórios utilizados no projeto para garantir que os experimentos
    sejam reprodutíveis.

    Args:
        seed: Valor inteiro da seed a ser utilizada.

    Example:
        >>> set_global_seed(42)
        # Agora todos os geradores de números aleatórios estão sincronizados
    """
    # Python random
    random.seed(seed)

    # NumPy
    np.random.seed(seed)

    # PyTorch
    torch.manual_seed(seed)

    # PyTorch CUDA (se disponível)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        # Configurações para determinismo (pode impactar performance)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    logger.info("Seeds globais configuradas: %d", seed)


