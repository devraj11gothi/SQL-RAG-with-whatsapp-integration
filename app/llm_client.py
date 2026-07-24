import requests

from app import config


class LLMConnectionError(Exception):
    pass


def _provider_settings() -> tuple[str, str, dict]:
    if config.LLM_PROVIDER == "gemini":
        return (
            config.GEMINI_BASE_URL,
            config.GEMINI_MODEL,
            {"Authorization": f"Bearer {config.GEMINI_API_KEY}"},
        )
    return config.LMSTUDIO_BASE_URL, config.LMSTUDIO_MODEL, {}


def chat(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
    base_url, model, headers = _provider_settings()
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
            },
            timeout=config.LLM_TIMEOUT_S,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        raise LLMConnectionError(
            f"Could not reach {config.LLM_PROVIDER} at {base_url}: {e}"
        ) from e
