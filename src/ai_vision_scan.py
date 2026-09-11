"""
src/ai_vision_scan.py - Multimodal AI Vision Inspection Engine (Prompt 18)
==========================================================================
Provides complementary cloud AI visual inspection using vision-capable models:
- Google Gemini 2.5 Flash / Pro (GEMINI_API_KEY)
- OpenAI GPT-4o / GPT-4 Vision (OPENAI_API_KEY)
- Anthropic Claude 3.5 Sonnet (ANTHROPIC_API_KEY)

Returns structured schema:
{
    "is_defective": bool,
    "defect_type": "crack"|"scratch"|"dent"|"stain"|"discoloration"|"dimensional_irregularity"|"none",
    "description": str,
    "confidence": "low"|"medium"|"high",
    "reasoning": str,
    "provider": str,
    "latency_ms": float,
    "status": "success"|"error",
    "error": Optional[str]
}
"""

import os
import sys
import time
import json
import base64
import logging
from typing import Dict, Any, Optional
import urllib.request
import urllib.error

logger = logging.getLogger("DefectInspectionApp.AiVision")

SYSTEM_INSPECTION_PROMPT = """You are a rigorous, highly specialized manufacturing quality assurance vision inspector.
Analyze this manufacturing product image for physical or surface defects.

Allowed defect categories:
- "crack" (micro-fractures, branching cracks, structural breaks)
- "scratch" (linear abrasions, scoring, surface scrapes)
- "dent" (localized 3D surface depressions or impact deformation)
- "stain" (oil, chemical residue, smudges, contamination)
- "discoloration" (thermal oxidation, chemical burning, uneven hue)
- "dimensional_irregularity" (edge deformities, burrs, missing material, chips, geometry distortion)
- "none" (conforming, uniform, defect-free baseline part)

You must respond ONLY in valid JSON matching this exact schema:
{
  "is_defective": boolean,
  "defect_type": "crack" | "scratch" | "dent" | "stain" | "discoloration" | "dimensional_irregularity" | "none",
  "description": "Precise plain-language localization describing where the defect appears (e.g. 'linear scratch across upper-right quadrant approximately 15mm from outer rim')",
  "confidence": "low" | "medium" | "high",
  "reasoning": "Technical explanation of observed surface features, edge integrity, and illumination gradients."
}
Do not wrap your response in markdown formatting or backticks. Return raw valid JSON only."""


def extract_json_safely(raw_text: str) -> Dict[str, Any]:
    """
    Strips markdown code fences (```json ... ```) or prefix text and parses JSON safely.
    """
    clean_text = raw_text.strip()
    if clean_text.startswith("```"):
        lines = clean_text.split("\n")
        # Remove opening fence
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # Remove closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        clean_text = "\n".join(lines).strip()

    # Locate first '{' and last '}' if model included explanatory preamble
    start_idx = clean_text.find("{")
    end_idx = clean_text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        clean_text = clean_text[start_idx : end_idx + 1]

    parsed = json.loads(clean_text)

    # Standardize and validate mandatory keys
    is_def = bool(parsed.get("is_defective", False))
    defect_type = str(parsed.get("defect_type", "none")).lower().strip()
    valid_types = {"crack", "scratch", "dent", "stain", "discoloration", "dimensional_irregularity", "none"}
    if defect_type not in valid_types:
        defect_type = "dimensional_irregularity" if is_def else "none"

    if not is_def:
        defect_type = "none"

    conf = str(parsed.get("confidence", "high")).lower().strip()
    if conf not in {"low", "medium", "high"}:
        conf = "medium"

    return {
        "is_defective": is_def,
        "defect_type": defect_type,
        "description": str(parsed.get("description", "Product surface inspected.")),
        "confidence": conf,
        "reasoning": str(parsed.get("reasoning", "Automated visual assessment complete."))
    }


