"""
Router para sincronização em lote de operações offline
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import secrets
import httpx

router = APIRouter()

class SyncItem(BaseModel):
    method: str
    url: str
    data: Optional[Any] = None
    headers: Optional[Dict[str, str]] = None

class BulkPayload(BaseModel):
    requests: List[SyncItem]

@router.post("/bulk")
async def bulk_sync(payload: BulkPayload, request: Request):
    """
    Processa requisições em lote de forma sequencial, respeitando idempotência.
    Cada item deve conter method, url, data e headers opcionais.
    """
    # Preparar cliente ASGI para despachar internamente na própria aplicação
    transport = httpx.ASGITransport(app=request.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://bulk.local") as client:
        results = []
        success = 0
        for item in payload.requests:
            method = (item.method or 'POST').lower()
            url = item.url
            if not isinstance(url, str) or not url.startswith('/'):
                results.append({
                    'ok': False,
                    'status': 400,
                    'url': url,
                    'error': 'URL inválida; deve iniciar com /'
                })
                continue
            headers = dict(item.headers or {})
            if 'X-Idempotency-Key' not in headers:
                headers['X-Idempotency-Key'] = f"bulk-{secrets.token_hex(8)}"
            try:
                resp = await client.request(method, url, json=item.data, headers=headers)
                body_text = resp.text
                # Tentar JSON
                try:
                    body_json = resp.json()
                except Exception:
                    body_json = None
                results.append({
                    'ok': resp.status_code < 400,
                    'status': resp.status_code,
                    'url': url,
                    'method': method.upper(),
                    'body': body_json if body_json is not None else body_text
                })
                if resp.status_code < 400:
                    success += 1
            except Exception as e:
                results.append({
                    'ok': False,
                    'status': 500,
                    'url': url,
                    'error': str(e)
                })
        return {
            'success': success,
            'total': len(payload.requests),
            'results': results
        }