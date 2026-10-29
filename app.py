import os, json, hashlib
import requests
from functools import lru_cache
import streamlit as st
from PIL import Image
import re, difflib, html
from urllib.parse import quote_plus

# ---------------------------------------------------------------- helpers (matching, prompt, links)

# One-line visual hints help a 2B model. Keys that are not listed fall back to the item's display_name,
# so adding an item to the JSON works without touching this file.
VISUAL_HINTS = {
    "pet_bottle": "plastic drinks bottle (water, soft drink, juice) with a screw cap",
    "sachet_water_ldpe": "small soft clear plastic pouch of drinking water, called 'pure water' or sachet nylon",
    "battery": "battery (AA/AAA, button cell, phone or power-bank battery, car or inverter battery)",
    "aluminium_cans": "metal drink can (aluminium can)",
    "food_waste": "food leftovers, cooked food, peels, bones or vegetable scraps",
    "glass_bottle": "glass bottle or glass jar",
    "paper_cardboard": "paper, newspaper or cardboard carton box",
    "e_waste": "old phone, charger, cable, headphones or other electronics",
}
# Words a small VLM tends to say -> item key. Only keys present in the JSON are used.
ALIASES = {
    "pet_bottle": ["pet bottle", "plastic bottle", "water bottle", "drink bottle", "soda bottle", "coke bottle", "bottle of water"],
    "sachet_water_ldpe": ["sachet", "pure water", "water sachet", "sachet water", "nylon", "plastic bag", "plastic pouch", "pouch", "ldpe", "polythene"],
    "battery": ["battery", "batteries", "dry cell", "power bank", "powerbank", "button cell", "car battery", "lithium"],
    "aluminium_cans": ["aluminium can", "aluminum can", "can", "cans", "tin can", "drink can", "soda can", "aluminium", "aluminum"],
    "food_waste": ["food", "leftover", "leftovers", "peel", "peels", "rice", "vegetable", "fruit", "bones", "kitchen waste", "organic"],
    "glass_bottle": ["glass", "glass bottle", "jar", "glass jar", "beer bottle"],
    "paper_cardboard": ["paper", "cardboard", "carton", "newspaper", "box", "carton box"],
    "e_waste": ["phone", "charger", "cable", "electronic", "electronics", "e-waste", "ewaste", "headphones", "laptop", "remote"],
}
NONE_WORDS = {"none", "other", "unknown", "general_residual", "general residual", "residual", "unclear", "none of these", "not sure"}

GENERAL_ITEM = dict(  # shown when nothing matches; uses the SAME keys as the JSON items
    display_name="General / Unidentified Waste", category="Residual Waste", hazard_level="Low", disposal_action="General Waste", eco_points=0,
    composition="Mixed or unclear material.",
    impact_fact="Lagos produces about 11,000 tonnes of waste a day, and only about 8% is recovered (UN-Habitat survey, 2021). Sorting at home is how that changes.",
    preparation_steps=["Pick the closest item from the list below, or take a clearer, closer photo of ONE item.", "Separate recyclables, food waste and hazardous items first.", "Put what is left in a tied bag or lidded bin for your PSP collector."],
    warnings=["Don't burn waste: open burning is an offence in Nigeria.", "Don't dump in drains or gutters."],
    recycler_ids=[], legal_guidance="Households must keep waste in lidded bins or tied bags and separate recyclables (NESREA S.I. 28 of 2009).")

def norm(s):
    return re.sub(r"[^a-z0-9_ ]+", " ", str(s).lower().replace("-", " ")).strip()

def match_label(raw, keys, aliases=ALIASES, cutoff=0.78):
    """Map ANY model string to an item key. Returns (key or None, how). None means 'unsure': the UI then asks the user.
    Order: exact key -> key inside text (token-safe) -> alias phrase -> fuzzy per-word. 'None of these' words -> None."""
    keys = list(keys); text = norm(raw)
    if not text: return None, "empty"
    flat = text.replace(" ", "_")
    if flat in keys: return flat, "exact"
    if text in NONE_WORDS or flat in NONE_WORDS: return None, "model_said_none"
    for k in sorted(keys, key=len, reverse=True):                     # 'This is a pet_bottle.' -> pet_bottle
        if re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", flat): return k, "key_in_text"
    cands = [(a, k) for k in keys for a in aliases.get(k, [])]
    for a, k in sorted(cands, key=lambda x: -len(x[0])):             # longest alias first: 'power bank' before 'bank'
        if re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", text): return k, "alias"
    vocab = {a: k for a, k in cands}
    for w in text.split():                                           # 'batterys', 'sachets', 'aluminum'
        hit = difflib.get_close_matches(w, list(vocab), n=1, cutoff=cutoff)
        if hit: return vocab[hit[0]], "fuzzy"
    return None, "no_match"

