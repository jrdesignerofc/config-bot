# Jr Store Discord Bot

Bot em Python para Railway focado em entrega de configs free por DM.

## Variáveis de ambiente
- `DISCORD_TOKEN`
- `CONFIG_CHANNEL_ID`
- `BRAND_NAME` (opcional, padrão: `Jr Store`)

## Instalação local
```bash
pip install -r requirements.txt
python bot.py
```

## Fluxo
- O bot publica ou atualiza automaticamente um painel no canal definido em `CONFIG_CHANNEL_ID`.
- O usuário clica em **Abrir catálogo**.
- Escolhe o produto.
- Escolhe a config.
- Recebe a entrega no privado com:
  - share code
  - instruções de importação
  - binds
  - observações e notas do pack

## Estrutura
- `bot.py` — lógica do bot
- `data/configs.json` — catálogo editável

## Railway
Start command:
```bash
python bot.py
```
