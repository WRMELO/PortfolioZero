"""Utilitários de logging do PortfolioZero.

Este módulo fornece funções para configuração de logging
baseadas nos objetos de configuração Pydantic.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from portfoliozero.config.domain import LoggingConfig


def setup_logging(config: LoggingConfig) -> None:
    """Aplica configuração de logging com base em um objeto LoggingConfig.

    Esta função configura o logging root do Python de acordo com as
    configurações fornecidas, incluindo nível de log, formatação e
    opcionalmente saída para arquivo.

    Args:
        config: Objeto LoggingConfig com as configurações desejadas.

    Example:
        >>> from portfoliozero.config.domain import LoggingConfig
        >>> config = LoggingConfig(level="DEBUG", log_to_file=True)
        >>> setup_logging(config)
    """
    # Mapear string de nível para constante do logging
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    level = level_map.get(config.level, logging.INFO)

    # Formato padrão de log
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    # Configurar logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Limpar handlers existentes
    root_logger.handlers.clear()

    # Handler de console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Handler de arquivo (opcional)
    if config.log_to_file:
        log_dir = Path(config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "portfoliozero.log")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    root_logger.info("Logging configurado com sucesso (level=%s)", config.level)


