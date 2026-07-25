import sys
import io
import json
from typing import AsyncGenerator
from ollama import AsyncClient
from backend.config import settings
from backend.llm.base import BaseLLMEngine

# Garantir UTF-8 no console do Windows
if hasattr(sys.stdout, 'buffer') and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer') and getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

class OllamaLLMEngine(BaseLLMEngine):
    """
    Módulo de Motor LLM utilizando Ollama local (ex: Qwen2.5 3B/7B, Llama 3.2).
    Suporta resposta direta, streaming de áudio/texto e chamada de funções para o Home Assistant.
    """

    def __init__(self, host: str | None = None, model: str | None = None):
        self.host = host or settings.OLLAMA_HOST
        self.model = model or settings.OLLAMA_MODEL
        self.client = AsyncClient(host=self.host)

    async def _try_start_ollama_service(self) -> bool:
        """Tenta iniciar o serviço do Ollama em segundo plano se não estiver rodando."""
        import os
        import subprocess
        import shutil
        import asyncio
        
        ollama_bin = shutil.which("ollama")
        if not ollama_bin:
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            possible_path = os.path.join(local_appdata, "Programs", "Ollama", "ollama.exe")
            if os.path.isfile(possible_path):
                ollama_bin = possible_path

        if ollama_bin:
            try:
                print("⚡ [OLLAMA AUTO-START] Iniciando o serviço Ollama em segundo plano...", flush=True)
                subprocess.Popen([ollama_bin, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                await asyncio.sleep(3.0)
                return True
            except Exception as e:
                print(f"⚠️ [OLLAMA AUTO-START] Não foi possível auto-iniciar Ollama: {e}", flush=True)
        return False

    async def ensure_model_loaded(self) -> bool:
        """
        Verifica se o Ollama está rodando e se o modelo configurado (ex: qwen2.5:3b) está disponível.
        Se o modelo não estiver baixado, faz o download automático em tempo real com progresso no console.
        """
        try:
            models_response = await self.client.list()
        except Exception:
            # Tenta auto-iniciar o serviço do Ollama se falhar na 1ª tentativa
            started = await self._try_start_ollama_service()
            if started:
                try:
                    models_response = await self.client.list()
                except Exception as ex:
                    print(f"⚠️ [OLLAMA HEALTH CHECK] Não foi possível conectar ao Ollama ({self.host}): {ex}", flush=True)
                    return False
            else:
                print(f"⚠️ [OLLAMA HEALTH CHECK] Servidor Ollama não está ativo em {self.host}. Verifique a instalação.", flush=True)
                return False

        try:
            model_names = [m.model for m in models_response.models]
            model_exists = any(self.model in name for name in model_names)
            
            if not model_exists:
                print("=" * 65)
                print(f"⚡ [OLLAMA MODEL AUTO-DOWNLOAD] Modelo '{self.model}' não encontrado localmente.")
                print(f"   Iniciando o download automático do modelo '{self.model}' no Ollama...")
                print("=" * 65, flush=True)
                
                async for progress in await self.client.pull(model=self.model, stream=True):
                    status = progress.get("status", "") if isinstance(progress, dict) else getattr(progress, "status", "")
                    completed = progress.get("completed", 0) if isinstance(progress, dict) else getattr(progress, "completed", 0) or 0
                    total = progress.get("total", 0) if isinstance(progress, dict) else getattr(progress, "total", 0) or 0
                    if total > 0:
                        pct = (completed / total) * 100
                        mb_comp = completed / (1024 * 1024)
                        mb_tot = total / (1024 * 1024)
                        print(f"  ├─ 📥 [OLLAMA PULL] {status}: {pct:.1f}% ({mb_comp:.1f} MB / {mb_tot:.1f} MB)", flush=True)
                    else:
                        print(f"  ├─ 📥 [OLLAMA PULL] {status}", flush=True)
                
                print("=" * 65)
                print(f"🚀 [OLLAMA MODEL READY] Modelo '{self.model}' baixado e pronto em GPU/VRAM!")
                print("=" * 65, flush=True)
            return True
        except Exception as e:
            print(f"⚠️ [OLLAMA DOWNLOAD ERROR] Erro durante o download do modelo: {e}", flush=True)
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[dict] | None = None
    ) -> str:
        """Gera resposta síncrona/completa do Ollama."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                stream=False
            )
            return response.get("message", {}).get("content", "").strip()
        except Exception as e:
            print(f"❌ [OLLAMA ERROR] Erro na geração: {e}")
            return f"Desculpe, ocorreu um erro ao conectar ao modelo {self.model}."

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[dict] | None = None
    ) -> AsyncGenerator[str, None]:
        """Gera resposta token a token em tempo real (Streaming)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        try:
            stream = await self.client.chat(
                model=self.model,
                messages=messages,
                stream=True
            )
            async for chunk in stream:
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
        except Exception as e:
            print(f"❌ [OLLAMA STREAM ERROR] Erro no streaming: {e}")
            yield f"Erro ao comunicar com {self.model}."

    async def call_tools(
        self,
        prompt: str,
        tools: list[dict],
        system_prompt: str | None = None
    ) -> dict:
        """Invocação de chamadas de funções/ferramentas para Home Assistant."""
        messages = []
        sys_p = system_prompt or settings.JARVIS_SYSTEM_PROMPT
        messages.append({"role": "system", "content": sys_p})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                tools=tools
            )
            message = response.get("message", {})
            return {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls", [])
            }
        except Exception as e:
            print(f"❌ [OLLAMA TOOL ERROR] Erro em chamadas de ferramenta: {e}")
            return {"content": "", "tool_calls": []}
