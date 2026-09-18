"""API v1 router aggregator + invitation QR helper."""
from __future__ import annotations

import io
import base64

import qrcode
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from app.api.v1 import admin, auth, debates, misc, users, wallet

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(debates.router)
api_router.include_router(wallet.router)
api_router.include_router(misc.categories_router)
api_router.include_router(misc.notifications_router)
api_router.include_router(misc.disputes_router)
api_router.include_router(misc.games_router)
api_router.include_router(admin.router)


@api_router.get("/invitations/qr", response_class=HTMLResponse, tags=["invitations"])
async def invitation_qr(token: str = Query(...)):
    """Return an inline SVG QR code for an invitation link (§16, §54)."""
    from app.core.config import settings

    url = f"{settings.FRONTEND_URL}/join/{token}"
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return HTMLResponse(
        f'<html><body style="margin:0;display:flex;align-items:center;'
        f'justify-content:center;height:100vh;background:#fff">'
        f'<img src="data:image/png;base64,{b64}" alt="Invitation QR code"/></body></html>'
    )
