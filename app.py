import streamlit as st
import json
import os
from PIL import Image
import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

# --- PAGE CONFIG ---
st.set_page_config(page_title="Waste-naija | AI Waste Sorting", page_icon="♻️", layout="centered")

# --- LOAD EXTERNAL CSS ---
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style.css")

# --- UI LANGUAGE DICTIONARY ---
LANG_UI = {
    "English": {"uploader": "Upload a photo of your waste item", "button": "Analyze Waste Item", "spinner": "Analyzing waste..."},
    "Yoruba (Yorùbá)": {"uploader": "Gbé fọ́tò ìtọ̀tì rẹ kalẹ̀", "button": "Ṣàyẹ̀wò Ìtọ̀tì", "spinner": "N ṣe àyẹ̀wò..."},
    "Igbo": {"uploader": "Bulite foto mkpofu gị", "button": "Nyochaa Mkpofu", "spinner": "Na-enyocha..."},
    "Hausa": {"uploader": "Loda hoton sharan ku", "button": "Binciki Sharan", "spinner": "Ana bincike..."},
    "Nigerian Pidgin": {"uploader": "Upload picture of your waste", "button": "Check Dis Waste", "spinner": "E dey check...ан"}
}

with st.sidebar:
    st.image("https://img.icons8.com/color/96/recycle.png", width=70)
    st.markdown("### Settings & Options")
    selected_lang = st.selectbox("🌐 Select Target Output Language", list(LANG_UI.keys()))
    st.markdown("---")
    st.markdown("**Challenge:** OPEN//BUILD 2026")
    st.markdown("**Model:** Qwen2-VL-2B-Instruct")

ui = LANG_UI[selected_lang]

st.title("♻️ Waste-naija")
st.markdown("*AI-powered waste sorting and disposal guidance tailored for Nigeria.*")
st.markdown("---")

# 1. Load Knowledge Base
@st.cache_data
def load_knowledge_base():
    if os.path.exists("final_knowledge_base.json"):
        with open("final_knowledge_base.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

kb_data = load_knowledge_base()
items_db = kb_data.get("items", {})
recyclers_db = kb_data.get("recyclers", {})

# 2. Load Qwen2-VL Model (Cached)
@st.cache_resource
def load_qwen_model():
    model_id = "Qwen/Qwen2-VL-2B-Instruct"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    
    model = Qwen2VLForConditionalGeneration.from_pretrained(model_id, torch_dtype=dtype).to(device)
    processor = AutoProcessor.from_pretrained(model_id)
    return model, processor

with st.spinner("Loading AI model into memory..."):
    model, processor = load_qwen_model()

uploaded_file = st.file_uploader(ui["uploader"], type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Resize large images automatically to speed up CPU inference!
    image = Image.open(uploaded_file).convert("RGB")
    image.thumbnail((512, 512)) 
    st.image(image, caption="Uploaded Waste Item (Optimized)", use_container_width=True)
    
    if st.button(ui["button"]):
        with st.spinner(ui["spinner"]):
            # Single prompt asking Qwen to directly write the localized analysis based on our rules
            prompt_text = f"""
            Analyze this waste item image. 
            Provide classification, safety warnings, NESREA legal context, and proper disposal/recycling instructions.
            CRITICAL INSTRUCTION: Write your entire response strictly in the {selected_lang} language. Keep it concise.
            """

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": prompt_text}
                    ]
                }
            ]
            
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = processor(
                text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt"
            ).to(model.device)
            
            # Limited max_new_tokens to ensure fast generation on CPU
            generated_ids = model.generate(**inputs, max_new_tokens=150)
            prediction = processor.batch_decode(
                [out[len(inp):] for inp, out in zip(inputs.input_ids, generated_ids)], 
                skip_special_tokens=True
            )[0]
            
            st.markdown("---")
            st.subheader(f"🔍 AI Analysis & Guidance ({selected_lang})")
            st.info(prediction)

            # Match keyword for recyclers directory
            pred_lower = prediction.lower()
            matched_key = "general_residual"
            if any(w in pred_lower for w in ["pet", "bottle", "plastic"]):
                matched_key = "pet_bottle"
            elif any(w in pred_lower for w in ["battery", "cell"]):
                matched_key = "battery"

            item_info = items_db.get(matched_key, {})
            recycler_ids = item_info.get('recycler_ids', [])
            
            if recycler_ids:
                st.markdown("#### 📍 Certified Recyclers / Handlers (LAWMA)")
                for r_id in recycler_ids:
                    rec = recyclers_db.get(r_id)
                    if rec:
                        st.success(f"🏢 **{rec.get('name')}**\n\n📍 Address: {rec.get('address')} | 📞 Contact: {rec.get('contact')}")