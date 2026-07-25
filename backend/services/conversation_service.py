import time
from typing import Any

class ConversationManager:
    """
    Gerenciador de Memória de Contexto de Conversa e Estado por Sessão.
    Armazena o histórico recente de mensagens (role/content), os metadados
    do último dispositivo/cômodo controlado e intenções pendentes multi-turnos.
    """

    def __init__(self):
        # Mapeamento: session_id -> list[dict[str, str]]
        self._history: dict[str, list[dict[str, str]]] = {}
        # Mapeamento: session_id -> dict com metadados do último dispositivo controlado
        self._last_device: dict[str, dict[str, Any]] = {}
        # Mapeamento: session_id -> dict com intenção pendente aguardando especificação do cômodo
        self._pending_action: dict[str, dict[str, Any]] = {}

    def get_history(self, session_id: str = "default", limit: int = 10) -> list[dict[str, str]]:
        """Retorna o histórico recente de mensagens da sessão para o motor LLM."""
        hist = self._history.get(session_id, [])
        return hist[-limit:]

    def add_user_message(self, session_id: str, content: str) -> None:
        """Registra uma mensagem do usuário no histórico da sessão."""
        if not content:
            return
        if session_id not in self._history:
            self._history[session_id] = []
        self._history[session_id].append({"role": "user", "content": content})
        if len(self._history[session_id]) > 30:
            self._history[session_id] = self._history[session_id][-30:]

    def add_assistant_message(self, session_id: str, content: str) -> None:
        """Registra uma resposta do assistente no histórico da sessão."""
        if not content:
            return
        if session_id not in self._history:
            self._history[session_id] = []
        self._history[session_id].append({"role": "assistant", "content": content})
        if len(self._history[session_id]) > 30:
            self._history[session_id] = self._history[session_id][-30:]

    def set_last_device(
        self,
        session_id: str,
        entity_id: str,
        friendly_name: str,
        target_name: str,
        domain: str = "light"
    ) -> None:
        """
        Registra o último dispositivo acionado/desativado com sucesso no contexto da conversa.
        Grava tanto na sessão específica quanto no fallback 'default'.
        """
        device_data = {
            "entity_id": entity_id,
            "friendly_name": friendly_name,
            "target_name": target_name,
            "domain": domain,
            "timestamp": time.time()
        }
        self._last_device[session_id] = device_data
        self._last_device["default"] = device_data
        print(f"🧠 [CONTEXT MEMORY] Gravado último dispositivo no contexto: '{friendly_name}' ({entity_id})", flush=True)

    def get_last_device(self, session_id: str = "default", max_age_seconds: float = 600.0) -> dict[str, Any] | None:
        """
        Recupera os metadados do último dispositivo manipulado se a sessão for válida e dentro do TTL.
        """
        device = self._last_device.get(session_id)
        if not device:
            device = self._last_device.get("default")

        if not device:
            return None

        if (time.time() - device.get("timestamp", 0)) > max_age_seconds:
            return None

        return device

    def set_pending_action(self, session_id: str, action: str, domain: str = "light") -> None:
        """
        Registra uma ação pendente (ex: turn_off) aguardando a especificação do cômodo no próximo turno.
        """
        action_data = {
            "action": action,
            "domain": domain,
            "timestamp": time.time()
        }
        self._pending_action[session_id] = action_data
        self._pending_action["default"] = action_data
        print(f"⌛ [PENDING INTENT] Gravado comando pendente '{action}' para sessão '{session_id}'", flush=True)

    def get_pending_action(self, session_id: str = "default", max_age_seconds: float = 60.0) -> dict[str, Any] | None:
        """
        Retorna o comando pendente se for solicitado dentro do TTL (60 segundos).
        """
        act = self._pending_action.get(session_id) or self._pending_action.get("default")
        if not act:
            return None

        if (time.time() - act.get("timestamp", 0)) > max_age_seconds:
            return None

        return act

    def clear_pending_action(self, session_id: str = "default") -> None:
        """Limpa o comando pendente após execução ou expiração."""
        self._pending_action.pop(session_id, None)
        self._pending_action.pop("default", None)

conversation_service = ConversationManager()
