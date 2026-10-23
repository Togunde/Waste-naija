import os
import gradio as gr
from llama_cpp import Llama

# ✏️ Pick your model on Hugging Face (a GGUF file that fits your server's RAM)
MODEL_REPO = os.getenv("MODEL_REPO", "bartowski/SmolLM2-360M-Instruct-GGUF")
MODEL_FILE = os.getenv("MODEL_FILE", "SmolLM2-360M-Instruct-Q4_K_M.gguf")

llm = Llama.from_pretrained(repo_id=MODEL_REPO, filename=MODEL_FILE, n_ctx=2048, verbose=False)

# ✏️ This is your product: who the AI is, what it does, and its rules
SYSTEM = """You are Study Buddy, a patient tutor for Nigerian university students.
1. Explain the concept in simple words.
2. Give one everyday example from Nigerian life.
3. End with one short quiz question.
If you are not sure, say "I'm not sure". Only answer study-related questions."""


def respond(message, history):
    # keep the last 3 exchanges so the prompt stays small and fast
    past = [{"role": m["role"], "content": m["content"]} for m in history[-6:]]
    messages = [{"role": "system", "content": SYSTEM}, *past, {"role": "user", "content": message}]

    reply = ""
    for chunk in llm.create_chat_completion(messages=messages, max_tokens=400, temperature=0.3, stream=True):
        reply += chunk["choices"][0]["delta"].get("content", "")
        yield reply


demo = gr.ChatInterface(
    fn=respond,
    type="messages",
    title="📚 Study Buddy",
    description="Ask about any concept you're stuck on. Runs on SmolLM2-360M, an open-weight model.",
    examples=["Explain osmosis simply", "What is demand and supply?", "Explain Ohm's law with an example"],
)

if __name__ == "__main__":
    demo.queue(max_size=20).launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", 7860)))
