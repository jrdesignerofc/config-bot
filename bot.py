import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CONFIG_CHANNEL_ID = int(os.getenv("CONFIG_CHANNEL_ID"))

def load_configs():
    with open("data/configs.json", "r", encoding="utf-8") as f:
        return json.load(f)["hacks"]

# ─── Views ────────────────────────────────────────────────────────────────────

class ConfigSelect(discord.ui.Select):
    def __init__(self, hack_id: str, hack_data: dict):
        self.hack_id = hack_id
        self.hack_data = hack_data

        options = [
            discord.SelectOption(
                label=cfg["label"],
                value=cfg_id,
                description=cfg["description"]
            )
            for cfg_id, cfg in hack_data["configs"].items()
        ]

        super().__init__(
            placeholder="Escolha a config...",
            options=options,
            custom_id=f"config_select_{hack_id}"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        cfg_id = self.values[0]
        cfg = self.hack_data["configs"][cfg_id]
        hack_type = self.hack_data["type"]

        embed = discord.Embed(
            title=f"{self.hack_data['emoji']} {self.hack_data['label']} — {cfg['label']}",
            color=0x2b2d31
        )
        embed.add_field(name="📋 Descrição", value=cfg["description"], inline=False)
        embed.add_field(name="✏️ Autor", value=cfg["author"], inline=True)
        embed.add_field(name="🔄 Atualizado", value=cfg["updated"], inline=True)
        embed.set_footer(text="Config entregue em privado • Use apenas em servidores HvH")

        try:
            if hack_type == "sharedcode":
                embed.add_field(name="🔑 Shared Code", value=f"```{cfg['code']}```", inline=False)
                await interaction.user.send(embed=embed)

            elif hack_type == "market":
                embed.add_field(name="🛒 Link do Market", value=cfg["url"], inline=False)
                await interaction.user.send(embed=embed)

            elif hack_type == "file":
                file_path = cfg["file"]
                if os.path.exists(file_path):
                    await interaction.user.send(
                        embed=embed,
                        file=discord.File(file_path)
                    )
                else:
                    await interaction.followup.send(
                        "❌ Arquivo não encontrado. Avisa o dono do servidor!",
                        ephemeral=True
                    )
                    return

            await interaction.followup.send(
                "✅ Config enviada no seu privado!",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Não consegui te mandar DM! Ativa as mensagens diretas nas configurações do Discord.",
                ephemeral=True
            )


class HackSelect(discord.ui.Select):
    def __init__(self, hacks: dict):
        options = [
            discord.SelectOption(
                label=data["label"],
                value=hack_id,
                emoji=data["emoji"]
            )
            for hack_id, data in hacks.items()
        ]

        super().__init__(
            placeholder="Escolha o hack...",
            options=options,
            custom_id="hack_select"
        )

    async def callback(self, interaction: discord.Interaction):
        hacks = load_configs()
        hack_id = self.values[0]
        hack_data = hacks[hack_id]

        view = discord.ui.View(timeout=None)
        view.add_item(ConfigSelect(hack_id, hack_data))

        embed = discord.Embed(
            title=f"{hack_data['emoji']} {hack_data['label']}",
            description=f"**{len(hack_data['configs'])} config(s) disponível(is)**\nEscolha qual você quer receber:",
            color=0x2b2d31
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class MainView(discord.ui.View):
    def __init__(self, hacks: dict):
        super().__init__(timeout=None)
        self.add_item(HackSelect(hacks))


# ─── Bot ──────────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot online como {bot.user}")
    await bot.tree.sync()

@bot.tree.command(name="setup_configs", description="Posta a mensagem fixa de configs no canal")
@app_commands.checks.has_permissions(administrator=True)
async def setup_configs(interaction: discord.Interaction):
    hacks = load_configs()

    embed = discord.Embed(
        title="🎮 Configs Free — HvH",
        description=(
            "Bem-vindo às configs gratuitas!\n\n"
            "**Como usar:**\n"
            "1️⃣ Selecione o hack que você usa\n"
            "2️⃣ Escolha a config desejada\n"
            "3️⃣ Receba no seu privado\n\n"
            "⚠️ Configs feitas para **servidores HvH** apenas."
        ),
        color=0x2b2d31
    )

    hack_list = "\n".join(
        f"{data['emoji']} **{data['label']}** — {len(data['configs'])} config(s)"
        for _, data in hacks.items()
    )
    embed.add_field(name="📦 Hacks disponíveis", value=hack_list, inline=False)
    embed.set_footer(text="Configs atualizadas regularmente • Selecione abaixo ↓")

    view = MainView(hacks)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Mensagem postada!", ephemeral=True)


bot.run(TOKEN)
