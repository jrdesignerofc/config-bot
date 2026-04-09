"""
Jr Store — Data
Contém todas as configs, hacks e produtos da loja.
"""

# ─── CORES DO BOT ────────────────────────────────────────────────────────────
COLOR_MAIN    = 0x00D9FF   # Cyan — identidade Jr Store
COLOR_SUCCESS = 0x2ECC71   # Verde
COLOR_ERROR   = 0xE74C3C   # Vermelho
COLOR_WARN    = 0xF0B232   # Amarelo/Ouro
COLOR_DARK    = 0x1E1F22   # Fundo escuro (embeds secundários)

RISK_COLOR = {
    "low":    COLOR_SUCCESS,
    "medium": COLOR_WARN,
    "high":   COLOR_ERROR,
}

# ─── HACKS DISPONÍVEIS ───────────────────────────────────────────────────────
HACKS: dict = {
    "memesense": {
        "name": "Memesense",
        "short_desc": {
            "pt": "Configs para Memesense CS2",
            "en": "Memesense CS2 Configs",
        },
        "how_to_import": {
            "pt": (
                "**1.** Abra o menu do **Memesense**\n"
                "**2.** Vá na aba **Config**\n"
                "**3.** Clique em **Create** → dê um nome\n"
                "**4.** Cole o **Shared Code** abaixo"
            ),
            "en": (
                "**1.** Open the **Memesense** menu\n"
                "**2.** Go to the **Config** tab\n"
                "**3.** Click **Create** → enter a name\n"
                "**4.** Paste the **Shared Code** below"
            ),
        },
        "update_note": {
            "pt": (
                "O pack é atualizado constantemente. Para receber "
                "atualizações, re-insira o mesmo shared code seguindo os passos acima."
            ),
            "en": (
                "The pack is constantly updated. To receive updates, "
                "re-enter the same shared code by following the steps above."
            ),
        },
    }
}

