# Jr Store Bot

Bot Discord para entrega de configs CS2 HvH e pagamentos PIX via Mercado Pago.

---

## Estrutura do projeto

```
jr-store-bot/
├── bot.py          — Bot principal (views, comandos, webhook)
├── data.py         — Dados das configs e produtos
├── payments.py     — Integração Mercado Pago PIX
├── requirements.txt
├── Procfile        — Deploy Railway
└── .env.example    — Variáveis de ambiente (copie para .env local)
```

---

## Deploy no Railway

1. Faça push desses arquivos para o seu repositório GitHub.
2. No Railway, conecte o repositório.
3. Vá em **Variables** e adicione todas as variáveis do `.env.example`.
4. O Railway detecta o `Procfile` e inicia com `python bot.py`.
5. Acesse **Settings → Networking → Generate Domain** para obter sua URL pública.
6. Cole essa URL em `WEBHOOK_URL`: `https://SEU-PROJETO.up.railway.app/webhook/mp`

---

## Configuração do Mercado Pago

1. Acesse [developers.mercadopago.com](https://developers.mercadopago.com).
2. Crie um aplicativo.
3. Copie o **Access Token de Produção** para `MERCADOPAGO_ACCESS_TOKEN`.
4. Em **Webhooks**, adicione a URL: `https://SEU-PROJETO.up.railway.app/webhook/mp`
5. Marque o evento `payment` para receber notificações.

---

## Comandos slash disponíveis

| Comando           | Quem pode usar | Descrição                                          |
|-------------------|----------------|----------------------------------------------------|
| `/setup`          | Admin          | Publica o painel de configs free no canal definido |
| `/setuploja`      | Admin          | Publica o painel de compras em um canal            |
| `/setupverify`    | Admin          | Publica o embed de verificação anti-bot            |
| `/setupticket`    | Admin          | Publica o painel de abertura de tickets            |
| `/anunciar`       | Admin          | Envia um anúncio embed em qualquer canal           |
| `/comprar`        | Todos          | Compra produto via PIX (resposta ephemeral)        |
| `/ticket`         | Todos          | Abre canal privado de suporte                      |
| `/fecharticket`   | Todos          | Fecha o ticket atual                               |
| `/stats`          | Todos          | Estatísticas do servidor                           |
| `/ajuda`          | Todos          | Lista todos os comandos                            |

---

## Fluxo — Configs Free

```
Canal #configs-free
  └── Embed fixo com Select "Escolha o hack"
        └── Usuário seleciona Memesense
              └── Mensagem ephemeral com Select de configs
                    ├── Closet / Legit / LegitRage / Semi
                    └── Bot envia DM com:
                          - Shared Code (caixa de código)
                          - Como importar (passo a passo)
                          - Keybinds completos
                          - Notas da config
                          - Botão de troca de idioma (PT / EN)
```

---

## Fluxo — Pagamento PIX

```
/comprar  ou  botão na #loja
  └── Select de produto
        └── Modal: e-mail para o recibo
              └── Bot cria pagamento PIX via Mercado Pago
                    └── Bot envia DM com:
                          - QR Code (imagem)
                          - Código copia-e-cola
                          - Prazo: 30 minutos
                    └── Mercado Pago envia webhook ao aprovar
                          └── Bot entrega produto + role automaticamente
```

---

## Permissões necessárias para o bot

- `Read Messages / View Channels`
- `Send Messages`
- `Embed Links`
- `Attach Files`
- `Manage Channels` (para criar/deletar canais de ticket)
- `Manage Roles` (para dar roles de verificação e pagamento)
- `Read Message History`

---

## Variáveis de ambiente

| Variável                    | Obrigatória | Descrição                                            |
|-----------------------------|-------------|------------------------------------------------------|
| `DISCORD_TOKEN`             | Sim         | Token do bot                                         |
| `CONFIG_CHANNEL_ID`         | Sim         | ID do canal de configs free                          |
| `MERCADOPAGO_ACCESS_TOKEN`  | Sim*        | Access Token de produção do MP                       |
| `WEBHOOK_URL`               | Sim*        | URL pública para receber notificações do MP          |
| `GUILD_ID`                  | Não         | Sincroniza slash commands mais rápido (dev)          |
| `PAID_ROLE_ID`              | Não         | Role entregue após pagamento aprovado                |
| `PRODUCT_PRICE`             | Não         | Preço em BRL (padrão: 29.90)                         |
| `LOG_CHANNEL_ID`            | Não         | Canal de logs de atividade                           |
| `VERIFY_ROLE_ID`            | Não         | Role de membro verificado                            |
| `STAFF_ROLE_ID`             | Não         | Role da equipe (acessa tickets)                      |
| `TICKET_CATEGORY_ID`        | Não         | Categoria para os canais de ticket                   |

*Obrigatório apenas para o sistema de pagamento.
