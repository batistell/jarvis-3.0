from backend.llm import LLMFactory, BaseLLMEngine

"""
Fachada do Serviço de Linguagem (LLM).
Delega chamadas para o motor ativo selecionado na fábrica LLMFactory (ex: OllamaLLMEngine).
"""

# Instância singleton do serviço LLM ativo
llm_service: BaseLLMEngine = LLMFactory.create_engine()
