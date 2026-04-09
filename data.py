"""
Jr Store — Data
Configs, hacks e produtos persistidos em products_db.json.
"""

import json
import os

# ─── CORES ───────────────────────────────────────────────────────────────────
COLOR_MAIN    = 0x9B59B6
COLOR_SUCCESS = 0x2ECC71
COLOR_ERROR   = 0xE74C3C
COLOR_WARN    = 0xF0B232
COLOR_DARK    = 0x1E1F22

RISK_COLOR = {
    "low":    COLOR_SUCCESS,
    "medium": COLOR_WARN,
    "high":   COLOR_ERROR,
}

# ─── HACKS ───────────────────────────────────────────────────────────────────
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

# ─── CONFIGS (gratuitas) ─────────────────────────────────────────────────────
CONFIGS: dict = {
    "memesense": [
        {
            "id": "closet",
            "name":       {"pt": "Closet",  "en": "Closet"},
            "short_desc": {"pt": "Config super legit com ESP melhorado", "en": "Super legit config with improved ESP"},
            "description": {
                "pt": (
                    "Config super legit focada em discrição máxima. "
                    "ESP aprimorado que depende de sons e posicionamento. "
                    "Chams visíveis apenas para inimigos visíveis."
                ),
                "en": (
                    "Super legit config focused on maximum discretion. "
                    "Enhanced ESP that relies on sounds and positioning. "
                    "Visible chams only for visible enemies."
                ),
            },
            "shared_code": "d5c2848ce27eaf33",
            "file": None,
            "risk": "low",
            "risk_label": {"pt": "Baixo Risco", "en": "Low Risk"},
            "keybinds": [
                {"key": "V / C", "action": {"pt": "3ª Pessoa (Toggle)",   "en": "3rd Person (Toggle)"}},
                {"key": "ALT",   "action": {"pt": "TriggerBot (Segurar)", "en": "TriggerBot (Hold)"}},
                {"key": "X",     "action": {"pt": "LegitBot ON/OFF",      "en": "LegitBot ON/OFF"}},
                {"key": "M3",    "action": {"pt": "ESP / Chams (Toggle)", "en": "ESP / Chams (Toggle)"}},
            ],
            "notes": {"pt": "SMGs ainda podem precisar de ajuste manual.", "en": "SMGs may need manual adjustment."},
        },
        {
            "id": "legit",
            "name":       {"pt": "Legit", "en": "Legit"},
            "short_desc": {"pt": "Baixíssima chance de ban por Overwatch", "en": "Very low chance of Overwatch ban"},
            "description": {
                "pt": (
                    "Config legit com baixíssima chance de ban por Overwatch. "
                    "FOV e smoothness otimizados para experiência natural. "
                    "Latência configurada individualmente por arma."
                ),
                "en": (
                    "Legit config with very low Overwatch ban chance. "
                    "Optimized FOV and smoothness for natural experience. "
                    "Latency configured individually per weapon."
                ),
            },
            "shared_code": "e798f3c223f354a6",
            "file": None,
            "risk": "low",
            "risk_label": {"pt": "Baixo Risco", "en": "Low Risk"},
            "keybinds": [
                {"key": "V / C", "action": {"pt": "3ª Pessoa (Toggle)",   "en": "3rd Person (Toggle)"}},
                {"key": "ALT",   "action": {"pt": "TriggerBot (Segurar)", "en": "TriggerBot (Hold)"}},
                {"key": "X",     "action": {"pt": "LegitBot ON/OFF",      "en": "LegitBot ON/OFF"}},
                {"key": "M3",    "action": {"pt": "ESP / Chams (Toggle)", "en": "ESP / Chams (Toggle)"}},
            ],
            "notes": {"pt": "Evite usar aimkeys (Aimlock).", "en": "Avoid using aimkeys (Aimlock)."},
        },
        {
            "id": "legitrage",
            "name":       {"pt": "LegitRage (Safe Semi)", "en": "LegitRage (Safe Semi)"},
            "short_desc": {"pt": "Semi-rage seguro e não detectado", "en": "Safe and undetected semi-rage"},
            "description": {
                "pt": (
                    "Semi-rage seguro projetado para manter sua conta protegida. "
                    "Requer pré-mira manual e predição de alvos. "
                    "FOV levemente baixo — mantenha o crosshair próximo dos alvos."
                ),
                "en": (
                    "Safe semi-rage designed to protect your account. "
                    "Requires manual pre-aiming and target prediction. "
                    "Slightly low FOV — keep crosshair close to targets."
                ),
            },
            "shared_code": "95f5d7e2acac9b66",
            "file": None,
            "risk": "medium",
            "risk_label": {"pt": "Risco Médio", "en": "Medium Risk"},
            "keybinds": [
                {"key": "X",   "action": {"pt": "Autofire RAGE (Toggle)",   "en": "Autofire RAGE (Toggle)"}},
                {"key": "M3",  "action": {"pt": "Autowall ON/OFF (Toggle)", "en": "Autowall ON/OFF (Toggle)"}},
                {"key": "ALT", "action": {"pt": "Override MinDmg (Toggle)", "en": "MinDmg Override (Toggle)"}},
                {"key": "C",   "action": {"pt": "3ª Pessoa (Toggle)",       "en": "3rd Person (Toggle)"}},
            ],
            "notes": {
                "pt": "Pré-mire na cabeça. Não tente mais de 3-4ks consecutivos.",
                "en": "Pre-aim at head. Do not go for more than 3-4 consecutive kills.",
            },
        },
        {
            "id": "semi",
            "name":       {"pt": "Semi (Use at Own Risk)", "en": "Semi (Use at Own Risk)"},
            "short_desc": {"pt": "Semi-rage otimizado — use por sua conta e risco", "en": "Optimized semi-rage — use at own risk"},
            "description": {
                "pt": (
                    "Config semi-rage com as melhores configurações do Memesense. "
                    "Totalmente otimizado e testado. "
                    "Suporte completo para AWP, Auto, Scout, Deagle e pistolas. Bhop habilitado."
                ),
                "en": (
                    "Semi-rage config with the best Memesense settings. "
                    "Fully optimized and tested. "
                    "Full support for AWP, Auto, Scout, Deagle and pistols. Bhop enabled."
                ),
            },
            "shared_code": "36755962085bce23",
            "file": None,
            "risk": "high",
            "risk_label": {"pt": "Use por sua conta e risco", "en": "Use at Own Risk"},
            "keybinds": [
                {"key": "X",   "action": {"pt": "Autofire RAGE (Toggle)",   "en": "Autofire RAGE (Toggle)"}},
                {"key": "M3",  "action": {"pt": "Autowall ON/OFF (Toggle)", "en": "Autowall ON/OFF (Toggle)"}},
                {"key": "ALT", "action": {"pt": "Override MinDmg (Toggle)", "en": "MinDmg Override (Toggle)"}},
                {"key": "C",   "action": {"pt": "3ª Pessoa (Toggle)",       "en": "3rd Person (Toggle)"}},
            ],
            "notes": {
                "pt": "Evite usar SSG enquanto semi-raging. Aimtime desativado.",
                "en": "Avoid using SSG while semi-raging. Aimtime disabled.",
            },
        },
    ]
}

