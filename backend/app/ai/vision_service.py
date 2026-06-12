"""Vision AI Service — Clavra ProdPilot™
Priority: GPT-4o Vision → Ollama moondream → Ollama llava → basic fallback.
"""
import json
import asyncio
from app.config import settings

VISION_PROMPT = """You are a quality control AI for a garment manufacturing facility.
Analyze the image and return JSON:
{
  "analysis_type": "defect_detection|label_reading|line_photo|equipment_check",
  "findings": ["finding 1", "finding 2"],
  "severity": "critical|major|minor|none",
  "recommendations": ["action 1", "action 2"],
  "defect_rate_estimate": 0.05,
  "confidence": 0.92,
  "summary": "2-sentence human-readable summary"
}
Be specific. Base all findings on visual evidence only."""

OLLAMA_VISION_PROMPT = """You are a quality control AI for a garment manufacturing facility.
Analyze this image carefully. Describe:
1. What you see (fabric, garment, equipment, label, defects, etc.)
2. Any quality issues, defects, or abnormalities visible
3. The overall condition (pass/fail/needs-review)
4. Any recommended actions

Be specific and practical. Focus on manufacturing QC relevance."""

# Vision-capable models to try in order (smallest/fastest first)
OLLAMA_VISION_MODELS = ["moondream:latest", "moondream", "llava:latest", "llava"]


async def analyze_image(image_url: str, image_bytes: bytes | None = None) -> dict:
    """Try OpenAI → Ollama vision models → basic fallback."""

    # ── 1. OpenAI GPT-4o Vision ─────────────────────────────────────────
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}},
                    {"type": "text", "text": VISION_PROMPT},
                ]}],
                response_format={"type": "json_object"},
                max_tokens=800,
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)
            data.setdefault("findings", [])
            data.setdefault("recommendations", [])
            data.setdefault("severity", "info")
            return data
        except Exception:
            pass  # fall through to Ollama

    # ── 2. Ollama local vision models ────────────────────────────────────
    if image_bytes:
        result = await _analyze_with_ollama(image_bytes)
        if result:
            return result

    # ── 3. Basic fallback ────────────────────────────────────────────────
    return {
        "summary": (
            "AI vision analysis is currently unavailable. "
            "To enable: add OpenAI API credits, or run `ollama pull moondream` "
            "to use a free local vision model."
        ),
        "findings": [],
        "severity": "info",
        "recommendations": [
            "Add OpenAI API credits for GPT-4o Vision",
            "Or run: ollama pull moondream  (free local ~1.6 GB)",
        ],
        "confidence": 0,
        "analysis_type": "unavailable",
    }


async def _analyze_with_ollama(image_bytes: bytes) -> dict | None:
    """Try available Ollama vision models. Returns None if none available."""
    # Find the first installed vision model
    model = await _find_ollama_vision_model()
    if not model:
        return None

    try:
        from ollama import AsyncClient
        client = AsyncClient()

        response = await asyncio.wait_for(
            client.chat(
                model=model,
                messages=[{
                    "role": "user",
                    "content": OLLAMA_VISION_PROMPT,
                    "images": [image_bytes],
                }],
            ),
            timeout=60,
        )
        text = response["message"]["content"].strip()

        # Parse into structured format
        return _parse_ollama_response(text, model)

    except asyncio.TimeoutError:
        return None
    except Exception:
        return None


async def _find_ollama_vision_model() -> str | None:
    """Return first available Ollama vision model name, or None."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get("http://localhost:11434/api/tags")
            if r.status_code != 200:
                return None
            installed = {m["name"] for m in r.json().get("models", [])}
        for candidate in OLLAMA_VISION_MODELS:
            if candidate in installed:
                return candidate
        return None
    except Exception:
        return None


def _parse_ollama_response(text: str, model: str) -> dict:
    """Convert free-text Ollama vision output to structured dict."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Build a concise summary from the first 2-3 meaningful sentences
    sentences = []
    for line in lines:
        line = line.lstrip("0123456789.-) *#")
        if len(line) > 20:
            sentences.append(line)
        if len(sentences) >= 2:
            break
    summary = " ".join(sentences[:2]) if sentences else text[:300]

    # Extract findings (numbered or bulleted lines after the first few)
    findings = []
    for line in lines[2:]:
        clean = line.lstrip("0123456789.-) *#").strip()
        if len(clean) > 15 and clean not in findings:
            findings.append(clean)
        if len(findings) >= 5:
            break

    # Detect severity keywords
    text_lower = text.lower()
    if any(w in text_lower for w in ["critical", "severe", "reject", "fail", "defect"]):
        severity = "major"
    elif any(w in text_lower for w in ["minor", "slight", "small", "pass"]):
        severity = "minor"
    else:
        severity = "none"

    return {
        "summary": summary,
        "findings": findings if findings else ["See full analysis above"],
        "severity": severity,
        "recommendations": [
            "Review image with supervisor if defects detected",
            "Document any issues in the quality inspection log",
        ],
        "confidence": 0.75,
        "analysis_type": f"local_vision_{model.split(':')[0]}",
    }
