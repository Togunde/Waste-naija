
import gradio as gr

from src.vision import identify_waste
from src.knowledge_base import get_guidance


def analyze(image):
    if image is None:
        return "Please upload a photo of a waste item."

    try:
        prediction = identify_waste(image)
    except Exception as error:
        print(f"Model error: {error}")
        return (
            "### Analysis unavailable\n"
            "The model request failed. Check your Hugging Face token, "
            "provider access and application logs."
        )

    item = prediction.get("item", "Unidentified item")
    category = prediction.get("category_id", "unknown")
    uncertainty = prediction.get("uncertainty", "Not provided")

    result = [
        "## WasteWise Africa",
        f"**Likely item:** {item}",
        f"**Category:** {category}",
        f"**Uncertainty:** {uncertainty}",
    ]

    if category == "unknown":
        result.append(
            "\nWe could not identify this item confidently. "
            "Try another photo with better lighting."
        )
        return "\n\n".join(result)

    guidance = get_guidance(category)

    if guidance is None:
        result.append(
            "\nNo matching knowledge-base entry was found. "
            "We cannot provide item-specific guidance yet."
        )
        return "\n\n".join(result)

    result.extend([
        "### Preparation",
        guidance.get("preparation", "No preparation guidance recorded."),
        "### General guidance",
        guidance.get("general_advice", "No general guidance recorded."),
    ])

    local_option = guidance.get("local_option")
    if local_option:
        result.append(f"**Verified local option:** {local_option}")
    else:
        result.append(
            "**Local collection:** No local option has been verified yet."
        )

    result.append(
        f"**Source:** {guidance.get('source', 'Not recorded')}"
    )

    verified_date = guidance.get("verified_date")
    if verified_date:
        result.append(f"**Last verified:** {verified_date}")

    return "\n\n".join(result)


demo = gr.Interface(
    fn=analyze,
    inputs=gr.Image(type="pil", label="Upload a waste photo"),
    outputs=gr.Markdown(label="WasteWise results"),
    title="WasteWise Africa ♻️",
    description=(
        "Identify everyday waste and explore guidance from our "
        "curated knowledge base. Local collection options are "
        "only shown when verified."
    ),
    flagging_mode="never",
)

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860)