def call_gemini_vision(image_bytes: bytes, mime_type: str, api_key: str) -> Dict[str, Any]:
    """
    Calls Google Gemini multimodal endpoint using standard HTTP requests.
    Supports Google AI Studio gemini-2.5-flash / gemini-1.5-flash.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    b64_img = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_INSPECTION_PROMPT},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": b64_img
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        candidate = res_data["candidates"][0]["content"]["parts"][0]["text"]
        return extract_json_safely(candidate)


def call_openai_vision(image_bytes: bytes, mime_type: str, api_key: str) -> Dict[str, Any]:
    """
    Calls OpenAI GPT-4o / GPT-4 Vision chat completions endpoint.
    """
    url = "https://api.openai.com/v1/chat/completions"
    b64_img = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64_img}"

    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": SYSTEM_INSPECTION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "high"}
                    }
                ]
            }
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        content = res_data["choices"][0]["message"]["content"]
        return extract_json_safely(content)


def call_claude_vision(image_bytes: bytes, mime_type: str, api_key: str) -> Dict[str, Any]:
    """
    Calls Anthropic Claude 3.5 Sonnet messages endpoint.
    """
    url = "https://api.anthropic.com/v1/messages"
    b64_img = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1024,
        "temperature": 0.1,
        "system": SYSTEM_INSPECTION_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": b64_img
                        }
                    },
                    {
                        "type": "text",
                        "text": "Inspect this part according to the schema. Output JSON only."
                    }
                ]
            }
        ]
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        content = res_data["content"][0]["text"]
        return extract_json_safely(content)


def analyze_with_ai(image_path: str, provider: Optional[str] = None) -> Dict[str, Any]:
    """
    Master function for AI Vision API Scan Mode (Prompt 18).
    Dispatches inspection to the configured multimodal AI vision provider.
    """
    if not provider:
        provider = os.environ.get("AI_VISION_PROVIDER", "gemini").lower()
    else:
        provider = provider.lower()

    # Determine required API key
    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY", "")
    elif provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
    elif provider == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    else:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        provider = "gemini"

    start_t = time.time()

    # Check for missing API credentials
    if not api_key:
        error_msg = f"AI Scan unavailable — check {provider.upper()}_API_KEY in environment or Settings."
        logger.warning("AI Vision scan skipped: missing API key for provider '%s'", provider)
        return {
            "is_defective": False,
            "defect_type": "none",
            "description": "API key missing.",
            "confidence": "low",
            "reasoning": error_msg,
            "provider": provider,
            "latency_ms": 0.0,
            "status": "error",
            "error": error_msg
        }

    # Read image bytes
    if not os.path.exists(image_path):
        return {
            "is_defective": False,
            "defect_type": "none",
            "description": "File not found.",
            "confidence": "low",
            "reasoning": f"Image at {image_path} does not exist.",
            "provider": provider,
            "latency_ms": 0.0,
            "status": "error",
            "error": "Image file not found"
        }

    ext = os.path.splitext(image_path)[1].lower()
    mime_type = "image/png" if ext == ".png" else "image/jpeg"

    try:
        with open(image_path, "rb") as f:
            img_bytes = f.read()

        if provider == "gemini":
            result = call_gemini_vision(img_bytes, mime_type, api_key)
        elif provider == "openai":
            result = call_openai_vision(img_bytes, mime_type, api_key)
        elif provider == "claude":
            result = call_claude_vision(img_bytes, mime_type, api_key)
        else:
            result = call_gemini_vision(img_bytes, mime_type, api_key)

        latency_ms = round((time.time() - start_t) * 1000, 1)

        result["provider"] = provider
        result["latency_ms"] = latency_ms
        result["status"] = "success"
        result["error"] = None

        # Prompt 18: Structured logging
        logger.info(
            "[AI_SCAN] provider=%s is_defective=%s type=%s conf=%s latency=%.1fms status=success",
            provider,
            result["is_defective"],
            result["defect_type"],
            result["confidence"],
            latency_ms
        )
        return result

    except urllib.error.HTTPError as he:
        latency_ms = round((time.time() - start_t) * 1000, 1)
        err_msg = f"HTTP {he.code} from {provider.upper()} API"
        logger.error("[AI_SCAN] provider=%s failed: %s (latency=%.1fms)", provider, err_msg, latency_ms)
        return {
            "is_defective": False,
            "defect_type": "none",
            "description": "AI Vision request failed.",
            "confidence": "low",
            "reasoning": f"{err_msg}. Check API quota or key validity.",
            "provider": provider,
            "latency_ms": latency_ms,
            "status": "error",
            "error": err_msg
        }

    except Exception as e:
        latency_ms = round((time.time() - start_t) * 1000, 1)
        err_msg = str(e)
        logger.exception("[AI_SCAN] provider=%s unexpected exception: %s", provider, err_msg)
        return {
            "is_defective": False,
            "defect_type": "none",
            "description": "AI Vision inference error.",
            "confidence": "low",
            "reasoning": f"Exception occurred during {provider.upper()} vision inspection: {err_msg}",
            "provider": provider,
            "latency_ms": latency_ms,
            "status": "error",
            "error": err_msg
        }
