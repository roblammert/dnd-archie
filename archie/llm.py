from __future__ import annotations
import json, re
import httpx
from .config import settings

class LLMError(RuntimeError):
    pass

class LLMContractError(LLMError):
    """The server answered, but the model violated the structured-output contract."""
    pass


def chat_json(system: str, user: str, temperature: float = 0.0) -> dict:
    url = settings.llm_base_url.rstrip('/') + '/chat/completions'
    payload = {
        'model': settings.llm_model,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
        'temperature': temperature,
        'stream': False,
        'max_tokens': settings.llm_max_tokens,
        'response_format': {'type': 'json_object'},
        'chat_template_kwargs': {'enable_thinking': False},
    }
    try:
        with httpx.Client(timeout=settings.llm_timeout) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        raise LLMError(f"Local LLM request failed at {url}: {e}") from e
    try:
        content = data['choices'][0]['message']['content']
    except Exception as e:
        raise LLMError(f"Unexpected LLM response: {data}") from e
    return parse_json(content)


def parse_json(content: str) -> dict:
    if not isinstance(content,str):
        raise LLMContractError('Model response content is not text.')
    content = content.strip()
    if content.startswith('```'):
        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', content, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        raise LLMContractError('Model did not return valid JSON.')
