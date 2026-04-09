
import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import discord
from discord.ext import commands

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("jr-store-bot")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CONFIG_CHANNEL_ID = int(os.getenv("CONFIG_CHANNEL_ID", "0"))
BRAND_NAME = os.getenv("BRAND_NAME", "Jr Store")
PANEL_MARKER = "jr_store_free_configs_panel_v1"

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN não definido.")
if not CONFIG_CHANNEL_ID:
    raise RuntimeError("CONFIG_CHANNEL_ID não definido.")

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)


@dataclass
class ConfigItem:
    id: str
    product: str
    title: str
    display_name: str
    delivery_type: str
    shared_code: Optional[str]
    summary: str
    positioning: str
    setup_name_suggestion: str
    setup_steps: List[str]
    keybinds: List[Dict[str, str]]
    details: List[str]
    update_notes: List[str]


def load_catalog() -> Dict[str, List[ConfigItem]]:
    with open("data/configs.json", "r", encoding="utf-8") as fp:
        raw = json.load(fp)

    grouped: Dict[str, List[ConfigItem]] = {}
    for entry in raw["configs"]:
        item = ConfigItem(**entry)
        grouped.setdefault(item.product, []).append(item)
    return grouped


CATALOG = load_catalog()


def format_keybinds(keybinds: List[Dict[str, str]]) -> str:
    lines = []
    for bind in keybinds:
        label = bind["label"]
        key = bind["key"]
        mode = bind["mode"]
        lines.append(f"• **{label}:** `{key}` — {mode}")
    return "\n".join(lines)


def format_steps(steps: List[str]) -> str:
    return "\n".join(f"{idx}. {step}" for idx, step in enumerate(steps, start=1))


def make_public_panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title=f"{BRAND_NAME} • Configs Free",
        description=(
            "Selecione o produto e depois a configuração para receber tudo no privado.\n\n"
            "A entrega é automática e organizada com instruções, binds e observações da configuração."
        ),
        color=discord.Color.dark_embed()
    )
    embed.add_field(
        name="Como funciona",
        value=(
            "1. Clique em **Abrir catálogo**.\n"
            "2. Escolha o produto.\n"
            "3. Escolha a configuração.\n"
            "4. Receba a entrega no seu privado."
        ),
        inline=False
    )
    embed.add_field(
        name="Entrega atual",
        value="Catálogo de configs free da **Jr Store** para **Memesense**.",
        inline=False
    )
    embed.set_footer(text=PANEL_MARKER)
    return embed


def make_dm_embed(item: ConfigItem, user: discord.abc.User) -> discord.Embed:
    embed = discord.Embed(
        title=f"{BRAND_NAME} • {item.display_name}",
        description=item.summary,
        color=discord.Color.blurple()
    )
    embed.add_field(name="Posicionamento", value=item.positioning, inline=False)
    embed.add_field(
        name="Share code",
        value=f"`{item.shared_code}`" if item.shared_code else "Entrega por arquivo",
        inline=False
    )
    embed.add_field(
        name="Importação",
        value=(
            f"Nome sugerido para salvar: **{item.setup_name_suggestion}**\n\n"
            f"{format_steps(item.setup_steps)}"
        ),
        inline=False
    )
    embed.add_field(
        name="Binds padrão do pack",
        value=format_keybinds(item.keybinds),
        inline=False
    )
    if item.details:
        embed.add_field(
            name="Observações",
            value="\n".join(f"• {line}" for line in item.details),
            inline=False
        )
    if item.update_notes:
        embed.add_field(
            name="Notas do pack",
            value="\n".join(f"• {line}" for line in item.update_notes[:5]),
            inline=False
        )
    embed.set_footer(text=f"{BRAND_NAME} • Entrega automática | solicitado por {user}")
    return embed


def make_secondary_dm_embed() -> discord.Embed:
    embed = discord.Embed(
        title=f"{BRAND_NAME} • Instruções gerais",
        description=(
            "Este material foi organizado com branding autoral da **Jr Store**.\n"
            "Sempre revise binds e comportamento da configuração antes de usar."
        ),
        color=discord.Color.dark_embed()
    )
    embed.add_field(
        name="Atualizações",
        value=(
            "Quando uma config usa o mesmo share code ao longo das revisões, "
            "basta repetir a importação para reaplicar a versão que você quiser usar."
        ),
        inline=False
    )
    embed.add_field(
        name="Fluxo recomendado",
        value=(
            "• Importar a config\n"
            "• Conferir binds\n"
            "• Ajustar apenas o indispensável\n"
            "• Testar em ambiente controlado antes de uso normal"
        ),
        inline=False
    )
    return embed


