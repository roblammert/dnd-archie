from __future__ import annotations

import json
import re

import httpx

from .config import settings


class LLMError(RuntimeError):
    pass


class LLMContractError(LLMError):
    """
    The server answered, but the model violated the
    structured-output contract.
    """

    pass


def chat_json(
    system: str,
    user: str,
    temperature: float = 0.0,
    *,
    max_tokens: int | None = None,
) -> dict:
    """
    Send one non-streaming JSON-mode request to the local LLM.

    Normal answer generation uses settings.llm_max_tokens.

    Callers that require larger structured responses, such as the
    evidence auditor, may provide a larger max_tokens value.
    """

    url = (
        settings.llm_base_url.rstrip("/")
        + "/chat/completions"
    )

    token_limit = (
        settings.llm_max_tokens
        if max_tokens is None
        else int(max_tokens)
    )

    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": system,
            },
            {
                "role": "user",
                "content": user,
            },
        ],
        "temperature": temperature,
        "stream": False,
        "max_tokens": token_limit,
        "response_format": {
            "type": "json_object",
        },
        "chat_template_kwargs": {
            "enable_thinking": False,
        },
    }

    try:
        with httpx.Client(
            timeout=settings.llm_timeout
        ) as client:
            response = client.post(
                url,
                json=payload,
            )

            response.raise_for_status()

            data = response.json()

    except Exception as exc:
        raise LLMError(
            "Local LLM request failed at "
            f"{url}: {exc}"
        ) from exc

    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
        finish_reason = choice.get(
            "finish_reason"
        )

    except Exception as exc:
        raise LLMError(
            f"Unexpected LLM response: {data}"
        ) from exc

    try:
        return parse_json(content)

    except LLMContractError as exc:
        if finish_reason in {
            "length",
            "max_tokens",
        }:
            raise LLMContractError(
                "Model response hit the output-token "
                "limit before producing valid JSON."
            ) from exc

        raise


def _strip_json_fence(
    content: str,
) -> str:
    """
    Remove a surrounding Markdown code fence without trying
    to repair or reinterpret the JSON itself.
    """

    text = content.strip()

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

    return text.strip()


def _raw_decode_object(
    content: str,
) -> dict | None:
    """
    Find the first independently valid JSON object in otherwise
    noisy model output.

    This is intentionally stricter than the old greedy {.*}
    regular expression. A greedy expression can accidentally
    combine multiple brace-delimited fragments into invalid JSON.
    """

    decoder = json.JSONDecoder()

    for index, char in enumerate(
        content
    ):
        if char != "{":
            continue

        try:
            obj, _ = decoder.raw_decode(
                content[index:]
            )

        except json.JSONDecodeError:
            continue

        if isinstance(obj, dict):
            return obj

    return None


def parse_json(
    content: str,
) -> dict:
    """
    Parse a model response under Archie's structured-output
    contract.

    No semantic repair happens here. The parser only accepts
    JSON that is already structurally valid.
    """

    if not isinstance(
        content,
        str,
    ):
        raise LLMContractError(
            "Model response content is not text."
        )

    text = _strip_json_fence(
        content
    )

    if not text:
        raise LLMContractError(
            "Model returned an empty response."
        )

    try:
        obj = json.loads(
            text
        )

    except json.JSONDecodeError:
        obj = _raw_decode_object(
            text
        )

    if not isinstance(
        obj,
        dict,
    ):
        raise LLMContractError(
            "Model did not return valid JSON."
        )

    return obj
