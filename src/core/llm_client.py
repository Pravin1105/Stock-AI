"""Unified LLM HTTP client supporting OpenAI, Anthropic Claude, Groq, and Google Gemini."""

import json
import re
from typing import Any, Dict, Optional
import httpx
from google import genai
from google.genai import types


class LLMClientError(Exception):
    """Raised when an external LLM provider API call fails."""
    pass


def extract_json_payload(text: str) -> Dict[str, Any]:
    """Robustly parse a JSON object from LLM response text, stripping markdown codeblocks if present."""
    if not text or not text.strip():
        raise ValueError("Received empty response from LLM.")

    clean = text.strip()

    # Strip markdown codeblocks (```json ... ``` or ``` ... ```)
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean)
    if fence_match:
        clean = fence_match.group(1).strip()

    try:
        data = json.loads(clean)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Find the outermost { and }
    start = clean.find("{")
    end = clean.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = clean[start : end + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse valid JSON object from response: {clean[:200]}")


def call_chat_completion(
    provider: str,
    model: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    temperature: float = 0.0,
    timeout: float = 45.0,
) -> str:
    """Dispatches a chat completion call to the specified LLM provider.

    Args:
        provider: 'gemini', 'openai', 'anthropic', or 'groq'.
        model: Model name string.
        api_key: Valid API key for the chosen provider.
        system_prompt: System-level instruction or persona.
        user_prompt: User prompt content.
        json_mode: Whether to enforce valid JSON output format.
        temperature: Sampling temperature.
        timeout: HTTP request timeout in seconds.

    Returns:
        The raw generated string response from the model.

    Raises:
        LLMClientError: On network, authorization, model, or API failures.
    """
    prov = (provider or "gemini").strip().lower()

    if not api_key:
        raise LLMClientError(
            f"No API key provided for {prov}. Please supply a key via BYOK or configure it on the server."
        )

    if prov == "gemini":
        return _call_gemini(
            model=model,
            api_key=api_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=json_mode,
            temperature=temperature,
        )
    elif prov == "openai":
        return _call_openai_compatible(
            endpoint_url="https://api.openai.com/v1/chat/completions",
            provider_name="OpenAI",
            model=model,
            api_key=api_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=json_mode,
            temperature=temperature,
            timeout=timeout,
        )
    elif prov == "groq":
        return _call_openai_compatible(
            endpoint_url="https://api.groq.com/openai/v1/chat/completions",
            provider_name="Groq",
            model=model,
            api_key=api_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=json_mode,
            temperature=temperature,
            timeout=timeout,
        )
    elif prov == "anthropic":
        return _call_anthropic(
            model=model,
            api_key=api_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=json_mode,
            temperature=temperature,
            timeout=timeout,
        )
    else:
        raise LLMClientError(
            f"Unsupported LLM provider '{provider}'. Supported providers are: 'gemini', 'openai', 'anthropic', 'groq'."
        )


def _call_gemini(
    model: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    json_mode: bool,
    temperature: float,
) -> str:
    """Execute Gemini request via Google GenAI SDK."""
    try:
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        if json_mode:
            config.response_mime_type = "application/json"

        candidate_models = [model]
        for fallback_m in ["gemini-2.0-flash", "gemini-1.5-flash"]:
            if fallback_m not in candidate_models:
                candidate_models.append(fallback_m)

        last_err: Optional[Exception] = None
        for m in candidate_models:
            try:
                response = client.models.generate_content(
                    model=m,
                    contents=user_prompt,
                    config=config,
                )
                if response.text:
                    return response.text.strip()
            except Exception as e:
                last_err = e
                continue

        raise LLMClientError(f"Gemini API generation failed across models: {last_err}")
    except Exception as e:
        if isinstance(e, LLMClientError):
            raise
        raise LLMClientError(f"Gemini Client error: {e}") from e


def _call_openai_compatible(
    endpoint_url: str,
    provider_name: str,
    model: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    json_mode: bool,
    temperature: float,
    timeout: float,
) -> str:
    """Execute chat completion for OpenAI and Groq APIs."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    effective_sys = system_prompt
    if json_mode:
        effective_sys += "\n\nCRITICAL: You MUST respond ONLY with a single valid JSON object. Do not wrap in markdown or include conversational text."

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": effective_sys},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }

    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(endpoint_url, headers=headers, json=payload)
    except httpx.TimeoutException:
        raise LLMClientError(f"{provider_name} request timed out after {timeout} seconds.")
    except Exception as err:
        raise LLMClientError(f"{provider_name} network connection error: {err}") from err

    if resp.status_code != 200:
        err_body = resp.text
        try:
            err_json = resp.json()
            if "error" in err_json:
                msg = err_json["error"].get("message", str(err_json["error"]))
                err_body = msg
        except Exception:
            pass

        if resp.status_code == 401:
            raise LLMClientError(f"Invalid API Key for {provider_name} (HTTP 401): {err_body}")
        elif resp.status_code == 429:
            raise LLMClientError(f"Rate limit or quota exceeded for {provider_name} (HTTP 429): {err_body}")
        elif resp.status_code == 404:
            raise LLMClientError(f"Model '{model}' not found or unsupported by {provider_name} (HTTP 404): {err_body}")
        else:
            raise LLMClientError(f"{provider_name} API returned error ({resp.status_code}): {err_body}")

    try:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        if not content:
            raise LLMClientError(f"{provider_name} returned an empty message content.")
        return content.strip()
    except (KeyError, IndexError) as parse_err:
        raise LLMClientError(f"Malformed response payload from {provider_name}: {resp.text}") from parse_err


def _call_anthropic(
    model: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    json_mode: bool,
    temperature: float,
    timeout: float,
) -> str:
    """Execute Claude message generation via Anthropic API."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    effective_sys = system_prompt
    if json_mode:
        effective_sys += "\n\nCRITICAL: Respond strictly with a valid JSON object. Do not include markdown fences, comments, or preamble."

    payload = {
        "model": model,
        "system": effective_sys,
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 4096,
        "temperature": temperature,
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
    except httpx.TimeoutException:
        raise LLMClientError(f"Anthropic request timed out after {timeout} seconds.")
    except Exception as err:
        raise LLMClientError(f"Anthropic network connection error: {err}") from err

    if resp.status_code != 200:
        err_body = resp.text
        try:
            err_json = resp.json()
            if "error" in err_json:
                msg = err_json["error"].get("message", str(err_json["error"]))
                err_body = msg
        except Exception:
            pass

        if resp.status_code == 401:
            raise LLMClientError(f"Invalid API Key for Anthropic Claude (HTTP 401): {err_body}")
        elif resp.status_code == 429:
            raise LLMClientError(f"Rate limit or quota exceeded for Anthropic Claude (HTTP 429): {err_body}")
        elif resp.status_code == 404:
            raise LLMClientError(f"Model '{model}' not found or unsupported by Anthropic (HTTP 404): {err_body}")
        else:
            raise LLMClientError(f"Anthropic API returned error ({resp.status_code}): {err_body}")

    try:
        data = resp.json()
        contents = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        full_text = "".join(contents).strip()
        if not full_text:
            raise LLMClientError("Anthropic returned empty text content.")
        return full_text
    except Exception as parse_err:
        raise LLMClientError(f"Failed to parse Anthropic response: {resp.text}") from parse_err
