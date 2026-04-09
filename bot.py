import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CONFIG_CHANNEL_ID = int(os.getenv("CONFIG_CHANNEL_ID"))

# Cores por nível de risco
RISK_COLORS = {
    "Baixo":  0x57F287,
    "Médio":  0xFEE75C,
    "Alto":   0xED4245,
}

STYLE_ICONS = {
    "Closet / Legit": "◈",
    "Legit":          "◈",
    "Safe Semi":      "◆",
    "Semi-Rage":      "◇",
}

def load_configs():
    with open("data/configs.json", "r", encoding="utf-8") as f:
        return json.load(f)["hacks"]


# ─── DM Embed ─────────────────────────────────────────────────────────────────

def build_dm_embed(hack_label: str, cfg: dict) -> discord.Embed:
    color = RISK_COLORS.get(cfg["risk"], 0x2b2d31)
    icon  = STYLE_ICONS.get(cfg["style"], "◈")

    embed = discord.Embed(
        title=f"{icon}  {cfg['label']}",
        description=cfg["description"],
        color=color
    )

    # Shared code em bloco destacado
    embed.add_field(
        name="Shared Code",
        value=f"```\n{cfg['code']}\n```",
        inline=False
    )

    # Keybinds formatadas
    binds_text = "\n".join(f"  {b}" for b in cfg["keybinds"])
    embed.add_field(
        name="Keybinds",
        value=f"```\n{binds_text}\n```",
        inline=False
    )

    # Como aplicar o shared code
    embed.add_field(
        name="Como aplicar",
        value=(
            "**1.** Abra o Memesense e vá na aba **Config**\n"
            "**2.** Clique em **Create** e dê um nome\n"
            "**3.** Cole o shared code acima\n"
            "**4.** O mesmo código é atualizado automaticamente — "
            "se houver update, basta re-inserir o código"
        ),
        inline=False
    )

    # Notas / aviso
    if cfg.get("notes"):
        embed.add_field(
            name="Notas",
            value=cfg["notes"],
            inline=False
        )

    embed.set_footer(
        text=f"Jr Store  ·  {hack_label}  ·  Risco: {cfg['risk']}  ·  Atualizado em {cfg['updated']}"
    )

    return embed


# ─── Views ────────────────────────────────────────────────────────────────────

class ConfigSelect(discord.ui.Select):
    def __init__(self, hack_id: str, hack_data: dict):
        self.hack_id   = hack_id
        self.hack_data = hack_data

        options = []
        for cfg_id, cfg in hack_data["configs"].items():
            icon = STYLE_ICONS.get(cfg["style"], "◈")
            options.append(
                discord.SelectOption(
                    label=cfg["label"],
                    value=cfg_id,
                    description=f"{cfg['style']}  ·  Risco {cfg['risk']}"
                )
            )

        super().__init__(
            placeholder="Selecione a config...",
            options=options,
            custom_id=f"config_select_{hack_id}"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        cfg_id    = self.values[0]
        cfg       = self.hack_data["configs"][cfg_id]
        hack_type = self.hack_data["type"]

        embed = build_dm_embed(self.hack_data["label"], cfg)

        try:
            await interaction.user.send(embed=embed)
            await interaction.followup.send(
                "Config enviada no seu privado.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "Não foi possível enviar DM. Ative as mensagens diretas nas configurações do Discord.",
                ephemeral=True
            )


class HackSelect(discord.ui.Select):
    def __init__(self, hacks: dict):
        options = [
            discord.SelectOption(
                label=data["label"],
                value=hack_id,
                description=f"{len(data['configs'])} configs disponíveis"
            )
            for hack_id, data in hacks.items()
        ]

        super().__init__(
            placeholder="Selecione o hack...",
            options=options,
            custom_id="hack_select"
        )

    async def callback(self, interaction: discord.Interaction):
        hacks     = load_configs()
        hack_id   = self.values[0]
        hack_data = hacks[hack_id]

        embed = discord.Embed(
            title=hack_data["label"],
            description=f"{len(hack_data['configs'])} configs disponíveis. Selecione abaixo.",
            color=0x2b2d31
        )

        for cfg_id, cfg in hack_data["configs"].items():
            embed.add_field(
                name=f"{STYLE_ICONS.get(cfg['style'], '◈')}  {cfg['label']}",
                value=f"{cfg['style']}  ·  Risco: **{cfg['risk']}**",
                inline=True
            )

        view = discord.ui.View(timeout=None)
        view.add_item(ConfigSelect(hack_id, hack_data))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class MainView(discord.ui.View):
    def __init__(self, hacks: dict):
        super().__init__(timeout=None)
        self.add_item(HackSelect(hacks))


# ─── Bot ──────────────────────────────────────────────────────────────────────

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Online · {bot.user}")
    await bot.tree.sync()


@bot.tree.command(name="setup_configs", description="Posta a mensagem de configs no canal (admin)")
@app_commands.checks.has_permissions(administrator=True)
async def setup_configs(interaction: discord.Interaction):
    hacks = load_configs()

    embed = discord.Embed(
        title="Configs Free",
        description=(
            "Configs gratuitas disponibilizadas pela **Jr Store**.\n\n"
            "Selecione o hack e em seguida a config desejada.\n"
            "A entrega é feita diretamente no seu privado."
        ),
        color=0x2b2d31
    )

    for hack_id, data in hacks.items():
        cfgs = "  ·  ".join(
            f"{STYLE_ICONS.get(c['style'], '◈')} {c['label']}"
            for c in data["configs"].values()
        )
        embed.add_field(
            name=data["label"],
            value=cfgs,
            inline=False
        )

    embed.set_footer(text="Jr Store  ·  Configs atualizadas regularmente")

    view = MainView(hacks)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("Mensagem postada.", ephemeral=True)


bot.run(TOKEN)
