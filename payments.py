"""
Jr Store — Mercado Pago PIX
Funções assíncronas para criar e consultar pagamentos PIX.
"""

import aiohttp
import uuid
import logging
import os
import base64
import io
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("jr_store.payments")

MP_BASE = "https://api.mercadopago.com"


def _headers() -> dict:
    token = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
    return {
        "Authorization":     f"Bearer {token}",
        "Content-Type":      "application/json",
        "X-Idempotency-Key": str(uuid.uuid4()),
    }


async def create_pix_payment(
    amount: float,
    description: str,
    payer_email: str,
    external_reference: str,
) -> dict:
    access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
    if not access_token:
        raise EnvironmentError("Variável MERCADOPAGO_ACCESS_TOKEN não definida.")

    expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=30)
    ).strftime("%Y-%m-%dT%H:%M:%S.000-03:00")

    webhook_url = os.getenv("WEBHOOK_URL", "").strip()

    payload = {
        "transaction_amount": round(float(amount), 2),
        "description":        description,
        "payment_method_id":  "pix",
        "date_of_expiration": expires_at,
        "external_reference": external_reference,
        "payer":              {"email": payer_email},
    }

    # Só inclui notification_url se for uma URL válida
    if webhook_url and webhook_url.startswith("http"):
        payload["notification_url"] = webhook_url

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{MP_BASE}/v1/payments",
            json=payload,
            headers=_headers(),
        ) as resp:
            data = await resp.json()
            if resp.status not in (200, 201):
                msg = data.get("message") or data.get("error", "Erro desconhecido")
                logger.error("MP create_payment error %s: %s", resp.status, data)
                raise RuntimeError(f"Erro ao criar pagamento: {msg}")
            logger.info("Pagamento PIX criado: id=%s ref=%s", data["id"], external_reference)
            return data


async def get_payment(payment_id: int | str) -> dict:
    access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
    headers = {"Authorization": f"Bearer {access_token}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{MP_BASE}/v1/payments/{payment_id}",
            headers=headers,
        ) as resp:
            data = await resp.json()
            if resp.status != 200:
                logger.error("MP get_payment error %s: %s", resp.status, data)
                raise RuntimeError(f"Erro ao consultar pagamento: {data.get('message', '')}")
            return data


def qr_code_to_file(qr_code_base64: str):
    import discord
    raw = base64.b64decode(qr_code_base64)
    buf = io.BytesIO(raw)
    buf.seek(0)
    return discord.File(buf, filename="pix_qrcode.png")


def format_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
