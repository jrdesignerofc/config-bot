# Jr Store Config Bot

Base de bot Discord para entrega automatizada de configs por DM, com suporte a português e inglês.

## O que ele faz
- Publica um painel fixo no canal configurado.
- Usuário escolhe idioma, programa e config.
- Entrega por DM com embed organizado.
- Suporta arquivo anexo e shared code/texto.
- Branding pronto em nome Jr Store.
- Estrutura pensada para Railway.

## Variáveis de ambiente
Obrigatórias:
- `DISCORD_TOKEN`
- `CONFIG_CHANNEL_ID`

Opcionais:
- `GUILD_ID` (sincroniza slash commands mais rápido em um servidor específico)
- `BRAND_NAME` (padrão: `Jr Store`)
- `BRAND_COLOR` (hex sem `#`, exemplo: `2B2D31`)

## Estrutura
- `main.py`: bot principal
- `data/catalog.json`: catálogo de programas e configs
- `data/files/`: arquivos que o bot pode enviar por DM

## Como cadastrar configs
Edite `data/catalog.json`.

Cada item em `items` representa um programa. Cada item em `configs` representa uma config.

### Exemplo de asset em texto
```json
{
  "type": "text",
  "label": {"pt": "Shared code", "en": "Shared code"},
  "content": {"pt": "ABC-123", "en": "ABC-123"},
  "filename": "shared_code.txt"
}
```

### Exemplo de asset em arquivo
```json
{
  "type": "file",
  "label": {"pt": "Arquivo principal", "en": "Main file"},
  "path": "files/example_app/sample_config.cfg"
}
```

## Deploy Railway
1. Suba esses arquivos para o repositório.
2. Configure `DISCORD_TOKEN` e `CONFIG_CHANNEL_ID` na aba Variables do serviço.
3. Faça o deploy pelo GitHub ou CLI.
4. Rode o slash command `/publish_configs` para publicar o painel.
5. Sempre que alterar o JSON, use `/reload_catalog`.

## Biblioteca usada
Este projeto usa `discord.py` com slash commands, interações e sincronização do `CommandTree`.

## Próximo passo ideal
Quando você tiver o seu material final, basta substituir os dados de exemplo do `catalog.json` e colocar os arquivos reais em `data/files/`.
