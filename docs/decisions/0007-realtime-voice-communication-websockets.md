# ADR-007: Protocolo para Transmissão de Voz (WebSockets com STT e TTS Nativos em Memória)

## Status
Aceito

## Contexto
A interação por voz contínua (always-listening) requer uma comunicação bi-direcional de baixíssima latência para receber continuamente o streaming de áudio do microfone e enviar os fragmentos sintetizados da voz do assistente.

## Decisão
Decidimos utilizar o protocolo **WebSockets** em `/ws/voice` com a execução do modelo de transcrição **`faster-whisper`** e síntese **`piper-tts`** diretamente em memória no backend Python.

### Principais Motivos da Mudança para Python Nativo:
1. **Transmissão Direta em Memória**: O áudio em PCM bruto recebido pelo WebSocket é convertido diretamente em arrays NumPy no processo Python, sendo passado ao `faster-whisper` sem a necessidade de gravar arquivos temporários em disco ou chamar endpoints HTTP externos.
2. **Síntese de Fala Instantânea**: À medida que os tokens de texto chegam da LLM, o `piper-tts` sintetiza o áudio em memória e envia as mensagens binárias diretamente de volta pelo canal WebSocket.
3. **Redução Drástica de Latência**: A eliminações de pontes HTTP adicionais e serializações intermediárias reduz significativamente o tempo total de resposta (*Time-To-First-Audio*).

## Consequências
* **Positivas**:
  * Arquitetura muito mais enxuta (sem necessidade de rodar contêineres adicionais de Whisper ou Piper).
  * Latência extremamente baixa.
