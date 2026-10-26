import base64
import io
import json
import os

from huggingface_hub import InferenceClient


MODEL_ID = "google/gemma-3-4b-it"

CATEGORIES = [
    "plastic_bottle",
    "flexible_plastic",
    "paper_cardboard",
    "metal_can",
    "glass_container",
    "food_waste",
    "unknown",
]


def identify_waste(image):
    token = os.getenv("HF_TOKEN")

    if not token:
        raise RuntimeError(
            "HF_TOKEN is missing. Configure your Hugging Face token."
        )

    # Convert the uploaded image to JPEG bytes.
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    image_url = f"data:image/jpeg;base64,{encoded}"

    client = InferenceClient(
        model=MODEL_ID,
        provider="auto",
        token=token,
    )

    prompt = f"""
Identify the main waste item in this image.

Return only a JSON object with these fields:
{{
  "item": "short description",
  "category_id": "one allowed category",
  "uncertainty": "what is unclear, or none"
}}

Allowed category_id values: {", ".join(CATEGORIES)}

Use unknown if you cannot reasonably identify the item.
Do not decide whether the item is recyclable.
Do not invent disposal instructions or local services.
"""

    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    },
                ],
            }
        ],
        max_tokens=180,
        temperature=0.1,
    )

    text = response.choices[0].message.content

    if not text:
        raise RuntimeError("The model returned an empty response.")

    # Some models wrap JSON in Markdown fences.
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0].strip()

    result = json.loads(cleaned)

    if result.get("category_id") not in CATEGORIES:
        result["category_id"] = "unknown"

    return result
