import io
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CATALOG_PATH = DATA_DIR / "catalog.json"
BRAND_NAME = os.getenv("BRAND_NAME", "Jr Store")
CONFIG_CHANNEL_ID = int(os.getenv("CONFIG_CHANNEL_ID", "0"))
BRAND_COLOR = int(os.getenv("BRAND_COLOR", "0x2B2D31"), 16)
GUILD_ID = os.getenv("GUILD_ID")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("jr-store-bot")

TEXTS: Dict[str, Dict[str, str]] = {
    "pt": {
        "panel_title": "Jr Store | Configs grátis",
        "panel_description": (
            "Selecione o idioma para abrir o catálogo.\n"
            "As configs são entregues por mensagem privada, com instruções e detalhes organizados."
        ),
        "panel_field_1_name": "Como funciona",
        "panel_field_1_value": (
            "1. Escolha o idioma.\n"
            "2. Selecione o programa.\n"
            "3. Escolha a config.\n"
            "4. Receba tudo no privado."
        ),
        "panel_field_2_name": "Entrega",
        "panel_field_2_value": "Arquivos, códigos e instruções podem ser enviados conforme o item selecionado.",
        "panel_footer": "Jr Store",
        "choose_language": "Selecione o idioma",
        "choose_program": "Selecione o programa",
        "choose_config": "Selecione a config",
        "open_catalog": "Abrir catálogo",
        "language_portuguese": "Português",
        "language_english": "English",
        "program_prompt_title": "Jr Store | Catálogo",
        "program_prompt_description": "Escolha o programa para ver as configs disponíveis.",
        "config_prompt_title": "Jr Store | Selecione a config",
        "config_prompt_description": "Programa selecionado: {program_name}\nAgora escolha a config que deseja receber no privado.",
        "back": "Voltar",
        "delivery_success_public": "A config foi enviada no seu privado.",
        "delivery_failure_public": "Não consegui te enviar mensagem privada. Verifique se sua DM está habilitada para membros do servidor e tente novamente.",
        "delivery_title": "{config_name}",
        "delivery_description": "Entrega automática da Jr Store.",
        "overview": "Visão geral",
        "instructions": "Instruções",
        "binds": "Binds",
        "notes": "Observações",
        "includes": "Conteúdo entregue",
        "support": "Suporte",
        "support_value": "Se precisar de ajuda, abra um ticket no servidor.",
        "private_intro": "Sua entrega está logo abaixo.",
        "code_block_label": "Código",
        "file_sent_label": "Arquivo enviado",
        "published": "Painel publicado em {channel}.",
        "reloaded": "Catálogo recarregado com sucesso.",
        "no_configs": "Nenhuma config foi cadastrada para este programa.",
        "no_programs": "Nenhum programa foi cadastrado no catálogo.",
        "admin_only": "Você precisa da permissão de gerenciar servidor para usar este comando.",
        "error_title": "Erro",
        "catalog_invalid": "O catálogo não pôde ser carregado. Verifique o JSON.",
        "config_not_found": "A config selecionada não foi encontrada.",
        "program_not_found": "O programa selecionado não foi encontrado.",
        "asset_missing": "Um dos arquivos configurados não foi encontrado no servidor.",
    },
    "en": {
        "panel_title": "Jr Store | Free configs",
        "panel_description": (
            "Choose your language to open the catalog.\n"
            "Configs are delivered via direct message with organized instructions and details."
        ),
        "panel_field_1_name": "How it works",
        "panel_field_1_value": (
            "1. Choose your language.\n"
            "2. Select the program.\n"
            "3. Select the config.\n"
            "4. Receive everything in DM."
        ),
        "panel_field_2_name": "Delivery",
        "panel_field_2_value": "Files, codes, and instructions can be delivered depending on the selected item.",
        "panel_footer": "Jr Store",
        "choose_language": "Choose your language",
        "choose_program": "Choose the program",
        "choose_config": "Choose the config",
        "open_catalog": "Open catalog",
        "language_portuguese": "Português",
        "language_english": "English",
        "program_prompt_title": "Jr Store | Catalog",
        "program_prompt_description": "Choose the program to view the available configs.",
        "config_prompt_title": "Jr Store | Select a config",
        "config_prompt_description": "Selected program: {program_name}\nNow choose the config you want to receive in DM.",
        "back": "Back",
        "delivery_success_public": "The config was sent to your DM.",
        "delivery_failure_public": "I could not send you a DM. Please enable direct messages from server members and try again.",
        "delivery_title": "{config_name}",
        "delivery_description": "Automatic delivery by Jr Store.",
        "overview": "Overview",
        "instructions": "Instructions",
        "binds": "Binds",
        "notes": "Notes",
        "includes": "Delivered content",
        "support": "Support",
        "support_value": "If you need help, open a ticket in the server.",
        "private_intro": "Your delivery is right below.",
        "code_block_label": "Code",
        "file_sent_label": "Attached file",
        "published": "Panel published in {channel}.",
        "reloaded": "Catalog reloaded successfully.",
        "no_configs": "No configs were registered for this program.",
        "no_programs": "No programs were registered in the catalog.",
        "admin_only": "You need the Manage Server permission to use this command.",
        "error_title": "Error",
        "catalog_invalid": "The catalog could not be loaded. Please review the JSON file.",
        "config_not_found": "The selected config was not found.",
        "program_not_found": "The selected program was not found.",
        "asset_missing": "One of the configured files was not found on the server.",
    },
}