def build_mc_prompt(items_db):
    """Multiple-choice prompt built from the JSON keys. Qwen answers with ONE LETTER (one token): fast and easy to parse.
    Returns (prompt, {letter: key_or_None})."""
    letters = "ABCDEFGHIJKLMNOP"; lines, mapping = [], {}
    for i, (k, v) in enumerate(items_db.items()):
        lines.append(f"{letters[i]}. {VISUAL_HINTS.get(k, v.get('display_name', k))}"); mapping[letters[i]] = k
    n = len(lines); lines.append(f"{letters[n]}. none of these / unclear"); mapping[letters[n]] = None
    prompt = ("What is the main waste item in this photo? Choose ONE option and answer with only the letter.\n" + "\n".join(lines) + "\nAnswer:")
    return prompt, mapping

def level_for(points):
    tiers = [(0, "Eco Rookie 🌱"), (50, "Naija Sorter ♻️"), (150, "Eco Warrior 🌍"), (300, "Waste Hero 🏆")]
    cur = max((t for t in tiers if points >= t[0]), key=lambda t: t[0]); nxt = next((t for t in tiers if t[0] > points), None)
    return cur[1], (nxt[0] if nxt else None), (nxt[1] if nxt else None)

def phone_link(contact):
    """First Nigerian phone number in a contact string -> tel: URL (works on phones). None if there is no number."""
    for m in re.finditer(r"\+?\d[\d\s\-]{8,}\d", contact or ""):
        d = re.sub(r"\D", "", m.group(0))
        if d.startswith("234") and len(d) == 13: return "tel:+" + d
        if d.startswith("0") and len(d) == 11 and d[1] in "789": return "tel:+234" + d[1:]
    return None

def maps_url(query): return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query or "")
def esc(x): return html.escape(str(x), quote=True)


DEMO = os.getenv("WASTE_DEMO") == "1"          # no model: pick the item by hand (testing, or a safety net if the model fails on stage)
CONF_MIN = float(os.getenv("WASTE_CONF_MIN", "0.45"))

st.set_page_config(page_title="Waste-Naija | AI Waste Sorting", page_icon="♻️", layout="wide", initial_sidebar_state="collapsed")


# ---------------------------------------------------------------- multilingual interface
# Uses the existing `requests` dependency. If the translation service is unavailable,
# the app safely falls back to the original English text.
LANGUAGES = {
    "English": "en",
    "Hausa": "ha",
    "Yorùbá": "yo",
    "Igbo": "ig",
    "Nigerian Pidgin (beta)": "pcm",
}
language_name = st.selectbox(
    "🌐 Language / Harshe / Èdè / Asụsụ",
    list(LANGUAGES.keys()),
    index=0,
    key="interface_language",
)
TARGET_LANGUAGE = LANGUAGES[language_name]

@lru_cache(maxsize=2048)
def _translate_cached(text, target):
    if not text or target == "en":
        return text
    try:
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "auto", "tl": target, "dt": "t", "q": text},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        translated = "".join(part[0] for part in data[0] if part and part[0])
        return translated or text
    except Exception:
        # Translation is an enhancement, never a reason for the app to stop working.
        return text

def tr(value):
    """Translate a plain user-facing string; preserve the English fallback on failure."""
    if not isinstance(value, str) or TARGET_LANGUAGE == "en":
        return value
    return _translate_cached(value, TARGET_LANGUAGE)

def tr_html(value):
    """Translate visible HTML text only, leaving tags and CSS classes untouched."""
    if not isinstance(value, str) or TARGET_LANGUAGE == "en":
        return value
    parts = re.split(r"(<[^>]+>)", value)
    return "".join(part if part.startswith("<") and part.endswith(">") else tr(part)
                   for part in parts)

