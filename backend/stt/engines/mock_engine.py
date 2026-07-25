from backend.stt.base import BaseSTTEngine

class MockSTTEngine(BaseSTTEngine):
    """
    Motor STT Mock para testes rápidos e desenvolvimento offline.
    """

    def __init__(self):
        self.is_loaded = False

    def load_model(self) -> None:
        self.is_loaded = True
        print("🛠️ [STT MOCK] Motor STT de Testes/Mock carregado.")

    def transcribe_pcm(self, pcm_bytes: bytes) -> str:
        print("🛠️ [STT MOCK] Transcrevendo áudio mock...")
        return "Mensagem de teste do motor STT Mock"

    def transcribe_partial_pcm(self, pcm_bytes: bytes) -> str:
        return "Testando..."
