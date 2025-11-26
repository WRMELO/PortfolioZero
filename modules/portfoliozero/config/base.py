"""Configurações base do PortfolioZero.

Este módulo define as classes base de configuração usando Pydantic,
permitindo validação estrita de tipos e serialização/deserialização.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from portfoliozero.config.domain import (
    BlackLittermanConfig,
    DataConfig,
    LoggingConfig,
    MuZeroConfig,
    RayConfig,
)


class BaseConfig(BaseModel):
    """Classe base para todas as configurações tipadas do PortfolioZero.

    Utiliza Pydantic para validação estrita de tipos e configuração.
    Configurada para proibir campos extras não especificados.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_default=True,
        frozen=False,
    )

    def to_dict(self) -> dict[str, Any]:
        """Converte a configuração para dicionário.

        Returns:
            Dicionário com todos os campos da configuração.
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseConfig:
        """Cria uma instância de configuração a partir de um dicionário.

        Args:
            data: Dicionário com os campos da configuração.

        Returns:
            Instância da configuração validada.
        """
        return cls.model_validate(data)


class GlobalConfig(BaseConfig):
    """Configuração global que agrega todas as configurações de um experimento.

    Esta classe é o ponto de entrada principal para configurar um experimento
    completo do PortfolioZero, agregando configurações de dados, MuZero,
    Black-Litterman, Ray e logging.

    Attributes:
        project_name: Nome lógico do projeto/experimento.
        run_id: Identificador único da execução (UUID ou timestamp).
        data: Configuração de dados de mercado.
        muzero: Hiperparâmetros do agente MuZero.
        black_litterman: Parâmetros do modelo Black-Litterman.
        ray: Configuração opcional de Ray para paralelismo.
        logging: Configuração opcional de logging.
    """

    project_name: str = "PortfolioZero"
    run_id: str = "default"
    data: DataConfig
    muzero: MuZeroConfig = MuZeroConfig()
    black_litterman: BlackLittermanConfig = BlackLittermanConfig()
    ray: RayConfig | None = None
    logging: LoggingConfig | None = None