def t(lang: str, key: str, **kwargs: Any) -> str:
    template = TEXTS.get(lang, TEXTS["en"]).get(key, key)
    return template.format(**kwargs)


def pick_lang(value: Any, lang: str) -> Any:
    if isinstance(value, dict):
        if lang in value:
            return value[lang]
        return value.get("en") or value.get("pt") or ""
    return value


def as_list(value: Any, lang: str) -> List[str]:
    resolved = pick_lang(value, lang)
    if resolved is None:
        return []
    if isinstance(resolved, list):
        return [str(item).strip() for item in resolved if str(item).strip()]
    if isinstance(resolved, str) and resolved.strip():
        return [resolved.strip()]
    return []


def format_lines(items: List[str]) -> str:
    if not items:
        return "—"
    return "\n".join(f"• {item}" for item in items)


def truncate(value: str, limit: int = 1024) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def load_catalog() -> Dict[str, Any]:
    if not CATALOG_PATH.exists():
        return {"items": []}
    with CATALOG_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Catalog root must be an object")
    data.setdefault("items", [])
    return data


class CatalogStore:
    def __init__(self) -> None:
        self.data = load_catalog()

    def reload(self) -> None:
        self.data = load_catalog()

    @property
    def items(self) -> List[Dict[str, Any]]:
        return self.data.get("items", [])

    def get_program(self, program_id: str) -> Optional[Dict[str, Any]]:
        return next((item for item in self.items if item.get("id") == program_id), None)

    def get_config(self, program_id: str, config_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        program = self.get_program(program_id)
        if not program:
            return None, None
        for config in program.get("configs", []):
            if config.get("id") == config_id:
                return program, config
        return program, None


class JrStoreBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.catalog = CatalogStore()

    async def setup_hook(self) -> None:
        self.add_view(LanguagePanelView(self))

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info("Synced %s commands to guild %s", len(synced), GUILD_ID)
        else:
            synced = await self.tree.sync()
            logger.info("Synced %s global commands", len(synced))

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (%s)", self.user, self.user.id if self.user else "unknown")


bot = JrStoreBot()


def build_panel_embed(lang: str = "en") -> discord.Embed:
    embed = discord.Embed(
        title="Jr Store | Free Configs / Configs grátis",
        description=(
            "Choose your language below to open the catalog.\n"
            "Escolha o idioma abaixo para abrir o catálogo."
        ),
        colour=BRAND_COLOR,
    )
    embed.add_field(
        name="How it works / Como funciona",
        value=(
            "1. Choose your language.\n"
            "2. Select the program.\n"
            "3. Select the config.\n"
            "4. Receive everything in DM.\n\n"
            "1. Escolha o idioma.\n"
            "2. Selecione o programa.\n"
            "3. Escolha a config.\n"
            "4. Receba tudo no privado."
        ),
        inline=False,
    )
    embed.add_field(
        name="Delivery / Entrega",
        value=(
            "Files, codes, and instructions may be delivered depending on the selected item.\n"
            "Arquivos, códigos e instruções podem ser enviados conforme o item selecionado."
        ),
        inline=False,
    )
    embed.set_footer(text=BRAND_NAME)
    return embed


def build_program_prompt_embed(lang: str) -> discord.Embed:
    embed = discord.Embed(
        title=t(lang, "program_prompt_title"),
        description=t(lang, "program_prompt_description"),
        colour=BRAND_COLOR,
    )
    embed.set_footer(text=BRAND_NAME)
    return embed


def build_config_prompt_embed(lang: str, program: Dict[str, Any]) -> discord.Embed:
    program_name = pick_lang(program.get("name"), lang) or program.get("id", "Program")
    embed = discord.Embed(
        title=t(lang, "config_prompt_title"),
        description=t(lang, "config_prompt_description", program_name=program_name),
        colour=BRAND_COLOR,
    )
    short_description = pick_lang(program.get("short_description"), lang)
    if short_description:
        embed.add_field(name=t(lang, "overview"), value=truncate(str(short_description), 1024), inline=False)
    embed.set_footer(text=BRAND_NAME)
    return embed


def build_delivery_embed(lang: str, program: Dict[str, Any], config: Dict[str, Any], delivered_assets: List[str]) -> discord.Embed:
    config_name = pick_lang(config.get("name"), lang) or config.get("id", "Config")
    program_name = pick_lang(program.get("name"), lang) or program.get("id", "Program")

    embed = discord.Embed(
        title=t(lang, "delivery_title", config_name=config_name),
        description=t(lang, "delivery_description"),
        colour=BRAND_COLOR,
    )
    embed.set_author(name=BRAND_NAME)
    embed.add_field(
        name=t(lang, "overview"),
        value=truncate(str(pick_lang(config.get("description"), lang) or program_name), 1024),
        inline=False,
    )
    embed.add_field(name=t(lang, "includes"), value=truncate(format_lines(delivered_assets), 1024), inline=False)
    embed.add_field(name=t(lang, "instructions"), value=truncate(format_lines(as_list(config.get("instructions"), lang)), 1024), inline=False)
    embed.add_field(name=t(lang, "binds"), value=truncate(format_lines(as_list(config.get("binds"), lang)), 1024), inline=False)
    embed.add_field(name=t(lang, "notes"), value=truncate(format_lines(as_list(config.get("notes"), lang)), 1024), inline=False)
    embed.add_field(name=t(lang, "support"), value=t(lang, "support_value"), inline=False)

    thumbnail = config.get("thumbnail") or program.get("thumbnail")
    if thumbnail:
        embed.set_thumbnail(url=str(thumbnail))

    embed.set_footer(text=BRAND_NAME)
    return embed


async def deliver_config(user: discord.User | discord.Member, lang: str, program_id: str, config_id: str) -> None:
    program, config = bot.catalog.get_config(program_id, config_id)
    if not program:
        raise ValueError(t(lang, "program_not_found"))
    if not config:
        raise ValueError(t(lang, "config_not_found"))

    delivered_assets: List[str] = []
    outgoing_files: List[discord.File] = []
    text_parts: List[str] = []

    intro = pick_lang(config.get("private_intro"), lang) or t(lang, "private_intro")
    text_parts.append(intro)

    assets = config.get("assets", [])
    for asset in assets:
        asset_type = asset.get("type")
        label = pick_lang(asset.get("label"), lang) or asset_type or "item"

        if asset_type == "file":
            rel_path = asset.get("path")
            if not rel_path:
                raise ValueError(t(lang, "asset_missing"))
            file_path = (DATA_DIR / rel_path).resolve()
            if not file_path.exists() or DATA_DIR.resolve() not in file_path.parents:
                raise ValueError(t(lang, "asset_missing"))
            outgoing_files.append(discord.File(file_path, filename=file_path.name))
            delivered_assets.append(f"{label}: {file_path.name}")

        elif asset_type == "text":
            content = str(pick_lang(asset.get("content"), lang) or "").strip()
            filename = asset.get("filename", "shared_code.txt")
            if not content:
                continue
            if len(content) <= 1800:
                text_parts.append(f"{label}:\n```\n{content}\n```")
            else:
                buffer = io.BytesIO(content.encode("utf-8"))
                outgoing_files.append(discord.File(buffer, filename=filename))
                delivered_assets.append(f"{label}: {filename}")
                text_parts.append(f"{label}: {t(lang, 'file_sent_label')}.")
            if len(content) <= 1800:
                delivered_assets.append(f"{label}: {t(lang, 'code_block_label')}")

    embed = build_delivery_embed(lang, program, config, delivered_assets or ["—"])
    dm = await user.create_dm()
    await dm.send(content="\n\n".join(text_parts), embed=embed, files=outgoing_files)


class LanguagePanelView(discord.ui.View):
    def __init__(self, bot_instance: JrStoreBot):
        super().__init__(timeout=None)
        self.bot_instance = bot_instance

    @discord.ui.button(label="Português", style=discord.ButtonStyle.secondary, custom_id="jrstore:lang:pt")
    async def portuguese(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await send_program_selector(interaction, "pt")

    @discord.ui.button(label="English", style=discord.ButtonStyle.secondary, custom_id="jrstore:lang:en")
    async def english(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await send_program_selector(interaction, "en")


class ProgramSelect(discord.ui.Select):
    def __init__(self, lang: str):
        items = bot.catalog.items[:25]
        options: List[discord.SelectOption] = []
        for item in items:
            label = str(pick_lang(item.get("name"), lang) or item.get("id", "Program"))[:100]
            description = str(pick_lang(item.get("short_description"), lang) or "")[:100] or None
            options.append(discord.SelectOption(label=label, value=item.get("id", label), description=description))

        super().__init__(
            placeholder=t(lang, "choose_program"),
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"jrstore:program:{lang}",
        )
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        program_id = self.values[0]
        program = bot.catalog.get_program(program_id)
        if not program:
            await interaction.response.send_message(t(self.lang, "program_not_found"), ephemeral=True)
            return

        configs = program.get("configs", [])
        if not configs:
            await interaction.response.send_message(t(self.lang, "no_configs"), ephemeral=True)
            return

        view = ConfigSelectView(self.lang, program_id)
        embed = build_config_prompt_embed(self.lang, program)
        await interaction.response.edit_message(embed=embed, view=view)


class ConfigSelect(discord.ui.Select):
    def __init__(self, lang: str, program_id: str):
        program = bot.catalog.get_program(program_id) or {"configs": []}
        configs = program.get("configs", [])[:25]
        options: List[discord.SelectOption] = []
        for config in configs:
            label = str(pick_lang(config.get("name"), lang) or config.get("id", "Config"))[:100]
            description = str(pick_lang(config.get("description"), lang) or "")[:100] or None
            options.append(discord.SelectOption(label=label, value=config.get("id", label), description=description))

        super().__init__(
            placeholder=t(lang, "choose_config"),
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"jrstore:config:{lang}:{program_id}",
        )
        self.lang = lang
        self.program_id = program_id

    async def callback(self, interaction: discord.Interaction) -> None:
        config_id = self.values[0]
        try:
            await deliver_config(interaction.user, self.lang, self.program_id, config_id)
        except discord.Forbidden:
            await interaction.response.send_message(t(self.lang, "delivery_failure_public"), ephemeral=True)
            return
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        except Exception:
            logger.exception("Unexpected error while delivering config")
            await interaction.response.send_message(t(self.lang, "catalog_invalid"), ephemeral=True)
            return

        await interaction.response.send_message(t(self.lang, "delivery_success_public"), ephemeral=True)


class ProgramSelectView(discord.ui.View):
    def __init__(self, lang: str):
        super().__init__(timeout=180)
        self.lang = lang
        if not bot.catalog.items:
            return
        self.add_item(ProgramSelect(lang))


class BackButton(discord.ui.Button):
    def __init__(self, lang: str):
        super().__init__(label=t(lang, "back"), style=discord.ButtonStyle.secondary)
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        await send_program_selector(interaction, self.lang, edit_existing=True)


class ConfigSelectView(discord.ui.View):
    def __init__(self, lang: str, program_id: str):
        super().__init__(timeout=180)
        self.add_item(ConfigSelect(lang, program_id))
        self.add_item(BackButton(lang))


async def send_program_selector(interaction: discord.Interaction, lang: str, edit_existing: bool = False) -> None:
    if not bot.catalog.items:
        message = t(lang, "no_programs")
        if edit_existing:
            await interaction.response.edit_message(content=message, embed=None, view=None)
        else:
            await interaction.response.send_message(message, ephemeral=True)
        return

    embed = build_program_prompt_embed(lang)
    view = ProgramSelectView(lang)

    if edit_existing:
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.tree.command(name="publish_configs", description="Publish the config panel in the configured channel.")
@app_commands.default_permissions(manage_guild=True)
@app_commands.checks.has_permissions(manage_guild=True)
async def publish_configs(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None) -> None:
    target_channel = channel
    if target_channel is None and CONFIG_CHANNEL_ID:
        fetched = interaction.guild.get_channel(CONFIG_CHANNEL_ID) if interaction.guild else None
        if isinstance(fetched, discord.TextChannel):
            target_channel = fetched
    if target_channel is None:
        if isinstance(interaction.channel, discord.TextChannel):
            target_channel = interaction.channel
        else:
            await interaction.response.send_message("No valid text channel was found.", ephemeral=True)
            return

    message = await target_channel.send(embed=build_panel_embed("en"), view=LanguagePanelView(bot))
    try:
        await message.pin(reason=f"{BRAND_NAME} config panel")
    except discord.Forbidden:
        logger.warning("Bot lacks permission to pin messages in %s", target_channel.id)

    await interaction.response.send_message(t("en", "published", channel=target_channel.mention), ephemeral=True)


@bot.tree.command(name="reload_catalog", description="Reload the config catalog from disk.")
@app_commands.default_permissions(manage_guild=True)
@app_commands.checks.has_permissions(manage_guild=True)
async def reload_catalog(interaction: discord.Interaction) -> None:
    try:
        bot.catalog.reload()
    except Exception:
        logger.exception("Failed to reload catalog")
        await interaction.response.send_message(t("en", "catalog_invalid"), ephemeral=True)
        return
    await interaction.response.send_message(t("en", "reloaded"), ephemeral=True)


@publish_configs.error
@reload_catalog.error
async def admin_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        if interaction.response.is_done():
            await interaction.followup.send(t("en", "admin_only"), ephemeral=True)
        else:
            await interaction.response.send_message(t("en", "admin_only"), ephemeral=True)
        return
    logger.exception("App command error", exc_info=error)
    if interaction.response.is_done():
        await interaction.followup.send(t("en", "catalog_invalid"), ephemeral=True)
    else:
        await interaction.response.send_message(t("en", "catalog_invalid"), ephemeral=True)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set.")
    bot.run(token)
