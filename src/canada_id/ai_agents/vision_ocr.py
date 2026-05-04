"""Vision OCR Agent for Canada ID (MRZ and Barcode Reading)."""
import base64
import io
import json
import os
from urllib import request, error
from PIL import Image

def _image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 encoded JPEG."""
    if image.mode != "RGB":
        image = image.convert("RGB")
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def extract_text_from_image_ai(image: Image.Image, extraction_type: str = "MRZ") -> str | None:
    """Extract text (MRZ or raw PDF417 data) from an image using Vision LLMs.
    
    Tries OPENROUTER_API_KEY first for multimodal models (e.g. gemini-1.5-pro or claude-3.5-sonnet).
    """
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        # Fallback to returning None so local OCR can take over
        return None

    if extraction_type == "MRZ":
        prompt = (
            "Extract the Machine Readable Zone (MRZ) text from this identity document image. "
            "The MRZ consists of 2 or 3 lines of fixed-width text at the bottom, containing uppercase letters, numbers, and '<' characters. "
            "Return EXACTLY the MRZ text, with no markdown formatting, no backticks, and absolutely no other conversational text. "
            "Preserve line breaks exactly."
        )
    else:
        prompt = (
            "Extract all raw text data encoded or printed on this image. "
            "If it's a barcode, transcribe any visible text associated with it. "
            "Return EXACTLY the extracted text, nothing else."
        )

    base64_img = _image_to_base64(image)
    
    payload = {
        "model": "google/gemini-2.5-pro", # Strong multimodal model on OpenRouter
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_img}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1,
    }

    req = request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=45) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        
        # Cleanup markdown blocks if model ignored instructions
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            if len(lines) > 2:
                content = "\n".join(lines[1:-1]).strip()
        
        return content
    except Exception as e:
        print(f"AI Vision Extraction failed: {e}")
        return None