# Wrap Streamlit display functions so the existing app UI is translated in place.
# Widget keys/options that drive app logic remain unchanged.
def _wrap_streamlit_text_function(function_name):
    original = getattr(st, function_name, None)
    if original is None:
        return
    def wrapped(*args, **kwargs):
        args = list(args)
        if args and isinstance(args[0], str):
            if function_name == "markdown" and kwargs.get("unsafe_allow_html", False):
                args[0] = tr_html(args[0])
            else:
                args[0] = tr(args[0])
        elif function_name == "tabs" and args and isinstance(args[0], (list, tuple)):
            args[0] = [tr(label) for label in args[0]]
        if isinstance(kwargs.get("text"), str):
            kwargs["text"] = tr(kwargs["text"])
        if callable(kwargs.get("format_func")):
            old_format = kwargs["format_func"]
            kwargs["format_func"] = lambda item: tr(old_format(item))
        return original(*args, **kwargs)
    setattr(st, function_name, wrapped)

for _function_name in (
    "markdown", "title", "header", "subheader", "caption", "write", "text",
    "info", "success", "warning", "error", "exception", "button", "selectbox",
    "radio", "text_input", "text_area", "camera_input", "file_uploader",
    "expander", "tabs", "metric", "progress", "toast", "status"
):
    _wrap_streamlit_text_function(_function_name)

def local_css(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f: st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
local_css("style.css")

# ---------------------------------------------------------------- data
@st.cache_data
def load_knowledge_base():
    if os.path.exists("final_knowledge_base.json"):
        with open("final_knowledge_base.json", "r", encoding="utf-8") as f: return json.load(f)
    return {}
kb = load_knowledge_base(); items_db = kb.get("items", {}); recyclers_db = kb.get("recyclers", {})
if not items_db: st.error("final_knowledge_base.json not found or empty."); st.stop()

# ---------------------------------------------------------------- session state (points persist across reruns)
ss = st.session_state
ss.setdefault("points", 0); ss.setdefault("awarded", {}); ss.setdefault("history", []); ss.setdefault("result", None); ss.setdefault("cache", {})

# ---------------------------------------------------------------- Qwen (classifier only), loaded lazily so the page appears instantly
@st.cache_resource(show_spinner=False)
def load_qwen_model():
    import torch
    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
    model_id = "Qwen/Qwen2-VL-2B-Instruct"
    torch.set_num_threads(os.cpu_count() or 4)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else (torch.bfloat16 if os.getenv("WASTE_BF16") == "1" else torch.float32)   # bf16 halves RAM (needs ~5 GB vs ~9 GB)
    model = Qwen2VLForConditionalGeneration.from_pretrained(model_id, torch_dtype=dtype).to(device).eval()
    # biggest CPU win: cap visual tokens (~256 instead of up to thousands)
    processor = AutoProcessor.from_pretrained(model_id, min_pixels=64 * 28 * 28, max_pixels=256 * 28 * 28)
    return model, processor

def classify_with_qwen(image):
    """One forward pass: read the probabilities of the answer letters A, B, C... No free text to parse."""
    import torch
    from qwen_vl_utils import process_vision_info
    model, processor = load_qwen_model()
    prompt, mapping = build_mc_prompt(items_db)
    messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}]}]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt").to(model.device)
    try:
        with torch.inference_mode():
            logits = model(**inputs).logits[0, -1].float()
        letters = list(mapping)
        ids = [processor.tokenizer.encode(l, add_special_tokens=False)[0] for l in letters]
        probs = torch.softmax(logits[ids], dim=-1).tolist(); best = max(range(len(letters)), key=lambda i: probs[i])
        key = mapping[letters[best]]
        return dict(key=key, conf=probs[best], how="letter_logits", raw=letters[best])
    except Exception:                                                    # fallback: generate a few tokens and parse them robustly
        with torch.inference_mode():
            out = model.generate(**inputs, max_new_tokens=8, do_sample=False)
        raw = processor.batch_decode([o[len(i):] for i, o in zip(inputs.input_ids, out)], skip_special_tokens=True)[0].strip()
        letter = raw[:1].upper(); key = mapping.get(letter) if letter in mapping else match_label(raw, items_db.keys())[0]
        return dict(key=key, conf=0.5 if key else 0.0, how="generate_fallback", raw=raw)

