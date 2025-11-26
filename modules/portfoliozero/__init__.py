"""PortfolioZero - Framework MuZero-based + Black-Litterman para alocação de portfólio.

Este pacote implementa um sistema de alocação de portfólio que combina:
- Aprendizado por reforço baseado na arquitetura MuZero para decisão sequencial
- Modelo Black-Litterman para otimização de pesos finais

Modules:
    core: Componentes centrais (ambiente, RL, dados, modelos, alocação)
    config: Configurações Pydantic para experimentos
    utils: Utilitários de logging, seeds, paths
"""

__version__ = "0.1.0"
__author__ = "PortfolioZero Team"

PACKAGE_NAME = "portfoliozero"

# Pontos de entrada de alto nível (placeholders para implementação futura)
__all__ = [
    "PACKAGE_NAME",
    "__version__",
]
