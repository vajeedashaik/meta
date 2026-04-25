import os


class LLMBackend:
    def __init__(self, backend: str = "groq", model_name: str = "llama-3.3-70b-versatile"):
        """
        backend: "groq" | "qwen" | "anthropic" | "openai"
        Default: Groq cloud inference — fast, no local GPU needed.
        Pipeline/client is lazy-loaded on first generate() call.
        """
        self.backend = backend
        self.model_name = model_name
        self._pipe = None
        self._client = None

        if backend not in ("groq", "qwen", "anthropic", "openai"):
            raise ValueError(f"Unknown backend: {backend!r}. Choose groq | qwen | anthropic | openai")

    def _get_pipe(self):
        if self._pipe is None:
            from transformers import pipeline
            self._pipe = pipeline("text-generation", model=self.model_name, device_map="auto")
        return self._pipe

    def _get_client(self):
        if self._client is None:
            if self.backend == "groq":
                from groq import Groq
                self._client = Groq(api_key=os.environ["GROQ_API_KEY"])
            elif self.backend == "anthropic":
                import anthropic
                self._client = anthropic.Anthropic()
            elif self.backend == "openai":
                from openai import OpenAI
                self._client = OpenAI()
        return self._client

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 512) -> str:
        if self.backend == "qwen":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            out = self._get_pipe()(messages, max_new_tokens=max_tokens, return_full_text=False)
            return out[0]["generated_text"]

        elif self.backend == "groq":
            resp = self._get_client().chat.completions.create(
                model=self.model_name,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return resp.choices[0].message.content

        elif self.backend == "anthropic":
            msg = self._get_client().messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return msg.content[0].text

        elif self.backend == "openai":
            resp = self._get_client().chat.completions.create(
                model=self.model_name,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return resp.choices[0].message.content