# ---------------------------------------------------------------- header + points strip (visible on mobile, unlike the sidebar)
st.markdown('<div class="hero-section"><h1>♻️ Waste-Naija</h1><p>Snap your waste. Sort it right. Earn eco-points.</p></div>', unsafe_allow_html=True)
top_slot = st.empty()          # filled at the END of the run so it always shows the updated total

def draw_top():
    lvl, nxt_at, nxt_name = level_for(ss.points); pct = 100 if nxt_at is None else min(100, int(100 * ss.points / nxt_at))
    with top_slot.container():
        st.markdown(f'<div class="points-strip"><div><span class="pts">{ss.points}</span><span class="pts-label"> eco-points</span></div><div class="lvl">{esc(lvl)}</div></div>', unsafe_allow_html=True)
        st.progress(pct, text=("Max level reached!" if nxt_at is None else f"{nxt_at - ss.points} points to {nxt_name}"))

def draw_sidebar():
    with st.sidebar:
        st.markdown("### ♻️ Waste-Naija"); st.caption("AI waste sorting for Lagos, Nigeria. OPEN//BUILD 2026.")
        st.metric("Eco-points", ss.points); st.caption(level_for(ss.points)[0])
        with st.expander("How points work"):
            st.markdown("- 🚨 Hazardous (batteries, e-waste): **50**\n- ♻️ Recyclables (bottles, cans, glass, paper): **20**\n- 🍲 Organic / food: **10**\n- 🗑️ General waste: **5**\n\nHazardous waste scores highest because it is the riskiest to get wrong. Each photo scores once.")
        if ss.history: st.markdown("**Recent:** " + ", ".join(ss.history[-5:]))
        if st.button("Reset points", use_container_width=True): ss.points = 0; ss.awarded = {}; ss.history = []; ss.result = None; st.rerun()

# ---------------------------------------------------------------- input: camera first (phones), upload second
col_in, col_out = st.columns([1, 1.5], gap="large")
with col_in:
    with st.container(border=True):
        st.markdown("### 📸 Show us your waste")
        img_file = None; demo_key = None
        if DEMO:
            demo_key = st.selectbox("Demo mode: pick an item", list(items_db), format_func=lambda k: items_db[k]["display_name"], key="demo_item")
        else:
            tab_cam, tab_up = st.tabs(["📷 Take photo", "📁 Upload"])
            with tab_cam: cam = st.camera_input("Take a photo of ONE item", label_visibility="collapsed")
            with tab_up: up = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
            img_file = cam or up
        image = None; img_hash = "demo:" + str(demo_key)
        if img_file is not None:
            raw_bytes = img_file.getvalue(); img_hash = hashlib.md5(raw_bytes).hexdigest()
            image = Image.open(img_file).convert("RGB"); image.thumbnail((512, 512)); st.image(image, use_container_width=True)
        can_run = DEMO or image is not None
        analyze = st.button("🔍 Analyze", use_container_width=True, disabled=not can_run, key="demo_btn" if DEMO else "analyze_btn")
        st.caption("Tip: one item, good light, fill the frame.")

if analyze and can_run:
    if DEMO: ss.result = dict(hash=img_hash, key=demo_key, conf=1.0, how="demo", raw=demo_key)
    elif img_hash in ss.cache: ss.result = ss.cache[img_hash]                      # same photo again: instant
    else:
        with st.status("Loading AI (first time only), then identifying...", expanded=False) as status:
            res = classify_with_qwen(image); res["hash"] = img_hash
            if res["key"] is not None and res["key"] not in items_db: res["key"] = match_label(res["raw"], items_db.keys())[0]
            if res["conf"] < CONF_MIN: res["unsure"] = True
            ss.cache[img_hash] = res; ss.result = res; status.update(label="Done!", state="complete")

