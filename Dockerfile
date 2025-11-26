# PortfolioZero - Dockerfile para ambiente de Data Science
# Base: Ubuntu 24.04 LTS com Python 3.11 via deadsnakes PPA
# Nota: Ubuntu 25.04 não é suportado pelo deadsnakes PPA para Python 3.11

FROM ubuntu:24.04

# Evitar prompts interativos durante instalação de pacotes
ENV DEBIAN_FRONTEND=noninteractive

# Variáveis de ambiente Python e Poetry
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_HOME="/opt/poetry" \
    PATH="/opt/poetry/bin:$PATH"

# Atualizar sistema e instalar dependências base + software-properties-common para PPAs
RUN apt-get update && apt-get install -y \
    software-properties-common \
    build-essential \
    git \
    curl \
    wget \
    ca-certificates \
    libssl-dev \
    libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Adicionar deadsnakes PPA e instalar Python 3.11
RUN add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Criar link simbólico para python3.11 como python padrão
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Instalar pip para Python 3.11
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Instalar Poetry via script oficial
RUN curl -sSL https://install.python-poetry.org | python3.11 - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos de configuração
COPY pyproject.toml README.md ./

# Copiar código fonte do projeto
COPY modules/ ./modules/
COPY tests/ ./tests/
COPY notebooks/ ./notebooks/
COPY scripts/ ./scripts/

# Instalar dependências e o pacote local
RUN poetry install

# Expor porta do Jupyter Lab
EXPOSE 8888

# Comando padrão: iniciar Jupyter Lab para ambiente exploratório
CMD ["poetry", "run", "jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
