FROM docker.uclv.cu/python:3.10-slim

# =====================
# Basic enviroment setup
# ---------------------

RUN apt update \
  && apt install -y \
  curl \
  locales \
  nano \
  ssh \
  sudo \
  bash \
  git \
  make \
  gcc \
  build-essential \ 
  python3-dev \
  python3-pip

ARG PIPX_VERSION=1.2.0 POETRY_VERSION=1.5.1
ENV PATH=/opt/pipx/bin:/app/.venv/bin:$PATH PIPX_BIN_DIR=/opt/pipx/bin PIPX_HOME=/opt/pipx/home POETRY_VIRTUALENVS_IN_PROJECT=true

RUN python3 -m pip install --no-cache-dir --upgrade --user "pipx==$PIPX_VERSION" \
  && python3 -m pipx ensurepath \
  && python3 -m pipx completions \
  && python3 -m pipx install "poetry==$POETRY_VERSION" \
  && poetry config installer.max-workers 10

WORKDIR /home/app/

COPY kade_drive /home/app/kade_drive/
COPY pyproject.toml /home/app/
COPY README.md /home/app/
COPY poetry.lock /home/app/

RUN poetry install --no-interaction

# CMD ["poetry", "run", "server"]
