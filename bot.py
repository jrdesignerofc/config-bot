"""
Jr Store Bot
Bot Discord completo para entrega de configs CS2 HvH e pagamentos PIX.

Variáveis de ambiente necessárias (Railway):
  DISCORD_TOKEN            — Token do bot Discord
  CONFIG_CHANNEL_ID        — ID do canal de configs free
  MERCADOPAGO_ACCESS_TOKEN — Access Token do Mercado Pago
  WEBHOOK_URL              — URL pública do webhook (ex: https://seu-app.railway.app/webhook/mp)
  GUILD_ID                 — (opcional) ID do servidor para sincronizar slash commands mais rápido
  PAID_ROLE_ID             — (opcional) Role entregue após pagamento confirmado
  PRODUCT_PRICE            — (opcional) Preço do produto em BRL (padrão: 29.90)
  LOG_CHANNEL_ID           — (opcional) Canal de logs de atividade
  VERIFY_ROLE_ID           — (opcional) Role entregue após verificação
  STAFF_ROLE_ID            — (opcional) Role da equipe (para tickets)
  TICKET_CATEGORY_ID       — (opcional) Categoria onde os canais de ticket serão criados
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import aiohttp
import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands, tasks

from data import (
    COLOR_DARK, COLOR_ERROR, COLOR_MAIN, COLOR_SUCCESS, COLOR_WARN,
    CONFIGS, HACKS, PRODUCTS, RISK_COLOR, get_config,
)
from payments import create_pix_payment, format_brl, get_payment, qr_code_to_file

# ─── LOGGING ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("jr_store")

# ─── ENV ─────────────────────────────────────────────────────────────────────
TOKEN             = os.getenv("DISCORD_TOKEN", "")
CONFIG_CHANNEL_ID = int(os.getenv("CONFIG_CHANNEL_ID", "0"))
GUILD_ID          = int(os.getenv("GUILD_ID", "0")) or None
PAID_ROLE_ID      = int(os.getenv("PAID_ROLE_ID", "0")) or None
LOG_CHANNEL_ID    = int(os.getenv("LOG_CHANNEL_ID", "0")) or None
VERIFY_ROLE_ID    = int(os.getenv("VERIFY_ROLE_ID", "0")) or None
STAFF_ROLE_ID     = int(os.getenv("STAFF_ROLE_ID", "0")) or None
TICKET_CATEGORY_ID= int(os.getenv("TICKET_CATEGORY_ID", "0")) or None
PRODUCT_PRICE     = float(os.getenv("PRODUCT_PRICE", "29.90"))
PORT              = int(os.getenv("PORT", "8080"))

# pending_payments[payment_id] = {"user_id": int, "product_id": str, "guild_id": int}
pending_payments: dict[str, dict] = {}

# ─── BOT SETUP ───────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
tree = bot.tree


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def risk_indicator(risk: str, lang: str) -> str:
    icons = {"low": "🟢", "medium": "🟡", "high": "🔴"}
    return icons.get(risk, "⚪")


async def send_log(guild: discord.Guild, message: str) -> None:
    if not LOG_CHANNEL_ID:
        return
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(message)


# ─── EMBED BUILDERS ──────────────────────────────────────────────────────────

def embed_main_panel(lang: str = "pt") -> discord.Embed:
    if lang == "pt":
        title = "Jr Store — Configs Free"
        desc  = (
            "Pegue sua config grátis abaixo.\n"
            "Selecione o hack e em seguida escolha a config desejada.\n\n"
            "Todas as configs são para **Memesense CS2**.\n"
            "Para suporte, use `/ticket`."
        )
        footer = "Jr Store  •  CS2 HvH  •  Configs grátis"
    else:
        title = "Jr Store — Free Configs"
        desc  = (
            "Get your free config below.\n"
            "Select the hack and then choose the desired config.\n\n"
            "All configs are for **Memesense CS2**.\n"
            "For support, use `/ticket`."
        )
        footer = "Jr Store  •  CS2 HvH  •  Free Configs"

    embed = discord.Embed(title=title, description=desc, color=COLOR_MAIN)

    available = "\n".join(
        f"**{HACKS[hk]['name']}** — {len(CONFIGS[hk])} configs"
        for hk in HACKS
    )
    field_title = "Disponível" if lang == "pt" else "Available"
    embed.add_field(name=field_title, value=available, inline=False)
    embed.set_footer(text=footer)
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def embed_config_select(hack_id: str, lang: str) -> discord.Embed:
    hack = HACKS[hack_id]
    title = f"Jr Store — {hack['name']}"
    desc = (
        "Escolha qual config deseja receber no privado:"
        if lang == "pt"
        else "Choose which config you want to receive in DMs:"
    )
    embed = discord.Embed(title=title, description=desc, color=COLOR_MAIN)

    for cfg in CONFIGS[hack_id]:
        ri = risk_indicator(cfg["risk"], lang)
        label = cfg["risk_label"][lang]
        embed.add_field(
            name=f"{cfg['name'][lang]}",
            value=f"{ri} {label}\n{cfg['short_desc'][lang]}",
            inline=True,
        )
    embed.set_footer(text="Jr Store  •  CS2 HvH")
    return embed


def embed_config_dm(hack_id: str, cfg: dict, lang: str) -> discord.Embed:
    hack    = HACKS[hack_id]
    ri      = risk_indicator(cfg["risk"], lang)
    rl      = cfg["risk_label"][lang]
    color   = RISK_COLOR[cfg["risk"]]

    if lang == "pt":
        title_prefix    = "Config"
        field_code      = "Shared Code"
        field_import    = "Como Importar"
        field_keybinds  = "Keybinds"
        field_notes     = "Notas"
        field_update    = "Atualizações"
        footer_text     = "Jr Store  •  CS2 HvH  •  Use com responsabilidade"
    else:
        title_prefix    = "Config"
        field_code      = "Shared Code"
        field_import    = "How to Import"
        field_keybinds  = "Keybinds"
        field_notes     = "Notes"
        field_update    = "Updates"
        footer_text     = "Jr Store  •  CS2 HvH  •  Use responsibly"

    embed = discord.Embed(
        title=f"{title_prefix}: {cfg['name'][lang]}  —  {hack['name']}",
        description=cfg["description"][lang],
        color=color,
    )

    # Risco
    embed.add_field(name="Risk" if lang == "en" else "Risco", value=f"{ri} {rl}", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    # Shared Code
    embed.add_field(
        name=field_code,
        value=f"```\n{cfg['shared_code']}\n```",
        inline=False,
    )

    # Como importar
    embed.add_field(name=field_import, value=hack["how_to_import"][lang], inline=False)

    # Keybinds
    kb_lines = "\n".join(
        f"`{b['key']:8}` — {b['action'][lang]}"
        for b in cfg["keybinds"]
    )
    embed.add_field(name=field_keybinds, value=kb_lines, inline=False)

    # Notas
    if cfg.get("notes", {}).get(lang):
        embed.add_field(name=field_notes, value=cfg["notes"][lang], inline=False)

    # Update note
    embed.add_field(name=field_update, value=hack["update_note"][lang], inline=False)

    embed.set_footer(text=footer_text)
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def embed_payment_pix(product: dict, payment_data: dict, lang: str) -> discord.Embed:
    txn   = payment_data["point_of_interaction"]["transaction_data"]
    pid   = payment_data["id"]
    price = format_brl(product["price"])

    if lang == "pt":
        title   = "Jr Store — Pagamento PIX"
        desc    = f"Produto: **{product['name']['pt']}**\nValor: **{price}**"
        f_code  = "Código PIX (Copia e Cola)"
        f_after = "Após o pagamento"
        after   = "A entrega é automática. Assim que o pagamento for confirmado, você receberá o produto aqui no privado."
        f_exp   = "Expira em"
        footer  = f"Jr Store  •  ID do pagamento: #{pid}"
    else:
        title   = "Jr Store — PIX Payment"
        desc    = f"Product: **{product['name']['en']}**\nAmount: **{price}**"
        f_code  = "PIX Code (Copy & Paste)"
        f_after = "After payment"
        after   = "Delivery is automatic. Once payment is confirmed, you will receive the product here in your DMs."
        f_exp   = "Expires in"
        footer  = f"Jr Store  •  Payment ID: #{pid}"

    embed = discord.Embed(title=title, description=desc, color=COLOR_MAIN)
    embed.add_field(
        name=f_code,
        value=f"```\n{txn['qr_code'][:200]}...\n```",
        inline=False,
    )
    embed.add_field(name=f_exp, value="30 minutos / 30 minutes", inline=True)
    embed.add_field(name=f_after, value=after, inline=False)
    embed.set_image(url="attachment://pix_qrcode.png")
    embed.set_footer(text=footer)
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def embed_payment_confirmed(product: dict, lang: str) -> discord.Embed:
    if lang == "pt":
        title = "Pagamento Confirmado"
        desc  = f"Seu pagamento foi aprovado! Obrigado por comprar na **Jr Store**.\n\nProduto: **{product['name']['pt']}**"
        footer = "Jr Store  •  Obrigado pela confiança"
    else:
        title = "Payment Confirmed"
        desc  = f"Your payment has been approved! Thank you for shopping at **Jr Store**.\n\nProduct: **{product['name']['en']}**"
        footer = "Jr Store  •  Thank you for your trust"

    embed = discord.Embed(title=title, description=desc, color=COLOR_SUCCESS)
    embed.set_footer(text=footer)
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def embed_verify(lang: str) -> discord.Embed:
    if lang == "pt":
        title = "Verificação — Jr Store"
        desc  = "Clique no botão abaixo para verificar sua conta e ter acesso ao servidor."
        footer = "Jr Store  •  Anti-bot"
    else:
        title = "Verification — Jr Store"
        desc  = "Click the button below to verify your account and access the server."
        footer = "Jr Store  •  Anti-bot"
    embed = discord.Embed(title=title, description=desc, color=COLOR_MAIN)
    embed.set_footer(text=footer)
    return embed


def embed_ticket_panel(lang: str) -> discord.Embed:
    if lang == "pt":
        title = "Suporte — Jr Store"
        desc  = "Precisa de ajuda? Clique no botão abaixo para abrir um ticket privado com a equipe."
        footer = "Jr Store  •  Suporte"
    else:
        title = "Support — Jr Store"
        desc  = "Need help? Click the button below to open a private ticket with the team."
        footer = "Jr Store  •  Support"
    embed = discord.Embed(title=title, description=desc, color=COLOR_MAIN)
    embed.set_footer(text=footer)
    return embed


# ─── VIEWS ───────────────────────────────────────────────────────────────────

class HackSelect(discord.ui.Select):
    """Select persistente para escolha do hack."""

    def __init__(self, lang: str = "pt"):
        options = [
            discord.SelectOption(
                label=HACKS[hk]["name"],
                value=hk,
                description=HACKS[hk]["short_desc"][lang],
            )
            for hk in HACKS
        ]
        placeholder = "Escolha o hack..." if lang == "pt" else "Choose your hack..."
        super().__init__(
            placeholder=placeholder,
            options=options,
            custom_id="jr_hack_select",
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        hack_id = self.values[0]
        embed = embed_config_select(hack_id, "pt")
        view  = ConfigSelectView(hack_id, "pt")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class HackSelectView(discord.ui.View):
    """View persistente do painel principal de configs."""

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HackSelect())


# ── Config Select (ephemeral) ────────────────────────────────────────────────

class ConfigSelect(discord.ui.Select):
    def __init__(self, hack_id: str, lang: str):
        self.hack_id = hack_id
        self.lang    = lang
        options = [
            discord.SelectOption(
                label=cfg["name"][lang],
                value=cfg["id"],
                description=cfg["short_desc"][lang],
            )
            for cfg in CONFIGS[hack_id]
        ]
        placeholder = "Escolha a config..." if lang == "pt" else "Choose the config..."
        super().__init__(placeholder=placeholder, options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        cfg = get_config(self.hack_id, self.values[0])
        if not cfg:
            await interaction.response.send_message("Config não encontrada.", ephemeral=True)
            return

        embed = embed_config_dm(self.hack_id, cfg, self.lang)
        view  = ConfigDMView(self.hack_id, cfg["id"], self.lang)

        try:
            await interaction.user.send(embed=embed, view=view)
            ok_msg = (
                "Config enviada no seu privado!"
                if self.lang == "pt"
                else "Config sent to your DMs!"
            )
            success = discord.Embed(description=f"✓  {ok_msg}", color=COLOR_SUCCESS)
            await interaction.response.send_message(embed=success, ephemeral=True)

            # Log
            if interaction.guild:
                await send_log(
                    interaction.guild,
                    f"`CONFIG` {interaction.user.mention} (`{interaction.user}`) "
                    f"pegou **{cfg['name']['pt']}** ({HACKS[self.hack_id]['name']})",
                )
        except discord.Forbidden:
            err_msg = (
                "Não consigo te enviar DM. Habilite mensagens privadas do servidor."
                if self.lang == "pt"
                else "Cannot send you a DM. Enable server direct messages."
            )
            err = discord.Embed(description=f"✗  {err_msg}", color=COLOR_ERROR)
            await interaction.response.send_message(embed=err, ephemeral=True)


class LangToggleButton(discord.ui.Button):
    """Alterna idioma no painel ephemeral de seleção de config."""

    def __init__(self, hack_id: str, current_lang: str):
        label = "🌐  English" if current_lang == "pt" else "🌐  Português"
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label,
            row=1,
        )
        self.hack_id      = hack_id
        self.current_lang = current_lang

    async def callback(self, interaction: discord.Interaction) -> None:
        new_lang = "en" if self.current_lang == "pt" else "pt"
        embed = embed_config_select(self.hack_id, new_lang)
        view  = ConfigSelectView(self.hack_id, new_lang)
        await interaction.response.edit_message(embed=embed, view=view)


class ConfigSelectView(discord.ui.View):
    def __init__(self, hack_id: str, lang: str):
        super().__init__(timeout=300)
        self.add_item(ConfigSelect(hack_id, lang))
        self.add_item(LangToggleButton(hack_id, lang))


# ── Config DM View (persistent) ──────────────────────────────────────────────

class DMLangToggle(discord.ui.Button):
    """Botão persistente para alternar idioma na DM de config."""

    def __init__(self, hack_id: str, cfg_id: str, current_lang: str):
        target_lang = "en" if current_lang == "pt" else "pt"
        label       = "🌐  English" if current_lang == "pt" else "🌐  Português"
        custom_id   = f"dm_lang_{hack_id}_{cfg_id}_{target_lang}"
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label,
            custom_id=custom_id,
        )
        self.hack_id     = hack_id
        self.cfg_id      = cfg_id
        self.target_lang = target_lang

    async def callback(self, interaction: discord.Interaction) -> None:
        cfg = get_config(self.hack_id, self.cfg_id)
        if not cfg:
            await interaction.response.defer()
            return
        embed = embed_config_dm(self.hack_id, cfg, self.target_lang)
        view  = ConfigDMView(self.hack_id, self.cfg_id, self.target_lang)
        await interaction.response.edit_message(embed=embed, view=view)


class ConfigDMView(discord.ui.View):
    def __init__(self, hack_id: str, cfg_id: str, lang: str):
        super().__init__(timeout=None)
        self.add_item(DMLangToggle(hack_id, cfg_id, lang))


# ── Verify View (persistent) ─────────────────────────────────────────────────

class VerifyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Verificar  /  Verify",
            custom_id="jr_verify",
            emoji="✓",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Erro interno.", ephemeral=True)
            return

        if not VERIFY_ROLE_ID:
            await interaction.response.send_message(
                "Verificação concluída! (VERIFY_ROLE_ID não configurado)", ephemeral=True
            )
            return

        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if not role:
            await interaction.response.send_message("Role de verificação não encontrado.", ephemeral=True)
            return

        if role in member.roles:
            await interaction.response.send_message(
                "Você já está verificado!" if True else "You are already verified!", ephemeral=True
            )
            return

        try:
            await member.add_roles(role, reason="Verificação pelo bot Jr Store")
            await interaction.response.send_message(
                "Verificado com sucesso! Bem-vindo à Jr Store.", ephemeral=True
            )
            await send_log(interaction.guild, f"`VERIFY` {member.mention} (`{member}`) verificou-se.")
        except discord.Forbidden:
            await interaction.response.send_message("Sem permissão para adicionar a role.", ephemeral=True)


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VerifyButton())


# ── Ticket View (persistent) ─────────────────────────────────────────────────

class TicketCreateButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Abrir Ticket  /  Open Ticket",
            custom_id="jr_ticket_create",
            emoji="🎫",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        guild  = interaction.guild
        member = interaction.user

        # Verifica se já tem ticket aberto
        existing = discord.utils.get(guild.text_channels, name=f"ticket-{member.id}")
        if existing:
            await interaction.response.send_message(
                f"Você já tem um ticket aberto: {existing.mention}", ephemeral=True
            )
            return

        category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member:             discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me:           discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if STAFF_ROLE_ID:
            staff_role = guild.get_role(STAFF_ROLE_ID)
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        try:
            channel = await guild.create_text_channel(
                name=f"ticket-{member.id}",
                category=category,
                overwrites=overwrites,
                topic=f"Ticket de {member} ({member.id}) | Jr Store",
            )
        except discord.Forbidden:
            await interaction.response.send_message("Sem permissão para criar canal.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Ticket Aberto — Jr Store",
            description=(
                f"Olá {member.mention}, descreva seu problema ou dúvida abaixo.\n"
                "A equipe irá te atender em breve.\n\n"
                "Para fechar o ticket, use `/fecharticket`."
            ),
            color=COLOR_MAIN,
        )
        embed.set_footer(text="Jr Store  •  Suporte")

        close_view = TicketCloseView()
        await channel.send(content=member.mention, embed=embed, view=close_view)
        await interaction.response.send_message(
            f"Ticket criado: {channel.mention}", ephemeral=True
        )
        await send_log(guild, f"`TICKET` {member.mention} (`{member}`) abriu o ticket {channel.mention}")


class TicketCloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Fechar Ticket  /  Close Ticket",
            custom_id="jr_ticket_close",
            emoji="✕",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        channel = interaction.channel
        await interaction.response.send_message("Fechando ticket em 5 segundos…", ephemeral=True)
        await send_log(
            interaction.guild,
            f"`TICKET FECHADO` {channel.mention} fechado por {interaction.user.mention}",
        )
        await asyncio.sleep(5)
        await channel.delete(reason=f"Ticket fechado por {interaction.user}")


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCloseButton())


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCreateButton())


# ── Payment Product Select (ephemeral) ───────────────────────────────────────

class ProductSelect(discord.ui.Select):
    def __init__(self, lang: str = "pt"):
        self.lang = lang
        options = [
            discord.SelectOption(
                label=p["name"][lang],
                value=p["id"],
                description=f"{format_brl(p['price'])}",
                emoji=p.get("emoji"),
            )
            for p in PRODUCTS
        ]
        placeholder = "Escolha o produto..." if lang == "pt" else "Choose the product..."
        super().__init__(placeholder=placeholder, options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        product_id = self.values[0]
        product    = next((p for p in PRODUCTS if p["id"] == product_id), None)
        if not product:
            await interaction.response.send_message("Produto não encontrado.", ephemeral=True)
            return

        product["price"] = PRODUCT_PRICE  # usa env var

        # Pede e-mail antes de criar pagamento
        modal = EmailModal(product, self.lang)
        await interaction.response.send_modal(modal)


class PaymentLangToggle(discord.ui.Button):
    def __init__(self, current_lang: str):
        label = "🌐  English" if current_lang == "pt" else "🌐  Português"
        super().__init__(style=discord.ButtonStyle.secondary, label=label, row=1)
        self.current_lang = current_lang

    async def callback(self, interaction: discord.Interaction) -> None:
        new_lang = "en" if self.current_lang == "pt" else "pt"
        embed, view = build_buy_embed_and_view(new_lang)
        await interaction.response.edit_message(embed=embed, view=view)


def build_buy_embed_and_view(lang: str):
    if lang == "pt":
        title = "Jr Store — Loja"
        desc  = "Escolha um produto abaixo para finalizar a compra via PIX."
    else:
        title = "Jr Store — Shop"
        desc  = "Choose a product below to complete your purchase via PIX."

    embed = discord.Embed(title=title, description=desc, color=COLOR_MAIN)
    for p in PRODUCTS:
        p["price"] = PRODUCT_PRICE
        embed.add_field(
            name=f"{p.get('emoji', '')} {p['name'][lang]}",
            value=f"{format_brl(p['price'])}\n{p['description'][lang]}",
            inline=False,
        )
    embed.set_footer(text="Jr Store  •  Pagamento seguro via PIX  •  Mercado Pago")

    view = discord.ui.View(timeout=300)
    view.add_item(ProductSelect(lang))
    view.add_item(PaymentLangToggle(lang))
    return embed, view


class EmailModal(discord.ui.Modal):
    email_input: discord.ui.TextInput = discord.ui.TextInput(
        label="E-mail (para o recibo Mercado Pago)",
        placeholder="seuemail@exemplo.com",
        required=True,
        min_length=5,
        max_length=100,
    )

    def __init__(self, product: dict, lang: str):
        title = "Finalizar Compra" if lang == "pt" else "Complete Purchase"
        super().__init__(title=title, timeout=300)
        self.product = product
        self.lang    = lang

    async def on_submit(self, interaction: discord.Interaction) -> None:
        payer_email = str(self.email_input.value).strip()
        user        = interaction.user
        product     = self.product
        lang        = self.lang

        thinking_msg = "Gerando PIX..." if lang == "pt" else "Generating PIX..."
        await interaction.response.send_message(thinking_msg, ephemeral=True)

        external_ref = f"{user.id}_{product['id']}_{int(datetime.now(timezone.utc).timestamp())}"

        try:
            data = await create_pix_payment(
                amount=product["price"],
                description=f"Jr Store — {product['name']['pt']}",
                payer_email=payer_email,
                external_reference=external_ref,
            )
        except Exception as exc:
            logger.exception("Erro ao criar pagamento PIX: %s", exc)
            err = "Erro ao gerar PIX. Tente novamente." if lang == "pt" else "Error generating PIX. Please try again."
            await interaction.followup.send(err, ephemeral=True)
            return

        pending_payments[str(data["id"])] = {
            "user_id":    user.id,
            "product_id": product["id"],
            "guild_id":   interaction.guild_id,
        }

        embed = embed_payment_pix(product, data, lang)
        txn   = data["point_of_interaction"]["transaction_data"]

        try:
            qr_file = qr_code_to_file(txn["qr_code_base64"])
            await user.send(embed=embed, file=qr_file)
        except discord.Forbidden:
            await interaction.followup.send(
                "Não consigo te enviar DM. Habilite mensagens privadas." if lang == "pt"
                else "Cannot DM you. Enable direct messages.",
                ephemeral=True,
            )
            return

        sent_msg = (
            "PIX enviado no seu privado! Você tem 30 minutos para pagar."
            if lang == "pt"
            else "PIX sent to your DMs! You have 30 minutes to pay."
        )
        await interaction.followup.send(sent_msg, ephemeral=True)

        if interaction.guild:
            await send_log(
                interaction.guild,
                f"`PAGAMENTO` {user.mention} iniciou compra de "
                f"**{product['name']['pt']}** | ID: `{data['id']}` | "
                f"Valor: {format_brl(product['price'])}",
            )


# ─── SLASH COMMANDS ──────────────────────────────────────────────────────────

@tree.command(name="setup", description="[Admin] Publica o painel de configs free no canal configurado.")
@app_commands.default_permissions(administrator=True)
async def cmd_setup(interaction: discord.Interaction) -> None:
    channel = interaction.guild.get_channel(CONFIG_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message(
            f"Canal CONFIG_CHANNEL_ID (`{CONFIG_CHANNEL_ID}`) não encontrado.", ephemeral=True
        )
        return

    embed = embed_main_panel("pt")
    view  = HackSelectView()
    await channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"Painel publicado em {channel.mention}.", ephemeral=True)


@tree.command(name="setupverify", description="[Admin] Publica o painel de verificação.")
@app_commands.default_permissions(administrator=True)
async def cmd_setupverify(interaction: discord.Interaction, canal: discord.TextChannel) -> None:
    embed = embed_verify("pt")
    view  = VerifyView()
    await canal.send(embed=embed, view=view)
    await interaction.response.send_message(f"Painel de verificação publicado em {canal.mention}.", ephemeral=True)


@tree.command(name="setupticket", description="[Admin] Publica o painel de suporte/tickets.")
@app_commands.default_permissions(administrator=True)
async def cmd_setupticket(interaction: discord.Interaction, canal: discord.TextChannel) -> None:
    embed = embed_ticket_panel("pt")
    view  = TicketPanelView()
    await canal.send(embed=embed, view=view)
    await interaction.response.send_message(f"Painel de tickets publicado em {canal.mention}.", ephemeral=True)


@tree.command(name="setuploja", description="[Admin] Publica o painel de compras em um canal.")
@app_commands.default_permissions(administrator=True)
async def cmd_setuploja(interaction: discord.Interaction, canal: discord.TextChannel) -> None:
    embed, view = build_buy_embed_and_view("pt")
    await canal.send(embed=embed, view=view)
    await interaction.response.send_message(f"Loja publicada em {canal.mention}.", ephemeral=True)


@tree.command(name="comprar", description="Compre um produto da Jr Store via PIX.")
async def cmd_comprar(interaction: discord.Interaction) -> None:
    embed, view = build_buy_embed_and_view("pt")
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@tree.command(name="ticket", description="Abre um ticket de suporte com a equipe Jr Store.")
async def cmd_ticket(interaction: discord.Interaction) -> None:
    guild  = interaction.guild
    member = interaction.user

    existing = discord.utils.get(guild.text_channels, name=f"ticket-{member.id}")
    if existing:
        await interaction.response.send_message(
            f"Você já tem um ticket aberto: {existing.mention}", ephemeral=True
        )
        return

    category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member:             discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me:           discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    if STAFF_ROLE_ID:
        sr = guild.get_role(STAFF_ROLE_ID)
        if sr:
            overwrites[sr] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    try:
        channel = await guild.create_text_channel(
            name=f"ticket-{member.id}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket de {member} ({member.id}) | Jr Store",
        )
    except discord.Forbidden:
        await interaction.response.send_message("Sem permissão para criar canal.", ephemeral=True)
        return

    embed = discord.Embed(
        title="Ticket Aberto — Jr Store",
        description=(
            f"Olá {member.mention}, descreva seu problema ou dúvida abaixo.\n"
            "Nossa equipe irá te atender em breve.\n\n"
            "Use o botão abaixo para fechar quando resolvido."
        ),
        color=COLOR_MAIN,
    )
    embed.set_footer(text="Jr Store  •  Suporte")
    await channel.send(content=member.mention, embed=embed, view=TicketCloseView())
    await interaction.response.send_message(f"Ticket aberto: {channel.mention}", ephemeral=True)


@tree.command(name="fecharticket", description="Fecha o ticket atual.")
async def cmd_fecharticket(interaction: discord.Interaction) -> None:
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("Este comando só funciona em canais de ticket.", ephemeral=True)
        return
    await interaction.response.send_message("Fechando ticket em 5 segundos…")
    await send_log(
        interaction.guild,
        f"`TICKET FECHADO` {interaction.channel.mention} fechado por {interaction.user.mention}",
    )
    await asyncio.sleep(5)
    await interaction.channel.delete(reason=f"Ticket fechado via /fecharticket por {interaction.user}")


@tree.command(name="anunciar", description="[Admin] Envia um anúncio em um canal.")
@app_commands.default_permissions(administrator=True)
async def cmd_anunciar(
    interaction: discord.Interaction,
    canal: discord.TextChannel,
    titulo: str,
    mensagem: str,
    mencionar_everyone: bool = False,
) -> None:
    embed = discord.Embed(title=titulo, description=mensagem, color=COLOR_MAIN)
    embed.set_footer(text=f"Jr Store  •  Anúncio por {interaction.user.display_name}")
    embed.timestamp = datetime.now(timezone.utc)
    content = "@everyone" if mencionar_everyone else None
    await canal.send(content=content, embed=embed)
    await interaction.response.send_message(f"Anúncio enviado em {canal.mention}.", ephemeral=True)


@tree.command(name="stats", description="Mostra estatísticas do servidor.")
async def cmd_stats(interaction: discord.Interaction) -> None:
    guild   = interaction.guild
    total   = guild.member_count
    bots    = sum(1 for m in guild.members if m.bot)
    humans  = total - bots
    online  = sum(1 for m in guild.members if m.status != discord.Status.offline and not m.bot)
    channels = len(guild.text_channels)

    embed = discord.Embed(title=f"Estatísticas — {guild.name}", color=COLOR_MAIN)
    embed.add_field(name="Membros",  value=str(humans),   inline=True)
    embed.add_field(name="Online",   value=str(online),   inline=True)
    embed.add_field(name="Canais",   value=str(channels), inline=True)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.set_footer(text="Jr Store")
    embed.timestamp = datetime.now(timezone.utc)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="ajuda", description="Lista todos os comandos do bot.")
async def cmd_ajuda(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="Jr Store — Comandos",
        description="Lista de todos os comandos disponíveis.",
        color=COLOR_MAIN,
    )
    embed.add_field(
        name="Configs",
        value=(
            "`/ticket` — Abre suporte privado\n"
            "`/comprar` — Compra produto via PIX\n"
            "`/stats` — Estatísticas do servidor"
        ),
        inline=False,
    )
    embed.add_field(
        name="Admin",
        value=(
            "`/setup` — Publica painel de configs free\n"
            "`/setuploja` — Publica loja em um canal\n"
            "`/setupverify` — Publica verificação\n"
            "`/setupticket` — Publica painel de tickets\n"
            "`/anunciar` — Envia anúncio\n"
            "`/fecharticket` — Fecha ticket atual"
        ),
        inline=False,
    )
    embed.set_footer(text="Jr Store  •  CS2 HvH")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ─── WEBHOOK MERCADO PAGO ────────────────────────────────────────────────────

async def handle_mp_webhook(request: web.Request) -> web.Response:
    """Recebe notificações do Mercado Pago e entrega produtos automaticamente."""
    try:
        body = await request.json()
    except Exception:
        return web.Response(status=400, text="Invalid JSON")

    action = body.get("action", "")
    data   = body.get("data", {})
    pid    = str(data.get("id", ""))

    logger.info("Webhook MP recebido: action=%s id=%s", action, pid)

    if action not in ("payment.updated", "payment.created"):
        return web.Response(status=200, text="OK")

    if not pid:
        return web.Response(status=200, text="OK")

    # Consulta status real do pagamento
    try:
        payment = await get_payment(pid)
    except Exception as exc:
        logger.error("Erro ao consultar pagamento %s: %s", pid, exc)
        return web.Response(status=200, text="OK")

    if payment.get("status") != "approved":
        return web.Response(status=200, text="OK")

    # Recupera pedido pendente
    pending = pending_payments.pop(pid, None)
    if not pending:
        # Tenta via external_reference (caso bot reiniciou)
        ext_ref = payment.get("external_reference", "")
        if ext_ref:
            parts = ext_ref.split("_")
            if len(parts) >= 2:
                pending = {"user_id": int(parts[0]), "product_id": parts[1], "guild_id": None}

    if not pending:
        logger.warning("Pagamento aprovado sem pedido pendente: id=%s", pid)
        return web.Response(status=200, text="OK")

    user_id    = pending["user_id"]
    product_id = pending["product_id"]
    guild_id   = pending.get("guild_id")

    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return web.Response(status=200, text="OK")

    # Entrega ao usuário
    user = bot.get_user(user_id)
    if not user:
        try:
            user = await bot.fetch_user(user_id)
        except Exception:
            logger.error("Usuário %s não encontrado.", user_id)
            return web.Response(status=200, text="OK")

    embed = embed_payment_confirmed(product, "pt")
    try:
        await user.send(embed=embed)
    except discord.Forbidden:
        logger.warning("Não foi possível enviar DM de confirmação ao usuário %s", user_id)

    # Dá a role paga (se configurada)
    if PAID_ROLE_ID and guild_id:
        guild = bot.get_guild(guild_id)
        if guild:
            member = guild.get_member(user_id)
            if member:
                role = guild.get_role(PAID_ROLE_ID)
                if role:
                    try:
                        await member.add_roles(role, reason="Pagamento PIX aprovado — Jr Store")
                    except discord.Forbidden:
                        logger.warning("Sem permissão para dar role %s", PAID_ROLE_ID)

            await send_log(
                guild,
                f"`VENDA` {user.mention} (`{user}`) pagamento aprovado — "
                f"**{product['name']['pt']}** | {format_brl(product['price'])} | ID: `{pid}`",
            )

    logger.info("Entrega realizada: user=%s product=%s payment=%s", user_id, product_id, pid)
    return web.Response(status=200, text="OK")


# ─── EVENTOS ─────────────────────────────────────────────────────────────────

@bot.event
async def on_ready() -> None:
    # Registra views persistentes
    bot.add_view(HackSelectView())
    bot.add_view(VerifyView())
    bot.add_view(TicketPanelView())
    bot.add_view(TicketCloseView())

    for hack_id in HACKS:
        for cfg in CONFIGS[hack_id]:
            for lang in ("pt", "en"):
                bot.add_view(ConfigDMView(hack_id, cfg["id"], lang))

    # Sync slash commands
    if GUILD_ID:
        guild_obj = discord.Object(id=GUILD_ID)
        tree.copy_global_to(guild=guild_obj)
        await tree.sync(guild=guild_obj)
    else:
        await tree.sync()

    logger.info("Jr Store Bot online — %s | Servidores: %d", bot.user, len(bot.guilds))


@bot.event
async def on_member_join(member: discord.Member) -> None:
    await send_log(
        member.guild,
        f"`JOIN` {member.mention} (`{member}`) entrou no servidor.",
    )


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    await send_log(
        member.guild,
        f"`LEAVE` `{member}` saiu do servidor.",
    )


# ─── SERVIDOR WEB (webhook) ──────────────────────────────────────────────────

async def start_web_server() -> None:
    app = web.Application()
    app.router.add_post("/webhook/mp", handle_mp_webhook)
    app.router.add_get("/health", lambda r: web.Response(text="Jr Store Bot — OK"))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info("Servidor web rodando na porta %d", PORT)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    if not TOKEN:
        raise EnvironmentError("Variável DISCORD_TOKEN não definida.")
    async with bot:
        await start_web_server()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
