"""
Jr Store Bot — v3
Variáveis de ambiente:
  DISCORD_TOKEN            — Token do bot
  CONFIG_CHANNEL_ID        — Canal de configs free
  MERCADOPAGO_ACCESS_TOKEN — Mercado Pago token
  WEBHOOK_URL              — URL pública do webhook (opcional)
  GUILD_ID                 — ID do servidor (opcional, sync mais rápido)
  PAID_ROLE_ID             — Role após pagamento (opcional)
  LOG_CHANNEL_ID           — Canal de logs (opcional)
  VERIFY_ROLE_ID           — Role de verificação (opcional)
  STAFF_ROLE_ID            — Role da equipe (opcional)
  TICKET_CATEGORY_ID       — Categoria dos tickets (opcional)
  CART_CATEGORY_ID         — Categoria dos carrinhos (opcional)
  TRANSCRIPT_CHANNEL_ID    — Canal de transcrições de ticket (opcional)
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone

import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands

from data import (
    COLOR_ERROR, COLOR_MAIN, COLOR_SUCCESS, COLOR_WARN,
    CONFIGS, HACKS, RISK_COLOR, get_config, get_products, save_products,
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
TOKEN                 = os.getenv("DISCORD_TOKEN", "")
CONFIG_CHANNEL_ID     = int(os.getenv("CONFIG_CHANNEL_ID", "0"))
GUILD_ID              = int(os.getenv("GUILD_ID", "0")) or None
PAID_ROLE_ID          = int(os.getenv("PAID_ROLE_ID", "0")) or None
LOG_CHANNEL_ID        = int(os.getenv("LOG_CHANNEL_ID", "0")) or None
VERIFY_ROLE_ID        = int(os.getenv("VERIFY_ROLE_ID", "0")) or None
STAFF_ROLE_ID         = int(os.getenv("STAFF_ROLE_ID", "0")) or None
TICKET_CATEGORY_ID    = int(os.getenv("TICKET_CATEGORY_ID", "0")) or None
CART_CATEGORY_ID      = int(os.getenv("CART_CATEGORY_ID", "0")) or None
TRANSCRIPT_CHANNEL_ID = int(os.getenv("TRANSCRIPT_CHANNEL_ID", "0")) or None
PORT                  = int(os.getenv("PORT", "8080"))

pending_payments: dict[str, dict] = {}

# ─── BOT ─────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
tree = bot.tree


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def risk_indicator(risk: str) -> str:
    return {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "⚪")


async def send_log(guild: discord.Guild, message: str) -> None:
    if not LOG_CHANNEL_ID:
        return
    ch = guild.get_channel(LOG_CHANNEL_ID)
    if ch:
        await ch.send(message)


def is_admin(member: discord.Member) -> bool:
    return member.guild_permissions.administrator


# ─── EMBEDS ──────────────────────────────────────────────────────────────────

def embed_main_panel(lang: str = "pt") -> discord.Embed:
    if lang == "pt":
        title  = "Jr Store — Configs Free"
        desc   = (
            "Pegue sua config grátis abaixo.\n"
            "Selecione o hack e em seguida escolha a config desejada.\n\n"
            "Todas as configs são para **Memesense CS2**.\n"
            "Para suporte, abra um ticket."
        )
        footer = "Jr Store  •  Configs grátis"
    else:
        title  = "Jr Store — Free Configs"
        desc   = (
            "Get your free config below.\n"
            "Select the hack and then choose the desired config.\n\n"
            "All configs are for **Memesense CS2**.\n"
            "For support, open a ticket."
        )
        footer = "Jr Store  •  Free Configs"

    embed = discord.Embed(title=title, description=desc, color=COLOR_MAIN)
    available = "\n".join(
        f"**{HACKS[hk]['name']}** — {len(CONFIGS[hk])} configs"
        for hk in HACKS
    )
    embed.add_field(name="Disponível" if lang == "pt" else "Available", value=available, inline=False)
    embed.set_footer(text=footer)
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def embed_config_select(hack_id: str, lang: str) -> discord.Embed:
    hack  = HACKS[hack_id]
    embed = discord.Embed(
        title=f"Jr Store — {hack['name']}",
        description=(
            "Escolha qual config deseja receber no privado:"
            if lang == "pt"
            else "Choose which config you want to receive in DMs:"
        ),
        color=COLOR_MAIN,
    )
    for cfg in CONFIGS[hack_id]:
        ri = risk_indicator(cfg["risk"])
        embed.add_field(
            name=cfg["name"][lang],
            value=f"{ri} {cfg['risk_label'][lang]}\n{cfg['short_desc'][lang]}",
            inline=True,
        )
    embed.set_footer(text="Jr Store  •  Suporte")
    return embed


def embed_config_dm(hack_id: str, cfg: dict, lang: str) -> discord.Embed:
    hack  = HACKS[hack_id]
    ri    = risk_indicator(cfg["risk"])
    rl    = cfg["risk_label"][lang]
    color = RISK_COLOR[cfg["risk"]]
    embed = discord.Embed(
        title=f"Config: {cfg['name'][lang]}  —  {hack['name']}",
        description=cfg["description"][lang],
        color=color,
    )
    embed.add_field(name="Risco" if lang == "pt" else "Risk", value=f"{ri} {rl}", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="Shared Code", value=f"```\n{cfg['shared_code']}\n```", inline=False)
    embed.add_field(
        name="Como Importar" if lang == "pt" else "How to Import",
        value=hack["how_to_import"][lang],
        inline=False,
    )
    kb = "\n".join(f"`{b['key']:8}` — {b['action'][lang]}" for b in cfg["keybinds"])
    embed.add_field(name="Keybinds", value=kb, inline=False)
    if cfg.get("notes", {}).get(lang):
        embed.add_field(name="Notas" if lang == "pt" else "Notes", value=cfg["notes"][lang], inline=False)
    embed.add_field(
        name="Atualizações" if lang == "pt" else "Updates",
        value=hack["update_note"][lang],
        inline=False,
    )
    embed.set_footer(text="Jr Store  •  Use com responsabilidade")
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def embed_store_main(lang: str = "pt") -> discord.Embed:
    """Embed inicial da loja — só mostra os produtos disponíveis, sem configs."""
    products = get_products(active_only=True)
    if lang == "pt":
        title = "🛒 Jr Store — Loja"
        desc  = (
            "Bem-vindo à **Jr Store**! 💜\n\n"
            "**Como comprar:**\n"
            "**1️⃣** Selecione o hack no menu abaixo\n"
            "**2️⃣** Escolha o pacote que deseja\n"
            "**3️⃣** Um carrinho privado será aberto para você\n"
            "**4️⃣** Finalize o pagamento e receba automaticamente\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        footer = "Jr Store  •  Pagamento seguro via PIX  •  Entrega automática"
    else:
        title = "🛒 Jr Store — Shop"
        desc  = (
            "Welcome to **Jr Store**! 💜\n\n"
            "**How to buy:**\n"
            "**1️⃣** Select the hack in the menu below\n"
            "**2️⃣** Choose the package you want\n"
            "**3️⃣** A private cart will be opened for you\n"
            "**4️⃣** Complete payment and receive automatically\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        footer = "Jr Store  •  Secure PIX payment  •  Automatic delivery"

    embed = discord.Embed(title=title, description=desc, color=COLOR_MAIN)
    for p in products:
        status = "✅ Disponível" if p.get("active", True) else "🔧 Em Manutenção"
        # Lista os pacotes com preços
        pkgs_text = "\n".join(
            f"• **{pkg['label_pt' if lang == 'pt' else 'label_en']}** — {format_brl(pkg['price'])}"
            for pkg in p.get("packages", [])
        )
        embed.add_field(
            name=f"{p.get('emoji','📦')} {p['name'][lang]}  •  {status}",
            value=f"{p['description'][lang]}\n\n{pkgs_text}",
            inline=False,
        )
    embed.set_footer(text=footer)
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def embed_hack_packages(product: dict, lang: str = "pt") -> discord.Embed:
    """Embed exibido APÓS selecionar o hack — mostra os pacotes com descrição completa."""
    img_url = product.get("image_url")
    embed = discord.Embed(
        title=f"{product.get('emoji','📦')} {product['name'][lang]}",
        description=product["description"][lang],
        color=COLOR_MAIN,
    )
    if img_url:
        embed.set_image(url=img_url)

    for pkg in product.get("packages", []):
        label = pkg["label_pt"] if lang == "pt" else pkg["label_en"]
        desc  = pkg["description_pt"] if lang == "pt" else pkg["description_en"]
        embed.add_field(
            name=f"{label}  —  {format_brl(pkg['price'])}",
            value=desc,
            inline=False,
        )
    embed.set_footer(
        text="Selecione um pacote abaixo para abrir seu carrinho 🛒"
        if lang == "pt"
        else "Select a package below to open your cart 🛒"
    )
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def embed_cart_channel(
    member: discord.Member,
    product: dict,
    pkg: dict,
    order_num: str,
    qty: int,
    coupon_discount: float,
    lang: str = "pt",
) -> discord.Embed:
    """Embed do canal de carrinho privado."""
    unit_price = pkg["price"]
    subtotal   = unit_price * qty
    total      = max(0.0, subtotal - coupon_discount)
    label      = pkg["label_pt"] if lang == "pt" else pkg["label_en"]

    embed = discord.Embed(
        title="🛒 Carrinho — Jr Store" if lang == "pt" else "🛒 Cart — Jr Store",
        color=COLOR_MAIN,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Produto" if lang == "pt" else "Product",
                    value=f"{product.get('emoji','')} {product['name'][lang]}", inline=True)
    embed.add_field(name="Pacote" if lang == "pt" else "Package", value=label, inline=True)
    embed.add_field(name="Nº Pedido" if lang == "pt" else "Order #", value=f"`{order_num}`", inline=True)
    embed.add_field(name="Quantidade" if lang == "pt" else "Qty", value=str(qty), inline=True)
    embed.add_field(name="Preço Unit." if lang == "pt" else "Unit Price", value=format_brl(unit_price), inline=True)
    if coupon_discount > 0:
        embed.add_field(name="Desconto 🏷️", value=f"- {format_brl(coupon_discount)}", inline=True)
    embed.add_field(name="**Total**", value=f"**{format_brl(total)}**", inline=False)
    embed.set_footer(
        text="Use os botões abaixo para finalizar ou ajustar seu pedido 👇"
        if lang == "pt"
        else "Use the buttons below to finalize or adjust your order 👇"
    )
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def embed_pix_payment(product: dict, pkg: dict, payment_data: dict, order_num: str, qty: int, lang: str) -> discord.Embed:
    txn   = payment_data["point_of_interaction"]["transaction_data"]
    pid   = payment_data["id"]
    label = pkg["label_pt"] if lang == "pt" else pkg["label_en"]
    total = pkg["price"] * qty

    embed = discord.Embed(
        title="💳 Pagamento PIX — Jr Store" if lang == "pt" else "💳 PIX Payment — Jr Store",
        description=(
            f"**Produto:** {product.get('emoji','')} {product['name'][lang]}\n"
            f"**Pacote:** {label}\n"
            f"**Total:** {format_brl(total)}\n"
            f"**Pedido:** `{order_num}`"
        ),
        color=COLOR_MAIN,
    )
    embed.add_field(
        name="📋 Código PIX — Copia e Cola" if lang == "pt" else "📋 PIX Code — Copy & Paste",
        value=f"```\n{txn['qr_code'][:300]}\n```",
        inline=False,
    )
    embed.add_field(
        name="⏱️ Expira em" if lang == "pt" else "⏱️ Expires in",
        value="30 minutos",
        inline=True,
    )
    embed.add_field(
        name="📦 Entrega" if lang == "pt" else "📦 Delivery",
        value="Automática após confirmação do pagamento" if lang == "pt" else "Automatic after payment confirmation",
        inline=True,
    )
    embed.set_image(url="attachment://pix_qrcode.png")
    embed.set_footer(text=f"Jr Store  •  MP ID: {pid}")
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def embed_payment_confirmed(product: dict, pkg: dict, lang: str) -> discord.Embed:
    label = pkg["label_pt"] if lang == "pt" else pkg["label_en"]
    embed = discord.Embed(
        title="✅ Pagamento Confirmado!" if lang == "pt" else "✅ Payment Confirmed!",
        description=(
            f"Obrigado por comprar na **Jr Store**! 💜\n\n"
            f"**Produto:** {product.get('emoji','')} {product['name'][lang]}\n"
            f"**Pacote:** {label}\n\n"
            "Sua(s) config(s) estão sendo enviadas abaixo. 📨"
            if lang == "pt"
            else
            f"Thank you for shopping at **Jr Store**! 💜\n\n"
            f"**Product:** {product.get('emoji','')} {product['name'][lang]}\n"
            f"**Package:** {label}\n\n"
            "Your config(s) are being sent below. 📨"
        ),
        color=COLOR_SUCCESS,
    )
    embed.set_footer(text="Jr Store  •  Obrigado pela confiança 💜" if lang == "pt" else "Jr Store  •  Thank you 💜")
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def embed_verify(lang: str) -> discord.Embed:
    title  = "✅ Verificação — Jr Store" if lang == "pt" else "✅ Verification — Jr Store"
    desc   = (
        "Clique no botão abaixo para verificar sua conta e ter acesso ao servidor."
        if lang == "pt"
        else "Click the button below to verify your account and access the server."
    )
    embed = discord.Embed(title=title, description=desc, color=COLOR_MAIN)
    embed.set_footer(text="Jr Store  •  Anti-bot")
    return embed


def embed_ticket_panel(lang: str) -> discord.Embed:
    if lang == "pt":
        desc = (
            "Precisa de ajuda? Nossa equipe está pronta para te atender.\n\n"
            "**Como funciona:**\n"
            "🔹 Clique em **Abrir Ticket** para criar um canal privado\n"
            "🔹 Descreva seu problema com detalhes\n"
            "🔹 Aguarde um membro da equipe assumir\n\n"
            "⏱️ Tempo médio de resposta: **< 24h**"
        )
    else:
        desc = (
            "Need help? Our team is ready to assist you.\n\n"
            "**How it works:**\n"
            "🔹 Click **Open Ticket** to create a private channel\n"
            "🔹 Describe your problem in detail\n"
            "🔹 Wait for a team member to take over\n\n"
            "⏱️ Average response time: **< 24h**"
        )
    embed = discord.Embed(
        title="🎫 Suporte — Jr Store" if lang == "pt" else "🎫 Support — Jr Store",
        description=desc,
        color=COLOR_MAIN,
    )
    embed.set_footer(text="Jr Store  •  Suporte")
    return embed


# ─── VIEWS — FREE CONFIGS ─────────────────────────────────────────────────────

class HackSelect(discord.ui.Select):
    def __init__(self, lang: str = "pt"):
        options = [
            discord.SelectOption(
                label=HACKS[hk]["name"],
                value=hk,
                description=HACKS[hk]["short_desc"][lang],
            )
            for hk in HACKS
        ]
        super().__init__(
            placeholder="Escolha o hack..." if lang == "pt" else "Choose your hack...",
            options=options,
            custom_id="jr_hack_select",
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        hack_id = self.values[0]
        embed   = embed_config_select(hack_id, "pt")
        view    = ConfigSelectView(hack_id, "pt")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class HackSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HackSelect())


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
        super().__init__(
            placeholder="Escolha a config..." if lang == "pt" else "Choose the config...",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        cfg = get_config(self.hack_id, self.values[0])
        if not cfg:
            await interaction.response.send_message("Config não encontrada.", ephemeral=True)
            return
        embed = embed_config_dm(self.hack_id, cfg, self.lang)
        view  = ConfigDMView(self.hack_id, cfg["id"], self.lang)
        try:
            await interaction.user.send(embed=embed, view=view)
            ok = discord.Embed(description="✅ Config enviada no seu privado! ✉️", color=COLOR_SUCCESS)
            await interaction.response.send_message(embed=ok, ephemeral=True)
            if interaction.guild:
                await send_log(
                    interaction.guild,
                    f"`CONFIG` {interaction.user.mention} pegou **{cfg['name']['pt']}** ({HACKS[self.hack_id]['name']})",
                )
        except discord.Forbidden:
            err = discord.Embed(
                description="❌ Não consigo te enviar DM. Habilite mensagens privadas do servidor.",
                color=COLOR_ERROR,
            )
            await interaction.response.send_message(embed=err, ephemeral=True)


class LangToggleButton(discord.ui.Button):
    def __init__(self, hack_id: str, current_lang: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="🌐  English" if current_lang == "pt" else "🌐  Português",
            row=1,
        )
        self.hack_id      = hack_id
        self.current_lang = current_lang

    async def callback(self, interaction: discord.Interaction) -> None:
        new_lang = "en" if self.current_lang == "pt" else "pt"
        await interaction.response.edit_message(
            embed=embed_config_select(self.hack_id, new_lang),
            view=ConfigSelectView(self.hack_id, new_lang),
        )


class ConfigSelectView(discord.ui.View):
    def __init__(self, hack_id: str, lang: str):
        super().__init__(timeout=300)
        self.add_item(ConfigSelect(hack_id, lang))
        self.add_item(LangToggleButton(hack_id, lang))


class DMLangToggle(discord.ui.Button):
    def __init__(self, hack_id: str, cfg_id: str, current_lang: str):
        target_lang = "en" if current_lang == "pt" else "pt"
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="🌐  English" if current_lang == "pt" else "🌐  Português",
            custom_id=f"dm_lang_{hack_id}_{cfg_id}_{target_lang}",
        )
        self.hack_id     = hack_id
        self.cfg_id      = cfg_id
        self.target_lang = target_lang

    async def callback(self, interaction: discord.Interaction) -> None:
        cfg = get_config(self.hack_id, self.cfg_id)
        if not cfg:
            await interaction.response.defer()
            return
        await interaction.response.edit_message(
            embed=embed_config_dm(self.hack_id, cfg, self.target_lang),
            view=ConfigDMView(self.hack_id, self.cfg_id, self.target_lang),
        )


class ConfigDMView(discord.ui.View):
    def __init__(self, hack_id: str, cfg_id: str, lang: str):
        super().__init__(timeout=None)
        self.add_item(DMLangToggle(hack_id, cfg_id, lang))


# ─── VIEWS — LOJA ────────────────────────────────────────────────────────────

class StoreHackSelect(discord.ui.Select):
    """Menu inicial da loja — seleciona o hack/produto."""

    def __init__(self, lang: str = "pt"):
        self.lang = lang
        products  = get_products(active_only=True)
        options   = [
            discord.SelectOption(
                label=p["name"][lang],
                value=p["id"],
                description=p["description"][lang][:100],
                emoji=p.get("emoji"),
            )
            for p in products
        ] or [discord.SelectOption(label="Nenhum produto disponível", value="__none__")]
        super().__init__(
            placeholder="1️⃣  Selecione o hack..." if lang == "pt" else "1️⃣  Select the hack...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="jr_store_hack_select",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        product_id = self.values[0]
        if product_id == "__none__":
            await interaction.response.send_message("Nenhum produto disponível.", ephemeral=True)
            return

        products = get_products(active_only=True)
        product  = next((p for p in products if p["id"] == product_id), None)
        if not product:
            await interaction.response.send_message("Produto não encontrado.", ephemeral=True)
            return

        embed = embed_hack_packages(product, self.lang)
        view  = PackageSelectView(product, self.lang, interaction.user, interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class StoreMainView(discord.ui.View):
    """View persistente da loja — recriada com produtos atuais a cada interação."""

    def __init__(self):
        super().__init__(timeout=None)
        # Adiciona placeholder; o select real é criado na interação
        self.add_item(_StoreLangBtn())
        self.add_item(_StoreOpenSelectBtn())


class _StoreOpenSelectBtn(discord.ui.Button):
    """Botão que abre o select de hacks com produtos atuais (sempre fresh)."""

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="🛒 Comprar",
            custom_id="jr_store_open_select",
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        products = get_products(active_only=True)
        if not products:
            await interaction.response.send_message(
                "❌ Nenhum produto disponível no momento.", ephemeral=True
            )
            return
        embed = discord.Embed(
            title="🛒 Selecione o Hack",
            description="Escolha abaixo qual hack você quer comprar configs:",
            color=COLOR_MAIN,
        )
        view = _FreshHackSelectView("pt")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class _FreshHackSelectView(discord.ui.View):
    """View ephemeral com select de hacks carregado sempre fresh do disco."""

    def __init__(self, lang: str = "pt"):
        super().__init__(timeout=300)
        self.lang = lang
        self._rebuild()

    def _rebuild(self):
        self.clear_items()
        products = get_products(active_only=True)
        options  = [
            discord.SelectOption(
                label=p["name"][self.lang],
                value=p["id"],
                description=p["description"][self.lang][:100],
                emoji=p.get("emoji"),
            )
            for p in products
        ]
        if not options:
            options = [discord.SelectOption(label="Nenhum produto disponível", value="__none__")]

        sel = discord.ui.Select(
            placeholder="Selecione o hack..." if self.lang == "pt" else "Select the hack...",
            options=options,
            min_values=1,
            max_values=1,
        )
        sel.callback = self._on_hack_select
        self.add_item(sel)

        lang_btn = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="🌐  English" if self.lang == "pt" else "🌐  Português",
            row=1,
        )
        lang_btn.callback = self._toggle_lang
        self.add_item(lang_btn)

    async def _toggle_lang(self, interaction: discord.Interaction) -> None:
        self.lang = "en" if self.lang == "pt" else "pt"
        self._rebuild()
        embed = discord.Embed(
            title="🛒 Select the Hack" if self.lang == "en" else "🛒 Selecione o Hack",
            description="Choose below which hack you want to buy configs for:" if self.lang == "en"
                        else "Escolha abaixo qual hack você quer comprar configs:",
            color=COLOR_MAIN,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def _on_hack_select(self, interaction: discord.Interaction) -> None:
        product_id = interaction.data["values"][0]
        if product_id == "__none__":
            await interaction.response.send_message("Nenhum produto disponível.", ephemeral=True)
            return
        products = get_products(active_only=True)
        product  = next((p for p in products if p["id"] == product_id), None)
        if not product:
            await interaction.response.send_message("Produto não encontrado.", ephemeral=True)
            return
        embed = embed_hack_packages(product, self.lang)
        view  = PackageSelectView(product, self.lang, interaction.user, interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


class PackageSelectView(discord.ui.View):
    """Step 2 — seleciona o pacote do hack."""

    def __init__(self, product: dict, lang: str, member: discord.Member, guild: discord.Guild):
        super().__init__(timeout=300)
        self.product = product
        self.lang    = lang
        self.member  = member
        self.guild   = guild

        packages = product.get("packages", [])
        options  = [
            discord.SelectOption(
                label=f"{pkg['label_pt' if lang == 'pt' else 'label_en']}  —  {format_brl(pkg['price'])}",
                value=pkg["id"],
                description=(pkg["description_pt"] if lang == "pt" else pkg["description_en"])[:100],
            )
            for pkg in packages
        ]

        sel = discord.ui.Select(
            placeholder="2️⃣  Escolha o pacote..." if lang == "pt" else "2️⃣  Choose the package...",
            options=options,
            min_values=1,
            max_values=1,
        )
        sel.callback = self._on_package_select
        self.add_item(sel)

    async def _on_package_select(self, interaction: discord.Interaction) -> None:
        pkg_id   = interaction.data["values"][0]
        packages = self.product.get("packages", [])
        pkg      = next((p for p in packages if p["id"] == pkg_id), None)
        if not pkg:
            await interaction.response.send_message("Pacote não encontrado.", ephemeral=True)
            return

        # Cria o canal de carrinho
        order_num = str(uuid.uuid4())[:8].upper()
        guild     = self.guild
        member    = self.member

        # Verifica carrinho já aberto
        existing = discord.utils.get(guild.text_channels, name=f"carrinho-{member.id}")
        if existing:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description=f"Você já tem um carrinho aberto: {existing.mention}",
                    color=COLOR_WARN,
                ),
                view=None,
            )
            return

        category = guild.get_channel(CART_CATEGORY_ID) if CART_CATEGORY_ID else None
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
            cart_ch = await guild.create_text_channel(
                name=f"carrinho-{member.id}",
                category=category,
                overwrites=overwrites,
                topic=f"Carrinho de {member} ({member.id}) | Pedido {order_num} | Jr Store",
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Sem permissão para criar canal de carrinho.", ephemeral=True
            )
            return

        # Confirma ao usuário
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=f"✅ Carrinho criado! Acesse {cart_ch.mention}",
                color=COLOR_SUCCESS,
            ),
            view=None,
        )

        # Envia embed do carrinho no canal privado
        cart_embed = embed_cart_channel(
            member=member,
            product=self.product,
            pkg=pkg,
            order_num=order_num,
            qty=1,
            coupon_discount=0.0,
            lang=self.lang,
        )
        cart_view = CartChannelView(
            member=member,
            product=self.product,
            pkg=pkg,
            order_num=order_num,
            qty=1,
            coupon_discount=0.0,
            lang=self.lang,
        )
        await cart_ch.send(
            content=member.mention,
            embed=cart_embed,
            view=cart_view,
        )
        await send_log(guild, f"`CARRINHO` {member.mention} abriu carrinho {cart_ch.mention} — {self.product['name']['pt']} / {pkg['label_pt']}")


class CartChannelView(discord.ui.View):
    """View dentro do canal de carrinho."""

    def __init__(
        self,
        member: discord.Member,
        product: dict,
        pkg: dict,
        order_num: str,
        qty: int,
        coupon_discount: float,
        lang: str,
    ):
        super().__init__(timeout=None)
        self.member          = member
        self.product         = product
        self.pkg             = pkg
        self.order_num       = order_num
        self.qty             = qty
        self.coupon_discount = coupon_discount
        self.lang            = lang

    async def _refresh(self, interaction: discord.Interaction) -> None:
        embed = embed_cart_channel(
            self.member, self.product, self.pkg,
            self.order_num, self.qty, self.coupon_discount, self.lang,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="💳 Pagar via PIX", style=discord.ButtonStyle.success, emoji="💳", row=0)
    async def pay_pix(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Este não é o seu carrinho.", ephemeral=True)
            return
        modal = PayEmailModal(self.product, self.pkg, self.order_num, self.qty, self.coupon_discount, self.lang)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🏷️ Cupom", style=discord.ButtonStyle.secondary, row=0)
    async def coupon(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Este não é o seu carrinho.", ephemeral=True)
            return
        modal = CouponModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="➕", style=discord.ButtonStyle.secondary, row=1)
    async def inc_qty(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Este não é o seu carrinho.", ephemeral=True)
            return
        self.qty = min(self.qty + 1, 10)
        await self._refresh(interaction)

    @discord.ui.button(label="➖", style=discord.ButtonStyle.secondary, row=1)
    async def dec_qty(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Este não é o seu carrinho.", ephemeral=True)
            return
        self.qty = max(self.qty - 1, 1)
        await self._refresh(interaction)

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger, row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.member.id and not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return
        embed = discord.Embed(
            title="🗑️ Carrinho Cancelado",
            description="Este carrinho foi cancelado. O canal será deletado em 10 segundos.",
            color=COLOR_ERROR,
        )
        await interaction.response.edit_message(embed=embed, view=None)
        await asyncio.sleep(10)
        try:
            await interaction.channel.delete(reason="Carrinho cancelado")
        except Exception:
            pass


class CouponModal(discord.ui.Modal):
    code = discord.ui.TextInput(
        label="Código do Cupom",
        placeholder="Ex: JRSTORE10",
        required=True,
        min_length=3,
        max_length=30,
    )

    def __init__(self, cart_view: CartChannelView):
        super().__init__(title="🏷️ Cupom de Desconto", timeout=120)
        self.cart_view = cart_view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # TODO: adicionar validação real de cupons aqui
        code = str(self.code.value).strip().upper()
        await interaction.response.send_message(
            f"❌ Cupom `{code}` inválido ou expirado.", ephemeral=True
        )


class PayEmailModal(discord.ui.Modal):
    email = discord.ui.TextInput(
        label="E-mail (para o recibo Mercado Pago)",
        placeholder="seuemail@exemplo.com",
        required=True,
        min_length=5,
        max_length=100,
    )

    def __init__(self, product, pkg, order_num, qty, coupon_discount, lang):
        super().__init__(
            title="Finalizar Compra" if lang == "pt" else "Complete Purchase",
            timeout=300,
        )
        self.product         = product
        self.pkg             = pkg
        self.order_num       = order_num
        self.qty             = qty
        self.coupon_discount = coupon_discount
        self.lang            = lang

    async def on_submit(self, interaction: discord.Interaction) -> None:
        payer_email = str(self.email.value).strip()
        user        = interaction.user
        total       = max(0.0, self.pkg["price"] * self.qty - self.coupon_discount)
        label       = self.pkg["label_pt"] if self.lang == "pt" else self.pkg["label_en"]

        await interaction.response.send_message(
            "⏳ Gerando PIX..." if self.lang == "pt" else "⏳ Generating PIX...",
            ephemeral=True,
        )

        external_ref = f"{user.id}_{self.product['id']}_{self.order_num}"

        try:
            data = await create_pix_payment(
                amount=total,
                description=f"Jr Store — {self.product['name']['pt']} / {self.pkg['label_pt']}",
                payer_email=payer_email,
                external_reference=external_ref,
            )
        except Exception as exc:
            logger.exception("Erro ao criar pagamento PIX: %s", exc)
            await interaction.followup.send(
                f"❌ Erro ao gerar PIX: {exc}", ephemeral=True
            )
            return

        pending_payments[str(data["id"])] = {
            "user_id":    user.id,
            "product_id": self.product["id"],
            "pkg_id":     self.pkg["id"],
            "guild_id":   interaction.guild_id,
            "order_num":  self.order_num,
            "qty":        self.qty,
            "channel_id": interaction.channel_id,
            "lang":       self.lang,
        }

        txn   = data["point_of_interaction"]["transaction_data"]
        embed = embed_pix_payment(self.product, self.pkg, data, self.order_num, self.qty, self.lang)

        try:
            qr_file = qr_code_to_file(txn["qr_code_base64"])
            await interaction.channel.send(embed=embed, file=qr_file)
        except Exception as exc:
            logger.error("Erro ao enviar QR: %s", exc)

        await interaction.followup.send(
            "✅ PIX gerado acima! Você tem 30 minutos para pagar."
            if self.lang == "pt"
            else "✅ PIX generated above! You have 30 minutes to pay.",
            ephemeral=True,
        )
        if interaction.guild:
            await send_log(
                interaction.guild,
                f"`PIX` {user.mention} gerou pagamento — {self.product['name']['pt']} / {label} "
                f"| Pedido `{self.order_num}` | {format_brl(total)}",
            )


class _StoreLangBtn(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="🌐  Language",
            custom_id="jr_store_lang",
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        # Detecta lang atual pelo embed
        embed = interaction.message.embeds[0] if interaction.message.embeds else None
        lang  = "en" if embed and "Shop" in embed.title else "pt"
        new_lang = "en" if lang == "pt" else "pt"
        new_embed = embed_store_main(new_lang)
        await interaction.response.edit_message(embed=new_embed)


# ─── VIEWS — VERIFY ──────────────────────────────────────────────────────────

class VerifyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Verificar  /  Verify",
            custom_id="jr_verify",
            emoji="✅",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Erro interno.", ephemeral=True)
            return
        if not VERIFY_ROLE_ID:
            await interaction.response.send_message(
                "✅ Verificação concluída! (VERIFY_ROLE_ID não configurado)", ephemeral=True
            )
            return
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if not role:
            await interaction.response.send_message("Role não encontrado.", ephemeral=True)
            return
        if role in member.roles:
            await interaction.response.send_message("✅ Você já está verificado!", ephemeral=True)
            return
        try:
            await member.add_roles(role, reason="Verificação Jr Store")
            await interaction.response.send_message(
                "✅ Verificado com sucesso! Bem-vindo à **Jr Store**. 💜", ephemeral=True
            )
            await send_log(interaction.guild, f"`VERIFY` {member.mention} verificou-se.")
        except discord.Forbidden:
            await interaction.response.send_message("Sem permissão para adicionar role.", ephemeral=True)


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VerifyButton())


# ─── VIEWS — TICKET ───────────────────────────────────────────────────────────

async def _make_transcript(channel: discord.TextChannel) -> bytes:
    lines = [f"📋 Transcrição do ticket: #{channel.name}\n{'='*50}\n"]
    async for msg in channel.history(limit=500, oldest_first=True):
        ts   = msg.created_at.strftime("%d/%m/%Y %H:%M")
        text = msg.content or "[sem texto]"
        lines.append(f"[{ts}] {msg.author.display_name}: {text}")
        for att in msg.attachments:
            lines.append(f"[{ts}] {msg.author.display_name}: [Anexo: {att.url}]")
    return "\n".join(lines).encode()


async def _close_ticket(channel: discord.TextChannel, guild: discord.Guild, closed_by: discord.Member) -> None:
    owner_id = None
    m = re.match(r"ticket-(\d+)", channel.name)
    if m:
        owner_id = int(m.group(1))

    transcript_bytes = await _make_transcript(channel)

    # Envia transcrição
    dest_ch = (
        guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        or (guild.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None)
    )
    if dest_ch:
        t_embed = discord.Embed(
            title=f"📋 Ticket Fechado — #{channel.name}",
            description=f"**Fechado por:** {closed_by.mention}",
            color=COLOR_WARN,
        )
        t_embed.timestamp = datetime.now(timezone.utc)
        await dest_ch.send(
            embed=t_embed,
            file=discord.File(fp=io.BytesIO(transcript_bytes), filename=f"transcript-{channel.name}.txt"),
        )

    # DM para o dono
    if owner_id:
        try:
            owner = guild.get_member(owner_id) or await bot.fetch_user(owner_id)
            dm = discord.Embed(
                title="🎫 Seu ticket foi encerrado — Jr Store",
                description=(
                    "Seu ticket foi fechado pela equipe.\n\n"
                    "Esperamos ter te ajudado! 💜\n"
                    "Se precisar de mais suporte, abra um novo ticket a qualquer momento."
                ),
                color=COLOR_MAIN,
            )
            dm.set_footer(text="Jr Store  •  Obrigado pelo contato")
            dm.timestamp = datetime.now(timezone.utc)
            await owner.send(embed=dm)
        except Exception:
            pass

    await asyncio.sleep(3)
    try:
        await channel.delete(reason=f"Ticket fechado por {closed_by}")
    except Exception:
        pass


class TicketInternalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🙋 Assumir Ticket", style=discord.ButtonStyle.primary, custom_id="jr_ticket_claim", row=0)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True)
            return

        owner_id = None
        m = re.match(r"ticket-(\d+)", interaction.channel.name)
        if m:
            owner_id = int(m.group(1))
        owner_mention = f"<@{owner_id}>" if owner_id else "usuário"

        embed = discord.Embed(
            title="✅ Ticket Assumido",
            description=f"**{interaction.user.display_name}** está atendendo este ticket.\n\n{owner_mention}, você será atendido em breve! 🎉",
            color=COLOR_SUCCESS,
        )
        embed.timestamp = datetime.now(timezone.utc)
        await interaction.response.send_message(embed=embed)

        button.disabled = True
        button.label    = f"✅ Assumido por {interaction.user.display_name}"
        await interaction.message.edit(view=self)
        await send_log(interaction.guild, f"`TICKET ASSUMIDO` {interaction.channel.mention} por {interaction.user.mention}")

    @discord.ui.button(label="🔒 Fechar Ticket", style=discord.ButtonStyle.danger, custom_id="jr_ticket_close", row=0)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True)
            return
        embed = discord.Embed(
            title="🔒 Encerrando Ticket...",
            description="Gerando transcrição e notificando o usuário...",
            color=COLOR_ERROR,
        )
        await interaction.response.send_message(embed=embed)
        await send_log(interaction.guild, f"`TICKET FECHADO` {interaction.channel.mention} por {interaction.user.mention}")
        await _close_ticket(interaction.channel, interaction.guild, interaction.user)


class TicketCreateButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="🎫 Abrir Ticket  /  Open Ticket",
            custom_id="jr_ticket_create",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
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
            title="🎫 Ticket Aberto — Jr Store",
            description=(
                f"Olá {member.mention}! 👋\n\n"
                "**Descreva seu problema ou dúvida** com o máximo de detalhes.\n"
                "Nossa equipe irá te atender em breve!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🙋 **Assumir** — Apenas administradores\n"
                "🔒 **Fechar** — Gera transcrição e notifica você no privado"
            ),
            color=COLOR_MAIN,
        )
        embed.set_footer(text="Jr Store  •  Suporte  •  Tempo médio < 24h")
        embed.timestamp = datetime.now(timezone.utc)
        await channel.send(content=member.mention, embed=embed, view=TicketInternalView())
        await interaction.response.send_message(f"✅ Ticket criado: {channel.mention}", ephemeral=True)
        await send_log(guild, f"`TICKET` {member.mention} abriu {channel.mention}")


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCreateButton())


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
    await interaction.response.send_message(f"✅ Painel de configs publicado em {channel.mention}.", ephemeral=True)


@tree.command(name="setuploja", description="[Admin] Publica o painel da loja em um canal.")
@app_commands.default_permissions(administrator=True)
async def cmd_setuploja(interaction: discord.Interaction, canal: discord.TextChannel) -> None:
    embed = embed_store_main("pt")
    view  = StoreMainView()
    await canal.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Loja publicada em {canal.mention}.", ephemeral=True)


@tree.command(name="setupverify", description="[Admin] Publica o painel de verificação em um canal.")
@app_commands.default_permissions(administrator=True)
async def cmd_setupverify(interaction: discord.Interaction, canal: discord.TextChannel) -> None:
    embed = embed_verify("pt")
    view  = VerifyView()
    await canal.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Painel de verificação publicado em {canal.mention}.", ephemeral=True)


@tree.command(name="setupticket", description="[Admin] Publica o painel de tickets em um canal.")
@app_commands.default_permissions(administrator=True)
async def cmd_setupticket(interaction: discord.Interaction, canal: discord.TextChannel) -> None:
    embed = embed_ticket_panel("pt")
    view  = TicketPanelView()
    await canal.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Painel de tickets publicado em {canal.mention}.", ephemeral=True)


# ── Gerenciar Produtos ────────────────────────────────────────────────────────

@tree.command(name="produto_novo", description="[Admin] Cria um novo produto/hack na loja.")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    id_produto="ID único (sem espaços, ex: skeet)",
    nome_pt="Nome em português",
    nome_en="Nome em inglês",
    descricao_pt="Descrição em português",
    descricao_en="Descrição em inglês",
    emoji="Emoji do produto",
    imagem_url="URL da imagem (opcional)",
)
async def cmd_produto_novo(
    interaction: discord.Interaction,
    id_produto: str,
    nome_pt: str,
    nome_en: str,
    descricao_pt: str,
    descricao_en: str,
    emoji: str = "📦",
    imagem_url: str = "",
) -> None:
    products = get_products()
    if any(p["id"] == id_produto for p in products):
        await interaction.response.send_message(f"❌ ID `{id_produto}` já existe.", ephemeral=True)
        return
    new_p = {
        "id":          id_produto,
        "name":        {"pt": nome_pt, "en": nome_en},
        "description": {"pt": descricao_pt, "en": descricao_en},
        "emoji":       emoji,
        "image_url":   imagem_url or None,
        "active":      True,
        "packages":    [],
    }
    products.append(new_p)
    save_products(products)
    embed = discord.Embed(title="✅ Produto Criado", description=f"**{emoji} {nome_pt}** criado com sucesso!\nAdicione pacotes com `/pacote_novo`.", color=COLOR_SUCCESS)
    embed.add_field(name="ID", value=f"`{id_produto}`", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="produto_editar", description="[Admin] Edita campo de um produto.")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    id_produto="ID do produto",
    campo="Campo: nome_pt | nome_en | descricao_pt | descricao_en | emoji | imagem_url | ativo",
    valor="Novo valor",
)
async def cmd_produto_editar(interaction: discord.Interaction, id_produto: str, campo: str, valor: str) -> None:
    products = get_products()
    product  = next((p for p in products if p["id"] == id_produto), None)
    if not product:
        await interaction.response.send_message(f"❌ Produto `{id_produto}` não encontrado.", ephemeral=True)
        return
    campo = campo.lower().strip()
    field_map = {
        "nome_pt":        ("name", "pt"),
        "nome_en":        ("name", "en"),
        "descricao_pt":   ("description", "pt"),
        "descricao_en":   ("description", "en"),
    }
    if campo in field_map:
        key, sub = field_map[campo]
        product[key][sub] = valor
    elif campo == "emoji":
        product["emoji"] = valor
    elif campo == "imagem_url":
        product["image_url"] = valor or None
    elif campo == "ativo":
        product["active"] = valor.lower() in ("true", "sim", "yes", "1", "ativo")
    else:
        await interaction.response.send_message(f"❌ Campo desconhecido: `{campo}`", ephemeral=True)
        return
    save_products(products)
    await interaction.response.send_message(f"✅ `{id_produto}` → `{campo}` = `{valor}`", ephemeral=True)


@tree.command(name="pacote_novo", description="[Admin] Adiciona um pacote (config) a um produto.")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    id_produto="ID do produto pai",
    id_pacote="ID do pacote (ex: closet, __full__)",
    label_pt="Nome em português",
    label_en="Nome em inglês",
    preco="Preço em BRL",
    descricao_pt="Descrição em português",
    descricao_en="Descrição em inglês",
)
async def cmd_pacote_novo(
    interaction: discord.Interaction,
    id_produto: str,
    id_pacote: str,
    label_pt: str,
    label_en: str,
    preco: float,
    descricao_pt: str,
    descricao_en: str,
) -> None:
    products = get_products()
    product  = next((p for p in products if p["id"] == id_produto), None)
    if not product:
        await interaction.response.send_message(f"❌ Produto `{id_produto}` não encontrado.", ephemeral=True)
        return
    if any(pk["id"] == id_pacote for pk in product.get("packages", [])):
        await interaction.response.send_message(f"❌ Pacote `{id_pacote}` já existe neste produto.", ephemeral=True)
        return
    pkg = {
        "id":             id_pacote,
        "label_pt":       label_pt,
        "label_en":       label_en,
        "price":          preco,
        "description_pt": descricao_pt,
        "description_en": descricao_en,
    }
    product.setdefault("packages", []).append(pkg)
    save_products(products)
    await interaction.response.send_message(
        f"✅ Pacote **{label_pt}** adicionado ao produto `{id_produto}` — {format_brl(preco)}",
        ephemeral=True,
    )


@tree.command(name="pacote_editar", description="[Admin] Edita campo de um pacote.")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    id_produto="ID do produto",
    id_pacote="ID do pacote",
    campo="Campo: label_pt | label_en | preco | descricao_pt | descricao_en",
    valor="Novo valor",
)
async def cmd_pacote_editar(
    interaction: discord.Interaction, id_produto: str, id_pacote: str, campo: str, valor: str
) -> None:
    products = get_products()
    product  = next((p for p in products if p["id"] == id_produto), None)
    if not product:
        await interaction.response.send_message(f"❌ Produto `{id_produto}` não encontrado.", ephemeral=True)
        return
    pkg = next((pk for pk in product.get("packages", []) if pk["id"] == id_pacote), None)
    if not pkg:
        await interaction.response.send_message(f"❌ Pacote `{id_pacote}` não encontrado.", ephemeral=True)
        return
    campo = campo.lower().strip()
    try:
        if campo == "label_pt":       pkg["label_pt"]       = valor
        elif campo == "label_en":     pkg["label_en"]       = valor
        elif campo == "preco":        pkg["price"]          = float(valor)
        elif campo == "descricao_pt": pkg["description_pt"] = valor
        elif campo == "descricao_en": pkg["description_en"] = valor
        else:
            await interaction.response.send_message(f"❌ Campo desconhecido: `{campo}`", ephemeral=True)
            return
    except ValueError:
        await interaction.response.send_message("❌ Valor inválido.", ephemeral=True)
        return
    save_products(products)
    await interaction.response.send_message(f"✅ Pacote `{id_pacote}` → `{campo}` = `{valor}`", ephemeral=True)


@tree.command(name="pacote_remover", description="[Admin] Remove um pacote de um produto.")
@app_commands.default_permissions(administrator=True)
async def cmd_pacote_remover(interaction: discord.Interaction, id_produto: str, id_pacote: str) -> None:
    products = get_products()
    product  = next((p for p in products if p["id"] == id_produto), None)
    if not product:
        await interaction.response.send_message(f"❌ Produto `{id_produto}` não encontrado.", ephemeral=True)
        return
    before = len(product.get("packages", []))
    product["packages"] = [pk for pk in product.get("packages", []) if pk["id"] != id_pacote]
    if len(product["packages"]) == before:
        await interaction.response.send_message(f"❌ Pacote `{id_pacote}` não encontrado.", ephemeral=True)
        return
    save_products(products)
    await interaction.response.send_message(f"✅ Pacote `{id_pacote}` removido.", ephemeral=True)


@tree.command(name="produto_listar", description="[Admin] Lista todos os produtos e pacotes.")
@app_commands.default_permissions(administrator=True)
async def cmd_produto_listar(interaction: discord.Interaction) -> None:
    products = get_products()
    embed    = discord.Embed(title="📦 Produtos da Loja", color=COLOR_MAIN)
    if not products:
        embed.description = "Nenhum produto cadastrado."
    for p in products:
        status = "✅" if p.get("active", True) else "🔧"
        pkgs   = p.get("packages", [])
        pkg_text = "\n".join(
            f"  └ `{pk['id']}` {pk['label_pt']} — {format_brl(pk['price'])}"
            for pk in pkgs
        ) or "  *(sem pacotes)*"
        img = f"\n  🖼️ {p['image_url']}" if p.get("image_url") else ""
        embed.add_field(
            name=f"{status} {p.get('emoji','')} {p['name']['pt']} (`{p['id']}`){img}",
            value=pkg_text,
            inline=False,
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="produto_remover", description="[Admin] Remove um produto inteiro.")
@app_commands.default_permissions(administrator=True)
async def cmd_produto_remover(interaction: discord.Interaction, id_produto: str) -> None:
    products = get_products()
    new_list = [p for p in products if p["id"] != id_produto]
    if len(new_list) == len(products):
        await interaction.response.send_message(f"❌ Produto `{id_produto}` não encontrado.", ephemeral=True)
        return
    save_products(new_list)
    await interaction.response.send_message(f"✅ Produto `{id_produto}` removido.", ephemeral=True)


@tree.command(name="anunciar", description="[Admin] Envia anúncio em um canal.")
@app_commands.default_permissions(administrator=True)
async def cmd_anunciar(
    interaction: discord.Interaction,
    canal: discord.TextChannel,
    titulo: str,
    mensagem: str,
    mencionar_everyone: bool = False,
) -> None:
    embed = discord.Embed(title=titulo, description=mensagem, color=COLOR_MAIN)
    embed.set_footer(text=f"Jr Store  •  por {interaction.user.display_name}")
    embed.timestamp = datetime.now(timezone.utc)
    await canal.send(content="@everyone" if mencionar_everyone else None, embed=embed)
    await interaction.response.send_message(f"✅ Anúncio enviado em {canal.mention}.", ephemeral=True)


@tree.command(name="stats", description="Mostra estatísticas do servidor.")
async def cmd_stats(interaction: discord.Interaction) -> None:
    guild    = interaction.guild
    total    = guild.member_count
    bots     = sum(1 for m in guild.members if m.bot)
    humans   = total - bots
    online   = sum(1 for m in guild.members if m.status != discord.Status.offline and not m.bot)
    channels = len(guild.text_channels)
    embed    = discord.Embed(title=f"📊 {guild.name}", color=COLOR_MAIN)
    embed.add_field(name="Membros",  value=str(humans),   inline=True)
    embed.add_field(name="Online",   value=str(online),   inline=True)
    embed.add_field(name="Canais",   value=str(channels), inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="Jr Store 💜")
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
        name="Suporte",
        value="`/stats` — Estatísticas do servidor",
        inline=False,
    )
    embed.add_field(
        name="Admin — Setup",
        value=(
            "`/setup` — Painel de configs free\n"
            "`/setuploja` — Loja em um canal\n"
            "`/setupverify` — Verificação\n"
            "`/setupticket` — Painel de tickets\n"
            "`/anunciar` — Anúncio"
        ),
        inline=False,
    )
    embed.add_field(
        name="Admin — Produtos",
        value=(
            "`/produto_novo` — Cria produto/hack\n"
            "`/produto_editar` — Edita produto\n"
            "`/produto_listar` — Lista produtos e pacotes\n"
            "`/produto_remover` — Remove produto\n"
            "`/pacote_novo` — Adiciona pacote a um produto\n"
            "`/pacote_editar` — Edita pacote\n"
            "`/pacote_remover` — Remove pacote"
        ),
        inline=False,
    )
    embed.set_footer(text="Jr Store 💜")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ─── WEBHOOK MERCADO PAGO ────────────────────────────────────────────────────

async def handle_mp_webhook(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except Exception:
        return web.Response(status=400, text="Invalid JSON")

    action = body.get("action", "")
    data   = body.get("data", {})
    pid    = str(data.get("id", ""))

    logger.info("Webhook MP: action=%s id=%s", action, pid)

    if action not in ("payment.updated", "payment.created") or not pid:
        return web.Response(status=200, text="OK")

    try:
        payment = await get_payment(pid)
    except Exception as exc:
        logger.error("Erro ao consultar pagamento %s: %s", pid, exc)
        return web.Response(status=200, text="OK")

    if payment.get("status") != "approved":
        return web.Response(status=200, text="OK")

    pending = pending_payments.pop(pid, None)
    if not pending:
        ext_ref = payment.get("external_reference", "")
        if ext_ref:
            parts = ext_ref.split("_")
            if len(parts) >= 2:
                pending = {
                    "user_id":    int(parts[0]),
                    "product_id": parts[1],
                    "pkg_id":     "__full__",
                    "guild_id":   None,
                    "order_num":  parts[2] if len(parts) > 2 else "???",
                    "qty":        1,
                    "channel_id": None,
                    "lang":       "pt",
                }

    if not pending:
        logger.warning("Pagamento aprovado sem pendente: id=%s", pid)
        return web.Response(status=200, text="OK")

    user_id    = pending["user_id"]
    product_id = pending["product_id"]
    pkg_id     = pending.get("pkg_id", "__full__")
    guild_id   = pending.get("guild_id")
    order_num  = pending.get("order_num", "???")
    qty        = pending.get("qty", 1)
    channel_id = pending.get("channel_id")
    lang       = pending.get("lang", "pt")

    products = get_products()
    product  = next((p for p in products if p["id"] == product_id), None)
    if not product:
        return web.Response(status=200, text="OK")

    packages = product.get("packages", [])
    pkg      = next((pk for pk in packages if pk["id"] == pkg_id), None)
    if not pkg:
        pkg = {"id": pkg_id, "label_pt": pkg_id, "label_en": pkg_id, "price": 0, "description_pt": "", "description_en": ""}

    user = bot.get_user(user_id)
    if not user:
        try:
            user = await bot.fetch_user(user_id)
        except Exception:
            return web.Response(status=200, text="OK")

    # Envia confirmação no canal do carrinho
    if channel_id and guild_id:
        guild = bot.get_guild(guild_id)
        if guild:
            cart_ch = guild.get_channel(channel_id)
            if cart_ch:
                confirm_embed = embed_payment_confirmed(product, pkg, lang)
                await cart_ch.send(embed=confirm_embed)

    # Envia as configs no canal do carrinho
    hack_id = product_id  # produto id = hack id (ex: "memesense")
    if pkg_id == "__full__":
        configs_to_send = CONFIGS.get(hack_id, [])
    else:
        cfg = get_config(hack_id, pkg_id)
        configs_to_send = [cfg] if cfg else []

    if channel_id and guild_id:
        guild = bot.get_guild(guild_id)
        if guild:
            cart_ch = guild.get_channel(channel_id)
            if cart_ch:
                for cfg in configs_to_send:
                    cfg_embed = embed_config_dm(hack_id, cfg, lang)
                    cfg_view  = ConfigDMView(hack_id, cfg["id"], lang)
                    await cart_ch.send(embed=cfg_embed, view=cfg_view)

    # Role paga
    if PAID_ROLE_ID and guild_id:
        guild = bot.get_guild(guild_id)
        if guild:
            member = guild.get_member(user_id)
            if member:
                role = guild.get_role(PAID_ROLE_ID)
                if role:
                    try:
                        await member.add_roles(role, reason="Pagamento aprovado — Jr Store")
                    except discord.Forbidden:
                        pass
            await send_log(
                guild,
                f"`VENDA` {user.mention} pagamento aprovado — **{product['name']['pt']}** / {pkg['label_pt']} "
                f"| Pedido `{order_num}` x{qty} | {format_brl(pkg['price'] * qty)} | MP `{pid}`",
            )

    return web.Response(status=200, text="OK")


# ─── EVENTOS ─────────────────────────────────────────────────────────────────

@bot.event
async def on_ready() -> None:
    bot.add_view(HackSelectView())
    bot.add_view(VerifyView())
    bot.add_view(TicketPanelView())
    bot.add_view(TicketInternalView())
    bot.add_view(StoreMainView())

    for hack_id in HACKS:
        for cfg in CONFIGS[hack_id]:
            for lang in ("pt", "en"):
                bot.add_view(ConfigDMView(hack_id, cfg["id"], lang))

    if GUILD_ID:
        guild_obj = discord.Object(id=GUILD_ID)
        tree.copy_global_to(guild=guild_obj)
        await tree.sync(guild=guild_obj)
    else:
        await tree.sync()

    logger.info("Jr Store Bot v3 online — %s | Servidores: %d", bot.user, len(bot.guilds))


@bot.event
async def on_member_join(member: discord.Member) -> None:
    await send_log(member.guild, f"`JOIN` {member.mention} entrou.")


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    await send_log(member.guild, f"`LEAVE` `{member}` saiu.")


# ─── WEB SERVER ──────────────────────────────────────────────────────────────

async def start_web_server() -> None:
    app = web.Application()
    app.router.add_post("/webhook/mp", handle_mp_webhook)
    app.router.add_get("/health", lambda r: web.Response(text="Jr Store Bot v3 — OK 💜"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logger.info("Web server na porta %d", PORT)


async def main() -> None:
    if not TOKEN:
        raise EnvironmentError("DISCORD_TOKEN não definida.")
    async with bot:
        await start_web_server()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
