# PortfolioZero

## Visão Geral

O **PortfolioZero** é um framework inovador para alocação de portfólio que combina técnicas avançadas de aprendizado por reforço (baseado na arquitetura MuZero) com o modelo clássico de Black-Litterman para otimização de carteiras de investimento.

O objetivo principal é criar um sistema capaz de aprender políticas de alocação adaptativas que incorporem tanto as expectativas do mercado quanto as visões do investidor, utilizando simulação de cenários futuros (planning) e aprendizado a partir de dados históricos. O framework foi projetado para ser modular, escalável e adequado tanto para experimentação acadêmica quanto para aplicações práticas em gestão de ativos.

A combinação do MuZero com Black-Litterman permite que o sistema aprenda a planejar alocações considerando múltiplos horizontes temporais, enquanto mantém a interpretabilidade e a incorporação de priors econômicos característica do modelo Black-Litterman tradicional.

---

## Arquitetura de Alto Nível

O PortfolioZero é organizado em três módulos principais:

1. **Módulo de Dados (`portfoliozero.core`)**: Responsável pela ingestão, transformação e preparação de dados de mercado. Utiliza Polars para processamento eficiente de séries temporais financeiras e Pydantic para validação de esquemas.

2. **Módulo de Aprendizado RL**: Implementa a arquitetura MuZero adaptada para o contexto de alocação de portfólio, incluindo as redes de representação, dinâmica e previsão. Utiliza PyTorch para modelagem e Ray para treinamento distribuído.

3. **Módulo de Otimização Black-Litterman**: Integra o modelo Black-Litterman para incorporar visões do investidor e calcular alocações ótimas, servindo tanto como baseline quanto como componente híbrido do sistema de RL.

---

## Estrutura de Diretórios

```
PortfolioZero/
├── data/                       # Dados do projeto
│   ├── raw/                    # Dados brutos (não processados)
│   ├── interim/                # Dados intermediários
│   ├── processed/              # Dados prontos para uso
│   └── external/               # Dados de fontes externas
├── modules/                    # Código fonte principal
│   └── portfoliozero/          # Pacote Python principal
│       ├── core/               # Módulos centrais (dados, modelos base)
│       ├── config/             # Configurações e schemas
│       └── utils/              # Utilitários e helpers
├── tests/                      # Testes automatizados
│   ├── unit/                   # Testes unitários
│   └── integration/            # Testes de integração
├── notebooks/                  # Jupyter notebooks
│   ├── eda/                    # Análise exploratória de dados
│   └── prototipos/             # Protótipos e experimentos
├── scripts/                    # Scripts utilitários
├── pyproject.toml              # Configuração de dependências (Poetry)
├── Dockerfile                  # Configuração do container
└── README.md                   # Este arquivo
```

---

## Stack Técnica

| Tecnologia | Versão | Justificativa |
|------------|--------|---------------|
| **Python** | 3.11 | Versão estável com melhorias de performance e typing |
| **Polars** | ^1.16 | DataFrame library de alta performance para processamento de dados financeiros |
| **Pydantic** | ^2.10 | Validação de dados e schemas com suporte nativo a typing |
| **PyTorch** | ^2.5 | Framework de deep learning maduro com excelente suporte a pesquisa |
| **Ray** | ^2.40 | Computação distribuída para treinamento escalável de RL |
| **Docker** | - | Containerização para reprodutibilidade do ambiente |
| **Ubuntu** | 25.04 | Sistema operacional base do container |
| **Poetry** | latest | Gerenciamento moderno de dependências Python |

### Ferramentas de Desenvolvimento

- **pytest**: Framework de testes
- **black**: Formatação de código
- **ruff**: Linting rápido
- **mypy**: Type checking estático

---

## Como Iniciar

### 1. Build da Imagem Docker

Construa a imagem Docker que contém todo o ambiente configurado:

```bash
docker build -t portfoliozero:latest .
```

### 2. Instalação de Dependências

As dependências são gerenciadas pelo Poetry. Dentro do container ou localmente:

```bash
# Instalar Poetry (se não estiver no container)
curl -sSL https://install.python-poetry.org | python3 -

# Instalar dependências
poetry install
```

### 3. Execução do Ambiente

Para iniciar o ambiente de desenvolvimento com Jupyter Lab:

```bash
# Via Docker
docker run -p 8888:8888 -v $(pwd):/app portfoliozero:latest

# Ou localmente
poetry run jupyter lab
```

Para verificar a instalação:

```bash
poetry run python --version  # Deve retornar Python 3.11.x
```

---

## Licença

MIT License - veja o arquivo LICENSE para detalhes.


