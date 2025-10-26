import os
import httpx
from typing import Optional, List, Dict


def _provider() -> str:
    return (os.getenv("AI_PROVIDER") or "").strip().lower()


def _default_temperature() -> float:
    try:
        return float(os.getenv("AI_TEMPERATURE", "0.2"))
    except Exception:
        return 0.2


def _default_max_tokens() -> int:
    try:
        return int(os.getenv("AI_MAX_TOKENS", "500"))
    except Exception:
        return 500


async def llm_generate(messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> Optional[str]:
    """Call an external LLM provider (OpenAI or Azure OpenAI) to generate a reply.

    messages: list of {role: "user"|"assistant"|"system", content: str}
    system_prompt: optional system instruction to prepend.

    Returns text content or None if provider not configured/failed.
    """
    prov = _provider()
    temperature = _default_temperature()
    max_tokens = _default_max_tokens()

    msgs = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    msgs.extend(messages or [])

    try:
        if prov in ("openai",):
            api_key = os.getenv("OPENAI_API_KEY")
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            if not api_key:
                return None
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": msgs,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                return (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content")
                )

        if prov in ("azure", "azure_openai"):
            api_key = os.getenv("AZURE_OPENAI_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
            if not (api_key and endpoint and deployment):
                return None
            url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "messages": msgs,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                # Azure returns same schema as OpenAI for chat/completions
                return (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content")
                )
    except Exception:
        return None

    return None