from __future__ import annotations
import json, re
import httpx
from .config import settings

class LLMError(RuntimeError): pass

def chat_json(system: str, user: str, temperature: float = 0.0) -> dict:
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"

    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "stream": False,
        "max_tokens": 768,
        "response_format": {
            "type": "json_object",
        },
        "chat_template_kwargs": {
            "enable_thinking": False,
        },
    }

    try:
        with httpx.Client(timeout=settings.llm_timeout) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        raise LLMError(
            f"Local LLM request failed at {url}: {e}"
        ) from e

    try:
        message = data["choices"][0]["message"]
        content = message.get("content", "")
    except Exception as e:
        raise LLMError(f"Unexpected LLM response: {data}") from e

    if not content:
        print("\n--- FULL LLAMA RESPONSE ---")
        print(json.dumps(data, indent=2))
        print("--- END RESPONSE ---\n")
        raise LLMError("Model returned empty content.")

    try:
        return parse_json(content)
    except Exception:
        print("\n--- RAW MODEL CONTENT ---")
        print(repr(content))
        print("--- END RAW MODEL CONTENT ---\n")

        print("--- FULL MESSAGE OBJECT ---")
        print(json.dumps(message, indent=2))
        print("--- END MESSAGE OBJECT ---\n")

        raise

def parse_json(content: str) -> dict:
    content=content.strip()
    if content.startswith('```'):
        content=re.sub(r'^```(?:json)?\s*','',content)
        content=re.sub(r'\s*```$','',content)
    try: return json.loads(content)
    except json.JSONDecodeError:
        m=re.search(r'\{.*\}',content,re.S)
        if m:
            try:return json.loads(m.group(0))
            except json.JSONDecodeError: pass
        raise LLMError('Model did not return valid JSON.')