class ConfigSelect(discord.ui.Select):
    def __init__(self, product: str):
        self.product = product
        items = CATALOG.get(product, [])
        options = [
            discord.SelectOption(
                label=item.title,
                value=item.id,
                description=(item.summary[:95] + "...") if len(item.summary) > 98 else item.summary
            )
            for item in items
        ]
        super().__init__(
            placeholder="Selecione a configuração",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_id = self.values[0]
        item = next(
            (cfg for cfg in CATALOG[self.product] if cfg.id == selected_id),
            None
        )
        if not item:
            await interaction.response.send_message(
                "Não consegui localizar essa configuração no catálogo atual.",
                ephemeral=True
            )
            return

        try:
            dm_embed = make_dm_embed(item, interaction.user)
            secondary = make_secondary_dm_embed()
            await interaction.user.send(embeds=[dm_embed, secondary])

            await interaction.response.send_message(
                "Entrega realizada no seu privado.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "Não consegui enviar no privado. Ative suas DMs para este servidor e tente novamente.",
                ephemeral=True
            )


class ConfigView(discord.ui.View):
    def __init__(self, product: str):
        super().__init__(timeout=300)
        self.add_item(ConfigSelect(product))


class ProductSelect(discord.ui.Select):
    def __init__(self):
        products = sorted(CATALOG.keys())
        options = [
            discord.SelectOption(
                label=product,
                value=product,
                description=f"Ver catálogo disponível para {product}"
            )
            for product in products
        ]
        super().__init__(
            placeholder="Selecione o produto",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        product = self.values[0]
        embed = discord.Embed(
            title=f"{BRAND_NAME} • {product}",
            description="Escolha a configuração que deseja receber no privado.",
            color=discord.Color.dark_embed()
        )
        embed.add_field(
            name="Disponíveis agora",
            value="\n".join(f"• {cfg.title}" for cfg in CATALOG[product]),
            inline=False
        )
        await interaction.response.send_message(
            embed=embed,
            view=ConfigView(product),
            ephemeral=True
        )


class ProductView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(ProductSelect())


class OpenCatalogButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Abrir catálogo",
            style=discord.ButtonStyle.primary,
            custom_id="jr_store_open_catalog"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{BRAND_NAME} • Catálogo",
                description="Selecione abaixo o produto para continuar.",
                color=discord.Color.dark_embed()
            ),
            view=ProductView(),
            ephemeral=True
        )


class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OpenCatalogButton())


async def upsert_panel_message():
    channel = bot.get_channel(CONFIG_CHANNEL_ID)
    if channel is None:
        logger.error("Canal CONFIG_CHANNEL_ID não encontrado.")
        return

    target_message = None
    async for message in channel.history(limit=50):
        if (
            message.author.id == bot.user.id
            and message.embeds
            and message.embeds[0].footer
            and message.embeds[0].footer.text == PANEL_MARKER
        ):
            target_message = message
            break

    embed = make_public_panel_embed()
    view = PanelView()

    if target_message:
        await target_message.edit(embed=embed, view=view)
        logger.info("Painel atualizado.")
        return

    sent = await channel.send(embed=embed, view=view)
    try:
        await sent.pin(reason="Painel principal de configs free da Jr Store")
    except discord.Forbidden:
        logger.warning("Sem permissão para fixar a mensagem.")
    logger.info("Painel criado.")


@bot.event
async def on_ready():
    logger.info("Logado como %s (%s)", bot.user, bot.user.id)
    bot.add_view(PanelView())
    await upsert_panel_message()


@bot.command(name="repostar_painel")
@commands.has_permissions(manage_guild=True)
async def repostar_painel(ctx: commands.Context):
    await upsert_panel_message()
    await ctx.reply("Painel revisado.", mention_author=False)


@repostar_painel.error
async def repostar_painel_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("Você precisa da permissão de gerenciar servidor para usar este comando.", mention_author=False)
        return
    logger.exception("Erro no comando repostar_painel: %s", error)
    await ctx.reply("Ocorreu um erro ao revisar o painel.", mention_author=False)


bot.run(DISCORD_TOKEN)
