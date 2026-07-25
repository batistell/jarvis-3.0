import sys
import io
import os
import site
import time
import logging
import asyncio
from typing import AsyncGenerator

# Silenciar avisos e verbosidade da biblioteca transformers / huggingface
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

# Registrar DLLs do CUDA (nvidia-cublas, nvidia-cudnn, nvidia-cuda-nvrtc) no PATH/DLL directory no Windows
try:
    for site_pkg in site.getsitepackages():
        nvidia_dir = os.path.join(site_pkg, 'nvidia')
        if os.path.isdir(nvidia_dir):
            for root, dirs, files in os.walk(nvidia_dir):
                if root.endswith('bin'):
                    if hasattr(os, 'add_dll_directory'):
                        try:
                            os.add_dll_directory(root)
                        except Exception:
                            pass
                    os.environ['PATH'] = root + ';' + os.environ.get('PATH', '')
except Exception as e:
    print(f"⚠️ Warning ao carregar DLLs do CUDA no Qwen LLM: {e}")

import ctranslate2
from transformers import AutoTokenizer
from huggingface_hub import snapshot_download
from backend.config import settings
from backend.llm.base import BaseLLMEngine

# Garantir codificação UTF-8 no stdout/stderr no Windows
if hasattr(sys.stdout, 'buffer') and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer') and getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

class NativeQwenEngine(BaseLLMEngine):
    """
    Módulo LLM Nativo Python usando CTranslate2 + Qwen 2.5 3B Instruct.
    Roda 100% em memória no processo Python na VRAM da GPU CUDA, sem precisar do Ollama ou servidor externo.
    """

    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or getattr(settings, "NATIVE_LLM_MODEL", "jncraton/Qwen2.5-3B-Instruct-ct2-int8")
        self.generator: ctranslate2.Generator | None = None
        self.tokenizer = None
        self._is_loading = False

    async def ensure_model_loaded(self) -> bool:
        """Carrega o modelo Qwen 2.5 diretamente na VRAM da GPU em memória no Python."""
        if self.generator is None and not self._is_loading:
            self._is_loading = True
            print("=" * 65)
            print(f"⚡ [NATIVE LLM] Carregando Qwen 2.5 3B Instruct nativo na GPU CUDA ({self.model_id})...")
            print("   Baixando/carregando modelo em memória no processo Python...")
            print("=" * 65, flush=True)

            try:
                # 1. Carregamento instantâneo do cache local se disponível (sem verificações de rede ou barras de progresso)
                try:
                    model_dir = await asyncio.to_thread(
                        snapshot_download, repo_id=self.model_id, local_files_only=True
                    )
                except Exception:
                    print(f"📥 [NATIVE LLM] Baixando modelo '{self.model_id}' do HuggingFace pela primeira vez...")
                    model_dir = await asyncio.to_thread(
                        snapshot_download, repo_id=self.model_id
                    )

                # 2. Carrega Tokenizer e Generator em GPU CUDA (ou CPU fallback)
                try:
                    self.tokenizer = await asyncio.to_thread(
                        AutoTokenizer.from_pretrained, self.model_id, trust_remote_code=True, local_files_only=True, fix_mistral_regex=True
                    )
                except Exception:
                    self.tokenizer = await asyncio.to_thread(
                        AutoTokenizer.from_pretrained, self.model_id, trust_remote_code=True, fix_mistral_regex=True
                    )
                
                device = getattr(settings, "WHISPER_DEVICE", "cuda")
                compute_type = getattr(settings, "WHISPER_COMPUTE_TYPE", "float16")
                
                try:
                    self.generator = ctranslate2.Generator(model_dir, device=device, compute_type=compute_type)
                    print("=" * 65)
                    print(f"🚀 [NATIVE QWEN READY] Qwen 2.5 3B pronto em GPU CUDA!")
                    print("=" * 65, flush=True)
                except Exception as ex:
                    print(f"⚠️ [NATIVE LLM CUDA FALLBACK] CPU int8: {ex}")
                    self.generator = ctranslate2.Generator(model_dir, device="cpu", compute_type="int8")
                    print(f"✅ [NATIVE QWEN READY] Qwen 2.5 3B pronto no CPU fallback!", flush=True)

                return True
            except Exception as e:
                print(f"❌ [NATIVE LLM ERROR] Falha ao carregar Qwen 2.5 nativo: {e}", flush=True)
                return False
            finally:
                self._is_loading = False
        return True

    def _prepare_tokens(self, prompt: str, system_prompt: str | None = None, history: list[dict] | None = None) -> list[str]:
        messages = []
        sys_p = system_prompt or settings.JARVIS_SYSTEM_PROMPT
        messages.append({"role": "system", "content": sys_p})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        tokens = self.tokenizer.convert_ids_to_tokens(self.tokenizer.encode(text))
        return tokens

    async def generate(self, prompt: str, system_prompt: str | None = None, history: list[dict] | None = None) -> str:
        await self.ensure_model_loaded()
        if not self.generator or not self.tokenizer:
            return "Erro: Motor Qwen nativo indisponível."

        tokens = self._prepare_tokens(prompt, system_prompt, history)
        
        results = await asyncio.to_thread(
            self.generator.generate_batch,
            [tokens],
            max_length=256,
            sampling_temperature=0.7
        )
        output_ids = results[0].sequences_ids[0]
        decoded = self.tokenizer.decode(output_ids, skip_special_tokens=True).strip()
        if "assistant\n" in decoded:
            decoded = decoded.split("assistant\n")[-1].strip()
        return decoded

    async def generate_stream(self, prompt: str, system_prompt: str | None = None, history: list[dict] | None = None) -> AsyncGenerator[str, None]:
        await self.ensure_model_loaded()
        if not self.generator or not self.tokenizer:
            yield "Erro: Motor Qwen nativo indisponível."
            return

        tokens = self._prepare_tokens(prompt, system_prompt, history)
        
        # Gerador em streaming token por token
        step_results = self.generator.generate_tokens(
            tokens,
            max_length=256,
            sampling_temperature=0.7
        )

        last_decoded_len = 0
        all_token_ids = []

        for step in step_results:
            token_id = step.token_id
            all_token_ids.append(token_id)
            full_decoded = self.tokenizer.decode(all_token_ids, skip_special_tokens=True)
            clean_decoded = full_decoded.split("assistant\n")[-1] if "assistant\n" in full_decoded else full_decoded
            new_text = clean_decoded[last_decoded_len:]
            if new_text:
                last_decoded_len = len(clean_decoded)
                yield new_text
                await asyncio.sleep(0)

    async def call_tools(self, prompt: str, tools: list[dict], system_prompt: str | None = None) -> dict:
        ans = await self.generate(prompt, system_prompt)
        return {"content": ans, "tool_calls": []}
