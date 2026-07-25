# ADR-004: Escolha do Framework Frontend (React & Vite)

## Status
Aceito

## Contexto
A interface do Jarvis 3.0 precisa ser reativa, fluida, visualmente marcante (estilo HUD futurista escuro) e capaz de interagir de forma performática com a Web Audio API para reprodução de som e gravação de áudio.

## Decisão
Manteremos o uso de **React** com **Vite** e **TypeScript** no frontend.

### Principais Motivos:
1. **Ecossistema & Reactividade**: Facilidade de atualização incremental do estado do chat à medida que os tokens de texto chegam via SSE ou WebSocket.
2. **Web Audio API**: Controle completo de captura de áudio PCM, cálculo RMS de silêncio (VAD) e enfileiramento assíncrono de chunks de som sintetizados pelo backend Python.
3. **Estilo Customizado**: Uso de Custom CSS com variáveis para estética futurista sem o acoplamento de bibliotecas utilitárias genéricas.

## Consequências
* **Positivas**:
  * Experiência de usuário altamente moderna e reativa.
  * Reutilização da estrutura frontend consagrada.
