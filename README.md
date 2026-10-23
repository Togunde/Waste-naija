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
