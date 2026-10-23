# 🚀 OPEN//BUILD 2026 AI App Starter

Starter template from the **OPEN//BUILD 2026 workshop**, part of the **OSCA Ile-Ife Hacktoberfest** programme by Open Source Community Africa (OSCA), Ile-Ife.

**Theme: AI belongs to everyone.**

This repo gives your team a working head start: an AI chat app that runs an **open-weight model** from Hugging Face with **llama.cpp**, has a **Gradio** interface, and deploys to **Render** with Docker.

## 📅 Key dates
| What | When |
|---|---|
| Challenge | October 25–29, 2026 |
| **Submission deadline** | **Thursday, October 29, 2026, 11:59 PM WAT** |
| Virtual Demo Day (shortlisted teams) | Saturday, October 31, 2026, 4:00 PM WAT |
| Prize pool | ₦150,000 |

Teams must have **exactly two** currently enrolled university students.

## ⚡ Quick start
1. Click **Use this template** to create your own repo, then clone it.
2. Change the three ✏️ spots in [`app.py`](app.py): the model, the `SYSTEM` prompt (your product), and the title/examples.
3. If you change the model, update the ✏️ `ENV` lines in the [`Dockerfile`](Dockerfile) too.
4. Run locally:
   ```bash
   pip install -r requirements.txt
   python app.py        # http://localhost:7860
   ```
5. Push to GitHub, then on Render: **New → Web Service → your repo → Docker → Free → Deploy**.
6. Replace this whole section with your project's details using the template below.

## 🧠 Choosing a model
- Search [huggingface.co/models](https://huggingface.co/models): filter by **Task**, **Parameters**, **GGUF** and **Licence**.
- Use an **Instruct** model, and check the **licence**. Open weights don't automatically mean open source.
- RAM needed ≈ parameters × bytes per parameter (4-bit ≈ 0.5 bytes), plus room for your app.
- Render's free tier has **512 MB RAM** and very little CPU, so only tiny models fit and answers are slow. Use a bigger model on a laptop (`share=True` gives a temporary public link), or record a demo video. The brief accepts a live link, a demo video, or clear run instructions.

## ✅ Submission checklist
- [ ] Project name, team names and universities
- [ ] Problem statement and who it affects
- [ ] What your solution does
- [ ] Public GitHub repo
- [ ] Working demo: live link, demo video, or clear run instructions
- [ ] Model: which one, its role, why you chose it, its limitations
- [ ] README with setup steps and dependencies
- [ ] Acknowledgements: licences, datasets, reused code, AI-assisted work
- [ ] No API keys, passwords or personal data in the repo

## 🏆 Judging (100 points)
| Criterion | Points |
|---|---|
| Problem understanding and usefulness | 25 |
| Working prototype and technical execution | 25 |
| Meaningful use of open or open-weight AI | 20 |
| Creativity and thoughtful design | 15 |
| Open-source practices and documentation | 15 |

Special awards: Best Open-Source Practice, Most Creative Solution, Community Impact. A small project that works and is well documented can beat a big one.

**Build for a world you understand. Make it open.**

---

<!-- ✏️ YOUR PROJECT README STARTS HERE: delete everything above this line -->

# <Project Name>

<One sentence: what your app does.>

**Problem:** <What problem are you solving, and why does it matter?>
**Users:** <Who has this problem, and in what situation?>

## Live demo
<Your Render URL, or a link to a demo video>

## Model
| | |
|---|---|
| Model | [<model name>](<Hugging Face link to the original model>) |
| File | [<GGUF file name>](<Hugging Face link to the GGUF repo>) |
| Licence | <e.g. Apache-2.0> |
| Why | <Why this model? Size, quality, licence, languages...> |
| Role | <What exactly the model does in your app> |

**Limitations:** <Where does it go wrong? Wrong answers, languages, speed, size...>

## How it works
Gradio chat → `respond()` builds system prompt + recent history → llama.cpp runs the GGUF model on CPU → answer streams back.

## Run locally
```bash
git clone https://github.com/<YOUR_NAME>/<REPO>.git
cd <REPO>
pip install -r requirements.txt
python app.py        # http://localhost:7860
```

## Run with Docker
```bash
docker build -t my-ai-app .
docker run -p 7860:7860 my-ai-app
```

## Deploy on Render
New → Web Service → connect this repo → Docker → Free → Deploy.

## Acknowledgements
- <Model> by <author> (<licence>), GGUF by <quantizer>
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python), [Gradio](https://gradio.app)
- <Datasets, reused code, and AI coding assistants you used>

## Team
- <Name>, <University>
- <Name>, <University>

## Licence
MIT