# ---------------------------------------------------------------- results
def render_item(item, key):
    haz = item.get("hazard_level", "Low"); hazardous = haz in ("Critical", "High")
    st.markdown(f'<div class="item-head"><div><h2>{esc(item["display_name"])}</h2><span class="chip">{esc(item["category"])}</span><span class="chip chip-action">{esc(item["disposal_action"])}</span></div>'
                f'<div class="points-badge">+{int(item.get("eco_points", 0))}<small>eco-points</small></div></div>', unsafe_allow_html=True)
    if hazardous: st.markdown(f'<div class="hazard-banner">🚨 <b>{esc(haz.upper())} HAZARD:</b> handle with care and keep it away from children.</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="fact-card">💡 <b>Did you know?</b> {esc(item["impact_fact"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="meta-row"><b>Material:</b> {esc(item["composition"])}</div>', unsafe_allow_html=True)
    if item.get("market_value"): st.markdown(f'<div class="value-card">💰 <b>Scrap value:</b> {esc(item["market_value"])}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        steps = "".join(f'<li><span class="n">{i}</span><span>{esc(s)}</span></li>' for i, s in enumerate(item.get("preparation_steps", []), 1))
        st.markdown(f'<div class="steps-card"><h4>✅ How to handle</h4><ol class="steps">{steps}</ol></div>', unsafe_allow_html=True)
    with c2:
        warns = "".join(f'<li>{esc(w)}</li>' for w in item.get("warnings", []))
        st.markdown(f'<div class="warn-card"><h4>❌ What NOT to do</h4><ul>{warns}</ul></div>', unsafe_allow_html=True)
    if item.get("legal_guidance"): st.markdown(f'<div class="legal-card">⚖️ <b>The law:</b> {esc(item["legal_guidance"])}</div>', unsafe_allow_html=True)
    st.markdown("### 📍 Where to take it")
    cards = []
    for rid in item.get("recycler_ids", []):
        rec = recyclers_db.get(rid)
        if not rec: continue
        tel = phone_link(rec.get("contact", ""))
        call = f'<a class="call-btn" href="{esc(tel)}">📞 Call</a>' if tel else ""
        cards.append(f'<div class="recycler-box"><h4>🏢 {esc(rec["name"])}</h4><p>📍 {esc(rec["address"])}<br>📞 {esc(rec["contact"])}</p>'
                     f'<p class="accepts">Accepts: {esc(", ".join(rec.get("accepted_materials", [])))}</p>'
                     f'<div class="btn-row"><a class="map-btn" href="{esc(maps_url(rec["maps_query"]))}" target="_blank" rel="noopener">🗺️ Open in Google Maps</a>{call}</div></div>')
    if cards:
        st.markdown("".join(cards), unsafe_allow_html=True)
        st.caption("⚠️ Details come from the LAWMA register and company profiles and can be out of date. Please call before you travel.")
    else: st.info("No verified drop-off for this item yet. Follow the steps above and use your normal LAWMA/PSP collection.")

with col_out:
    res = ss.result
    if res and (DEMO or res["hash"] == img_hash):
        labels = {k: v["display_name"] for k, v in items_db.items()}; labels["__general__"] = GENERAL_ITEM["display_name"]
        guess = res["key"] if res["key"] in items_db else "__general__"
        if res.get("unsure"): st.warning("I'm not fully sure about this one. Check the match below, or pick the right item.")
        pick = st.selectbox("Not right? Choose the correct item:", list(labels), index=list(labels).index(guess), format_func=lambda k: labels[k], key=f"pick_{res['hash']}")
        item = items_db.get(pick, GENERAL_ITEM)
        with st.container(border=True):
            render_item(item, pick)
        new_pts = int(item.get("eco_points", 0)); old_pts = ss.awarded.get(res["hash"])
        if old_pts is None or (old_pts != new_pts and pick != "__general__"):            # one award per photo; changing the pick swaps it
            ss.points += new_pts - (old_pts or 0); ss.awarded[res["hash"]] = new_pts
            if new_pts > 0:
                ss.history.append(item["display_name"].split(" (")[0])
                st.toast(f"+{new_pts} eco-points! {item['display_name'].split(' (')[0]} sorted", icon="🌱")
                if item["hazard_level"] in ("Critical", "High"): st.balloons()
    else:
        st.markdown('<div class="empty-state"><div class="big">📷</div><h3>Ready when you are</h3><p>Take or upload a photo of one waste item, then tap <b>Analyze</b>.</p></div>', unsafe_allow_html=True)

draw_top(); draw_sidebar()