# ─── PRODUTOS PAGOS ───────────────────────────────────────────────────────────
# Cada produto representa um hack/software.
# Dentro do produto, "packages" define os pacotes vendáveis (configs individuais + pacote completo).
#
# Estrutura de packages:
# {
#   "id": str,            # "closet" | "__full__" etc
#   "label_pt": str,      # nome exibido em pt
#   "label_en": str,
#   "price": float,       # preço DESTE pacote
#   "description_pt": str,
#   "description_en": str,
# }

PRODUCTS_DB_FILE = "products_db.json"

_DEFAULT_PRODUCTS: list[dict] = [
    {
        "id":    "memesense",
        "name":  {"pt": "Memesense — Config Pack", "en": "Memesense — Config Pack"},
        "description": {
            "pt": "Pacotes de configuração premium para Memesense CS2. Escolha uma config individual ou leve o pacote completo.",
            "en": "Premium configuration packages for Memesense CS2. Choose an individual config or get the full pack.",
        },
        "emoji":     "🎯",
        "image_url": None,
        "active":    True,
        # Pacotes disponíveis neste produto
        "packages": [
            {
                "id":             "closet",
                "label_pt":       "Closet",
                "label_en":       "Closet",
                "price":          14.90,
                "description_pt": "Config legit focada em discrição máxima com ESP aprimorado.",
                "description_en": "Legit config focused on maximum discretion with enhanced ESP.",
            },
            {
                "id":             "legit",
                "label_pt":       "Legit",
                "label_en":       "Legit",
                "price":          14.90,
                "description_pt": "Baixíssima chance de ban por Overwatch. FOV e smoothness otimizados.",
                "description_en": "Very low Overwatch ban chance. Optimized FOV and smoothness.",
            },
            {
                "id":             "legitrage",
                "label_pt":       "LegitRage (Safe Semi)",
                "label_en":       "LegitRage (Safe Semi)",
                "price":          19.90,
                "description_pt": "Semi-rage seguro e não detectado. Requer pré-mira manual.",
                "description_en": "Safe and undetected semi-rage. Requires manual pre-aiming.",
            },
            {
                "id":             "semi",
                "label_pt":       "Semi (Use at Own Risk)",
                "label_en":       "Semi (Use at Own Risk)",
                "price":          19.90,
                "description_pt": "Semi-rage otimizado com suporte completo para AWP, Auto, Scout. Bhop habilitado.",
                "description_en": "Optimized semi-rage with full AWP, Auto, Scout support. Bhop enabled.",
            },
            {
                "id":             "__full__",
                "label_pt":       "⭐ Pacote Completo",
                "label_en":       "⭐ Full Package",
                "price":          39.90,
                "description_pt": "Todas as 4 configs + atualizações automáticas + suporte prioritário.",
                "description_en": "All 4 configs + automatic updates + priority support.",
            },
        ],
    },
]


def _load_products() -> list[dict]:
    if os.path.exists(PRODUCTS_DB_FILE):
        try:
            with open(PRODUCTS_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    _save_products(_DEFAULT_PRODUCTS)
    return [dict(p) for p in _DEFAULT_PRODUCTS]


def _save_products(products: list[dict]) -> None:
    with open(PRODUCTS_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


PRODUCTS: list[dict] = _load_products()


def get_products(active_only: bool = False) -> list[dict]:
    products = _load_products()
    if active_only:
        return [p for p in products if p.get("active", True)]
    return products


def save_products(products: list[dict]) -> None:
    _save_products(products)


def get_config(hack_id: str, cfg_id: str) -> dict | None:
    for cfg in CONFIGS.get(hack_id, []):
        if cfg["id"] == cfg_id:
            return cfg
    return None
