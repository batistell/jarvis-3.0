# ADR-003: Execução Local de LLM com Ollama Python SDK (Llama 3)

## Status
Aceito

## Contexto
O Jarvis 3.0 é projetado para operar com privacidade total, baixo tempo de resposta e autonomia na rede local doméstica, sem dependência de APIs pagas em nuvem como OpenAI ou Anthropic.

## Decisão
Decidimos utilizar o **Ollama** executando o modelo **Llama 3**, integrado ao backend Python através da biblioteca oficial assíncrona `ollama.AsyncClient`.

### Principais Motivos:
1. **Privacidade & Custo Zero**: Todo o processamento de linguagem natural ocorre na máquina local do usuário.
2. **Suporte a Streaming Assíncrono**: O SDK `ollama.AsyncClient` fornece geradores assíncronos nativos para streaming de tokens.
3. **Function Calling Nativo**: Suporte direto para definição e chamada de ferramentas (automação residencial do Home Assistant).

## Consequências
* **Positivas**:
  * Autonomia total e operação offline.
  * Integração limpa e nativa com o `asyncio` do FastAPI.
* **Negativas**:
  * Exige hardware local adequado (GPU com VRAM suficiente ou CPU moderna) para manter latências de geração satisfatórias.
