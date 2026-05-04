"""Synthetic Data Generation Agent for Canadian IDs."""
import json
import os
from urllib import request, error

def generate_synthetic_identity(province_or_doc: str, age_range: str = "25-35", sex: str = "Random") -> dict:
    """Generate a valid, realistic synthetic Canadian identity using LLM API.
    
    Tries OpenRouter first, then Gemini, etc., based on available environment variables.
    """
    prompt = (
        f"Generate a realistic synthetic Canadian identity for {province_or_doc}. "
        f"Age range: {age_range}. Sex: {sex}. "
        "Return ONLY a raw JSON object with NO markdown formatting, NO backticks. "
        "Fields needed: "
        "- surname: Last name (all caps) "
        "- given_names: First and middle names (all caps) "
        "- dob: Date of birth (YYYYMMDD) "
        "- sex: M, F, or X "
        "- address: Realistic street address "
        "- city: Realistic city in that province/country "
        "- province: 2-letter province code (if applicable) "
        "- postal_code: Valid Canadian postal code for that city (format A1A 1A1) "
        "- height: 150-200 "
        "- eyes: BRO, BLU, GRN, HAZ, BLK "
        "- document_number: Realistic ID number format for that province/doc type "
        "- issue_date: YYYYMMDD (recent) "
        "- expiry_date: YYYYMMDD (future, usually 5 years after issue date) "
        "- nationality: CAN"
    )

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        return _call_openrouter(openrouter_key, prompt)

    # Fallback to hardcoded basic generation if no API is available
    return {
        "error": "No API keys configured (OPENROUTER_API_KEY missing). Cannot generate synthetic data."
    }

def _call_openrouter(api_key: str, prompt: str) -> dict:
    payload = {
        "model": "google/gemini-2.5-pro", # Defaulting to a high intelligence model on openrouter, or could use deepseek/deepseek-chat
        "messages": [
            {
                "role": "system",
                "content": "You are a synthetic data generator. Output ONLY raw JSON.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.7,
    }

    req = request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        
        # Cleanup potential markdown around JSON
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        return json.loads(content.strip())
    except Exception as e:
        return {"error": f"API request failed: {e}"}
