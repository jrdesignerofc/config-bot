# Config Bot — HvH Discord

Bot para entrega automática de configs free via DM.

## Setup

1. Renomeie `.env.example` para `.env` e preencha com seu token e ID do canal
2. Instale as dependências: `pip install -r requirements.txt`
3. Rode: `python bot.py`

## Adicionando configs

- **Shared code / Market:** Edite `data/configs.json`
- **Arquivos:** Coloque o `.cfg` em `configs/<hack>/` e registre no JSON

## Comandos

- `/setup_configs` — Posta a mensagem fixa no canal (apenas admin)

## Deploy no Railway

1. Suba o projeto no GitHub
2. No Railway: New Project → Deploy from GitHub Repo
3. Adicione as variáveis de ambiente (`DISCORD_TOKEN`, `CONFIG_CHANNEL_ID`)
4. Start Command: `python bot.py`
