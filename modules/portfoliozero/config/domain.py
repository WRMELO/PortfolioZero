"""Configurações de domínio do PortfolioZero.

Este módulo define as classes de configuração específicas para cada
componente do sistema: dados, MuZero, Black-Litterman, Ray e logging.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DomainConfig(BaseModel):
    """Classe base para configurações de domínio.

    Configurada para validação estrita e proibição de campos extras.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_default=True,
    )


class DataConfig(DomainConfig):
    """Parâmetros de fonte e pré-processamento de dados de mercado.

    Attributes:
        universe: Lista de tickers que compõem o universo de investimento.
        data_frequency: Frequência da série de preços ('daily' ou 'intraday').
        lookback_window: Número de passos históricos usados como estado de entrada.
        data_paths: Mapeamento lógico->caminho físico dos datasets.
    """

    universe: list[str] = Field(
        default_factory=list,
        description="Lista de tickers que compõem o universo de investimento.",
    )
    data_frequency: Literal["daily", "intraday"] = Field(
        default="daily",
        description="Frequência da série de preços.",
    )
    lookback_window: int = Field(
        default=252,
        ge=1,
        description="Número de passos históricos usados como estado de entrada para o agente.",
    )
    data_paths: dict[str, str] = Field(
        default_factory=dict,
        description="Mapeamento lógico->caminho físico dos datasets.",
    )


class MuZeroConfig(DomainConfig):
    """Hiperparâmetros do agente MuZero aplicado a portfólio.

    Attributes:
        discount: Fator de desconto de recompensas futuras (gamma).
        num_simulations: Número de simulações MCTS por decisão.
        num_unroll_steps: Número de passos de unroll da dinâmica ao treinar.
        td_steps: Horizonte de bootstrap do target de valor.
        policy_temperature: Temperatura da política na fase de exploração.
        learning_rate: Taxa de aprendizado do otimizador.
        batch_size: Tamanho do batch de treino.
        replay_buffer_size: Tamanho máximo do replay buffer.
    """

    discount: float = Field(
        default=0.99,
        ge=0.0,
        le=1.0,
        description="Fator de desconto de recompensas futuras.",
    )
    num_simulations: int = Field(
        default=50,
        ge=1,
        description="Número de simulações MCTS por decisão.",
    )
    num_unroll_steps: int = Field(
        default=5,
        ge=1,
        description="Número de passos de unroll da dinâmica ao treinar.",
    )
    td_steps: int = Field(
        default=5,
        ge=1,
        description="Horizonte de bootstrap do target de valor.",
    )
    policy_temperature: float = Field(
        default=1.0,
        ge=0.0,
        description="Temperatura da política na fase de exploração.",
    )
    learning_rate: float = Field(
        default=3e-4,
        gt=0.0,
        description="Taxa de aprendizado do otimizador.",
    )
    batch_size: int = Field(
        default=256,
        ge=1,
        description="Tamanho do batch de treino.",
    )
    replay_buffer_size: int = Field(
        default=100_000,
        ge=1,
        description="Tamanho máximo do replay buffer.",
    )


class BlackLittermanConfig(DomainConfig):
    """Parâmetros de alocação Black-Litterman.

    Attributes:
        tau: Escala de incerteza da matriz de covariância de equilíbrio.
        risk_aversion: Coeficiente de aversão ao risco do investidor.
        view_confidence: Confiança média em views geradas pelo agente (0-1).
        max_leverage: Alavancagem máxima permitida na alocação.
    """

    tau: float = Field(
        default=0.05,
        gt=0.0,
        description="Escala de incerteza da matriz de covariância de equilíbrio.",
    )
    risk_aversion: float = Field(
        default=2.5,
        gt=0.0,
        description="Coeficiente de aversão ao risco do investidor.",
    )
    view_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confiança média em views geradas pelo agente (0-1).",
    )
    max_leverage: float = Field(
        default=1.0,
        ge=0.0,
        description="Alavancagem máxima permitida na alocação.",
    )


class RayConfig(DomainConfig):
    """Parâmetros de orquestração com Ray.

    Attributes:
        enabled: Se Ray deve ou não ser utilizado.
        num_workers: Número de workers de treino paralelo.
    """

    enabled: bool = Field(
        default=False,
        description="Se Ray deve ou não ser utilizado.",
    )
    num_workers: int = Field(
        default=1,
        ge=1,
        description="Número de workers de treino paralelo.",
    )


class LoggingConfig(DomainConfig):
    """Configuração básica de logging.

    Attributes:
        level: Nível de logging (DEBUG, INFO, WARNING, ERROR).
        log_to_file: Se logs devem ser gravados em arquivo.
        log_dir: Diretório para arquivos de log.
    """

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Nível de logging.",
    )
    log_to_file: bool = Field(
        default=True,
        description="Se logs devem ser gravados em arquivo.",
    )
    log_dir: str = Field(
        default="logs",
        description="Diretório para arquivos de log.",
    )