# ─── CONFIGS ─────────────────────────────────────────────────────────────────
CONFIGS: dict = {
    "memesense": [
        {
            "id": "closet",
            "name":       {"pt": "Closet",  "en": "Closet"},
            "short_desc": {
                "pt": "Config super legit com ESP melhorado",
                "en": "Super legit config with improved ESP",
            },
            "description": {
                "pt": (
                    "Config super legit focada em discrição máxima. "
                    "ESP aprimorado que depende de sons e posicionamento para melhores resultados. "
                    "Chams visíveis apenas para inimigos visíveis. "
                    "Ideal para jogar sem levantar suspeitas em qualquer servidor."
                ),
                "en": (
                    "Super legit config focused on maximum discretion. "
                    "Enhanced ESP that relies on sounds and positioning for best results. "
                    "Visible chams only for visible enemies. "
                    "Ideal for playing without raising suspicion on any server."
                ),
            },
            "shared_code": "d5c2848ce27eaf33",
            "file": None,
            "risk": "low",
            "risk_label": {"pt": "Baixo Risco", "en": "Low Risk"},
            "keybinds": [
                {"key": "V / C", "action": {"pt": "3ª Pessoa (Toggle)",     "en": "3rd Person (Toggle)"}},
                {"key": "ALT",   "action": {"pt": "TriggerBot (Segurar)",   "en": "TriggerBot (Hold)"}},
                {"key": "X",     "action": {"pt": "LegitBot ON/OFF",        "en": "LegitBot ON/OFF"}},
                {"key": "M3",    "action": {"pt": "ESP / Chams (Toggle)",   "en": "ESP / Chams (Toggle)"}},
            ],
            "notes": {
                "pt": "SMGs ainda podem precisar de ajuste manual para melhores resultados.",
                "en": "SMGs may still need manual adjustment for best results.",
            },
        },
        {
            "id": "legit",
            "name":       {"pt": "Legit",   "en": "Legit"},
            "short_desc": {
                "pt": "Baixíssima chance de ban por Overwatch",
                "en": "Very low chance of Overwatch ban",
            },
            "description": {
                "pt": (
                    "Config legit com baixíssima chance de ban por Overwatch. "
                    "FOV e smoothness otimizados para uma experiência totalmente natural. "
                    "Latência configurada individualmente para diferentes armas. "
                    "Aim assist estável e aprimorado."
                ),
                "en": (
                    "Legit config with a very low chance of Overwatch ban. "
                    "Optimized FOV and smoothness for a completely natural experience. "
                    "Latency configured individually for different weapons. "
                    "Stable and enhanced aim assist."
                ),
            },
            "shared_code": "e798f3c223f354a6",
            "file": None,
            "risk": "low",
            "risk_label": {"pt": "Baixo Risco", "en": "Low Risk"},
            "keybinds": [
                {"key": "V / C", "action": {"pt": "3ª Pessoa (Toggle)",     "en": "3rd Person (Toggle)"}},
                {"key": "ALT",   "action": {"pt": "TriggerBot (Segurar)",   "en": "TriggerBot (Hold)"}},
                {"key": "X",     "action": {"pt": "LegitBot ON/OFF",        "en": "LegitBot ON/OFF"}},
                {"key": "M3",    "action": {"pt": "ESP / Chams (Toggle)",   "en": "ESP / Chams (Toggle)"}},
            ],
            "notes": {
                "pt": "Evite usar aimkeys (Aimlock) — pode resultar em ban imediato.",
                "en": "Avoid using aimkeys (Aimlock) — may result in an immediate ban.",
            },
        },
        {
            "id": "legitrage",
            "name":       {"pt": "LegitRage (Safe Semi)", "en": "LegitRage (Safe Semi)"},
            "short_desc": {
                "pt": "Semi-rage seguro e não detectado",
                "en": "Safe and undetected semi-rage",
            },
            "description": {
                "pt": (
                    "Semi-rage seguro projetado para manter sua conta protegida. "
                    "Requer pré-mira manual e predição de alvos para melhores resultados. "
                    "FOV levemente baixo — mantenha o crosshair próximo dos alvos. "
                    "Não altere configurações críticas do Legitbot."
                ),
                "en": (
                    "Safe semi-rage designed to keep your account protected. "
                    "Requires manual pre-aiming and target prediction for best results. "
                    "Slightly low FOV — keep your crosshair close to targets. "
                    "Do not change critical Legitbot settings."
                ),
            },
            "shared_code": "95f5d7e2acac9b66",
            "file": None,
            "risk": "medium",
            "risk_label": {"pt": "Risco Médio", "en": "Medium Risk"},
            "keybinds": [
                {"key": "X",   "action": {"pt": "Autofire RAGE (Toggle)",    "en": "Autofire RAGE (Toggle)"}},
                {"key": "M3",  "action": {"pt": "Autowall ON/OFF (Toggle)",  "en": "Autowall ON/OFF (Toggle)"}},
                {"key": "ALT", "action": {"pt": "Override MinDmg (Toggle)",  "en": "MinDmg Override (Toggle)"}},
                {"key": "C",   "action": {"pt": "3ª Pessoa (Toggle)",        "en": "3rd Person (Toggle)"}},
            ],
            "notes": {
                "pt": (
                    "Pré-mire preferencialmente na cabeça e áreas acertáveis. "
                    "Não tente mais de 3-4ks consecutivos."
                ),
                "en": (
                    "Pre-aim preferably at head and hittable areas. "
                    "Do not go for more than 3-4 consecutive kills."
                ),
            },
        },
        {
            "id": "semi",
            "name":       {"pt": "Semi (Use at Own Risk)", "en": "Semi (Use at Own Risk)"},
            "short_desc": {
                "pt": "Semi-rage otimizado — use por sua conta e risco",
                "en": "Optimized semi-rage — use at own risk",
            },
            "description": {
                "pt": (
                    "Config semi-rage com as melhores configurações disponíveis no Memesense. "
                    "Totalmente otimizado, seguro e testado. "
                    "Suporte completo para AWP, Auto, Scout, Deagle e pistolas. "
                    "Bhop habilitado."
                ),
                "en": (
                    "Semi-rage config with the best available Memesense settings. "
                    "Fully optimized, secured and tested. "
                    "Full support for AWP, Auto, Scout, Deagle and pistols. "
                    "Bhop enabled."
                ),
            },
            "shared_code": "36755962085bce23",
            "file": None,
            "risk": "high",
            "risk_label": {"pt": "Use por sua conta e risco", "en": "Use at Own Risk"},
            "keybinds": [
                {"key": "X",   "action": {"pt": "Autofire RAGE (Toggle)",    "en": "Autofire RAGE (Toggle)"}},
                {"key": "M3",  "action": {"pt": "Autowall ON/OFF (Toggle)",  "en": "Autowall ON/OFF (Toggle)"}},
                {"key": "ALT", "action": {"pt": "Override MinDmg (Toggle)",  "en": "MinDmg Override (Toggle)"}},
                {"key": "C",   "action": {"pt": "3ª Pessoa (Toggle)",        "en": "3rd Person (Toggle)"}},
            ],
            "notes": {
                "pt": "Evite usar SSG enquanto semi-raging. Aimtime desativado nesta versão.",
                "en": "Avoid using SSG while semi-raging. Aimtime disabled in this version.",
            },
        },
    ]
}

# ─── PRODUTOS PAGOS ──────────────────────────────────────────────────────────
# Configure via variáveis de ambiente: PRODUCT_PRICE, PAID_ROLE_ID
PRODUCTS: list[dict] = [
    {
        "id":    "hvh_pack_premium",
        "name":  {"pt": "HvH Config Pack Premium", "en": "HvH Premium Config Pack"},
        "description": {
            "pt": (
                "Acesso ao pack premium exclusivo de configs HvH, "
                "incluindo atualizações automáticas e suporte prioritário via ticket."
            ),
            "en": (
                "Access to the exclusive HvH premium config pack, "
                "including automatic updates and priority ticket support."
            ),
        },
        "price":     29.90,   # BRL — sobrescrito por PRODUCT_PRICE no .env
        "emoji":     "⚔️",
    },
]


def get_config(hack_id: str, cfg_id: str) -> dict | None:
    """Retorna um config dict pelo hack e id, ou None se não encontrado."""
    for cfg in CONFIGS.get(hack_id, []):
        if cfg["id"] == cfg_id:
            return cfg
    return None
