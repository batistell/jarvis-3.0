# ADR-006: Integração com Home Assistant via REST API Assíncrona (httpx)

## Status
Aceito

## Contexto
Um dos pilares do Jarvis 3.0 é a capacidade de atuar como hub de comando de voz para automação residencial, interagindo com luzes, interruptores e sensores conectados ao Home Assistant em um Raspberry Pi local.

## Decisão
Utilizaremos a capacidade de **Tools / Function Calling** do Llama 3 via `ollama.AsyncClient` acoplada a chamadas HTTP assíncronas enviadas com a biblioteca **`httpx`** para a API REST do Home Assistant.

### Fluxo de Operação:
1. O esquema da ferramenta (ex: `control_home_device`) é fornecido ao Ollama.
2. Quando o usuário pede para controlar um dispositivo, a LLM retorna a instrução de execução da função.
3. O handler Python intercepta o pedido e envia uma requisição `POST` com token de longa duração via `httpx` para `http://<raspberry-pi-ip>:8123/api/services/<domain>/<action>`.
4. O resultado HTTP é devolvido à LLM para gerar a resposta textual de confirmação.

## Consequências
* **Positivas**:
  * Execução assíncrona não-bloqueante no FastAPI.
  * Integração nativa de ferramentas sem acoplamento a frameworks pesados de agentes.
