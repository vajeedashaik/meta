import os


class LLMBackend:
    def __init__(self, backend: str = "hf", model_name: str = "meta-llama/Llama-2-7b-chat-hf"):
        """
        backend: "groq" | "qwen" | "anthropic" | "openai" | "hf"
        Default: HuggingFace Inference API — free tier, no local GPU needed.
        Pipeline/client is lazy-loaded on first generate() call.
        """
        self.backend = backend
        self.model_name = model_name
        self._pipe = None
        self._client = None

        if backend not in ("groq", "qwen", "anthropic", "openai", "hf"):
            raise ValueError(f"Unknown backend: {backend!r}. Choose groq | qwen | anthropic | openai | hf")

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
            elif self.backend == "hf":
                from huggingface_hub import InferenceClient
                self._client = InferenceClient(token=os.environ.get("HF_TOKEN"))
        return self._client

    @staticmethod
    def _strip_fences(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            newline = text.find("\n")
            text = text[newline + 1:] if newline != -1 else text[3:]
            if text.endswith("```"):
                text = text[:-3].rstrip()
        return text

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 512, timeout_seconds: int = 30) -> str:
        """
        All LLM calls must complete within timeout_seconds.
        Raises TimeoutError if exceeded — caller handles gracefully.
        """
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._generate_inner, system_prompt, user_prompt, max_tokens)
            try:
                return future.result(timeout=timeout_seconds)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(f"LLM call timed out after {timeout_seconds}s")

    def _generate_inner(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        if self.backend == "qwen":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            out = self._get_pipe()(messages, max_new_tokens=max_tokens, return_full_text=False)
            return self._strip_fences(out[0]["generated_text"])

        elif self.backend == "groq":
            resp = self._get_client().chat.completions.create(
                model=self.model_name,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return self._strip_fences(resp.choices[0].message.content)

        elif self.backend == "anthropic":
            msg = self._get_client().messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return self._strip_fences(msg.content[0].text)

        elif self.backend == "openai":
            resp = self._get_client().chat.completions.create(
                model=self.model_name,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return self._strip_fences(resp.choices[0].message.content)

        elif self.backend == "hf":
            full_prompt = f"<s>[INST] {system_prompt}\n\n{user_prompt} [/INST]"
            try:
                response = self._get_client().text_generation(
                    full_prompt,
                    model=self.model_name,
                    max_new_tokens=max_tokens,
                )
                return self._strip_fences(response)
            except Exception as e:
                raise RuntimeError(f"HF Inference API error: {e}")
