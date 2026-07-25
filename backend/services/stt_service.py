from backend.stt import STTFactory, BaseSTTEngine

"""
Fachada do Serviço de Reconhecimento de Fala (STT).
Delega chamadas para o motor ativo selecionado na fábrica STTFactory (ex: FasterWhisperEngine).
"""

# Instância singleton do serviço STT ativo
stt_service: BaseSTTEngine = STTFactory.create_engine()
