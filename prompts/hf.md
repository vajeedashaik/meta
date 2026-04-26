# Switch LLM Backend from Anthropic to HuggingFace Inference API
> Paste this entire prompt into Claude Code. Takes 10 minutes.

---

You are updating the Viral Script Debugging Engine to use HuggingFace Inference API instead of Anthropic API. The Anthropic API key is broken and you need judges to be able to test the environment on HF Spaces.

**Current problem:** Agents are hardcoded to use Anthropic. When judges try to access the HF Space, the API calls fail.

**Solution:** Switch all agents to use HuggingFace Inference API (free tier, you have $30 credits).

**What to change:**

---

## STEP 1: Update `agents/llm_backend.py`

Open this file. Find the line with `def __init__`. Change it from:

```python
def __init__(self, backend: str = "anthropic", model_name: str = "claude-sonnet-4-20250514"):
```

To:

```python
def __init__(self, backend: str = "hf", model_name: str = "meta-llama/Llama-2-7b-chat-hf"):
```

This makes HuggingFace the default instead of Anthropic.

---

## STEP 2: Check the `generate()` method in same file

In the `generate()` method, find the section that says:

```python
elif self.backend == "hf":
```

If it doesn't exist, add this block (it should already exist, but verify):

```python
elif self.backend == "hf":
    full_prompt = f"<s>[INST] {system_prompt}\n\n{user_prompt} [/INST]"
    try:
        response = self.client.text_generation(
            full_prompt,
            max_new_tokens=max_tokens,
            timeout=timeout_seconds
        )
        return response
    except Exception as e:
        raise RuntimeError(f"HF Inference API error: {e}")
```

If the HF section doesn't exist, add it after the anthropic section.

---

## STEP 3: Update `environment/env.py`

Find where the agents are created in the `__init__` method. Look for lines like:

```python
self.critic = CriticAgent()
self.defender = DefenderAgent()
self.rewriter = RewriterAgent()
self.baseline_arbitrator = BaselineArbitratorAgent()
```

Change them to:

```python
self.critic = CriticAgent(backend="hf")
self.defender = DefenderAgent(backend="hf")
self.rewriter = RewriterAgent(backend="hf")
self.baseline_arbitrator = BaselineArbitratorAgent(backend="hf")
```

That's it. Just add `backend="hf"` to each one.

---

## STEP 4: Update `app.py`

In the FastAPI app file, find the place where the environment is instantiated. It might look like:

```python
env = ViralScriptEnv()
```

Or inside the reset function:

```python
@app.post("/reset")
def reset(req: ResetRequest):
    env = ViralScriptEnv(difficulty=req.difficulty)
```

This stays the same — you don't need to change anything here. The backend setting is now inherited from env.py.

---

## STEP 5: Verify `requirements.txt` has HF library

Open `requirements.txt`. Check that it contains:

```
huggingface-hub>=0.17.0
```

If it's not there, add it.

---

## STEP 6: Commit and push to HF Space

In terminal:

```bash
git add agents/llm_backend.py environment/env.py requirements.txt
git commit -m "Switch LLM backend from Anthropic to HuggingFace Inference API"
git push
```

Your HF Space will auto-rebuild. Wait 2-3 minutes.

---

## STEP 7: Test the HF Space

1. Open your HF Space URL in **incognito browser**
2. Add `/health` to the end
3. You should see: `{"status": "ok", "environment": "ViralScriptDebugEngine"}`

If you see that, the Space is working.

---

## STEP 8: Update your Colab notebook

In your Colab, in a cell BEFORE the training starts, add:

```python
import os

# Set your HuggingFace token
os.environ["HF_TOKEN"] = "hf_YOUR_TOKEN_HERE"

# Verify it's set
print(f"HF Token set: {'HF_TOKEN' in os.environ}")
```

Replace `hf_YOUR_TOKEN_HERE` with your actual HF token (from huggingface.co/settings/tokens).

---

## STEP 9: Run training in Colab

Now run your training command:

```python
!python viral_script_engine/training/train_grpo.py \
    --tier easy,medium \
    --steps 30 \
    --model unsloth/Qwen2.5-7B-Instruct-bnb-4bit \
    --output-dir ./trained_model
```

The agents will now use HF Inference API instead of Anthropic.

---

## Verification Checklist

- [ ] `agents/llm_backend.py` has `backend="hf"` as default
- [ ] `environment/env.py` agent instantiation has `backend="hf"` on all 4 agents
- [ ] `app.py` has no changes (stays the same)
- [ ] `requirements.txt` has `huggingface-hub>=0.17.0`
- [ ] Files committed and pushed to HF Space
- [ ] HF Space URL + `/health` works in incognito browser
- [ ] Colab has `os.environ["HF_TOKEN"] = "hf_..."`
- [ ] Training runs without Anthropic API errors

---

## If something breaks:

**Error: "HF_TOKEN not found"**
→ Set the token in Colab: `os.environ["HF_TOKEN"] = "hf_YOUR_TOKEN"`

**Error: "Model not found"**
→ Make sure model name is correct: `meta-llama/Llama-2-7b-chat-hf`

**HF Space still shows errors**
→ Check the Space logs (there's a "Logs" button on the Space page)

**Training is slow**
→ Normal — HF Inference API throttles free tier. You have $30 credits which removes throttling.

---

Done. This takes 10 minutes. After this, judges can test your environment and your Colab training works.