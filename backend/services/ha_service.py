import time
import asyncio
import httpx
import unicodedata
import re
from typing import Any
from backend.config import settings
from backend.services.conversation_service import conversation_service

def _normalize_text(text: str) -> str:
    """Remove acentos, converte para minúsculas e remove caracteres especiais."""
    if not text:
        return ""
    nfkd = unicodedata.normalize('NFD', text)
    ascii_text = nfkd.encode('ascii', 'ignore').decode('utf-8')
    return ascii_text.lower().strip()

# Dicionário de Sinônimos e Tradução Português <-> Inglês para Cômodos e Dispositivos
TRANSLATION_MAP: dict[str, list[str]] = {
    "escritorio": ["office", "desk", "study", "workstation"],
    "sala": ["living", "living room", "lounge", "tv room", "estar"],
    "cozinha": ["kitchen", "cook", "dining"],
    "quarto": ["bedroom", "bed room", "room", "master"],
    "quarto principal": ["master bedroom", "master"],
    "banheiro": ["bathroom", "restroom", "bath", "wc", "lavabo"],
    "entrada": ["entrance", "entry", "hall", "foyer", "front"],
    "corredor": ["hallway", "corridor", "passway"],
    "garagem": ["garage"],
    "jardim": ["garden", "yard", "lawn", "outdoor"],
    "quintal": ["backyard", "yard"],
    "varanda": ["balcony", "patio", "porch", "veranda"],
    "sacada": ["balcony"],
    "lavanderia": ["laundry", "utility"],
    "teto": ["ceiling"],
    "parede": ["wall"],
}

# Domínios válidos para controle de iluminação/dispositivos (exclui estritamente button, sensor, automation, etc.)
ALLOWED_DEVICE_DOMAINS = {"light", "switch", "group", "fan", "climate"}

# Pronomes e termos anafóricos que referenciam o último dispositivo do contexto
ANAPHORA_PRONOUNS = {
    "", "ela", "ele", "elas", "eles", "isso", "essa", "este", "esta", "a luz", "o dispositivo",
    "a lampada", "lampada", "luz", "novo", "de novo", "mesmo", "mesma"
}

class HAService:
    """
    Serviço de integração assíncrono com a API REST do Home Assistant.
    Fornece pré-carregamento de entidades na inicialização, resolução inteligente por nome
    (com tradução PT-BR <-> EN), resolução de anáforas (memória de contexto de conversa)
    e controle de dispositivos com validação de feedback de sensores/estados.
    """

    def __init__(self, ha_url: str | None = None, ha_token: str | None = None):
        raw_url = (ha_url if ha_url is not None else settings.HA_URL).rstrip("/")
        if raw_url.endswith("/api"):
            raw_url = raw_url[:-4].rstrip("/")
        self._url = raw_url
        self._token = settings.HA_TOKEN if ha_token is None else ha_token

        # Cache de entidades pré-carregadas
        self._cache_entities: list[dict[str, Any]] = []
        self._cache_timestamp: float = 0.0
        self._cache_ttl: float = 60.0  # Expira após 60 segundos

    @property
    def is_configured(self) -> bool:
        """Verifica se o token do Home Assistant está configurado."""
        return bool(self._token and len(self._token.strip()) > 10)

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }

    async def load_entities_cache(self, force: bool = False) -> list[dict[str, Any]]:
        """
        Carrega e atualiza em memória todas as entidades registradas no Home Assistant.
        Executado na inicialização do backend (lifespan) ou sob demanda.
        """
        now = time.time()
        if not force and self._cache_entities and (now - self._cache_timestamp) < self._cache_ttl:
            return self._cache_entities

        if not self.is_configured:
            print("⚠️ [HA CACHE] Token do Home Assistant não configurado no .env.", flush=True)
            return []

        url = f"{self._url}/api/states"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=self._get_headers())
                if resp.status_code == 200:
                    states = resp.json()
                    self._cache_entities = states
                    self._cache_timestamp = now

                    lights = [s for s in states if s.get("entity_id", "").startswith("light.")]
                    switches = [s for s in states if s.get("entity_id", "").startswith("switch.")]

                    print("=" * 65)
                    print(f"🏠 [HA ENTITIES CACHE] {len(states)} entidades pré-carregadas do Home Assistant")
                    print(f"   ├─ Luzes ({len(lights)}): {', '.join([l.get('attributes', {}).get('friendly_name', l['entity_id']) for l in lights[:8]])}")
                    if switches:
                        print(f"   └─ Interruptores ({len(switches)}): {', '.join([s.get('attributes', {}).get('friendly_name', s['entity_id']) for s in switches[:8]])}")
                    print("=" * 65, flush=True)

                    return states
                else:
                    print(f"❌ [HA CACHE ERROR] HTTP {resp.status_code} ao buscar entidades do HA: {resp.text}", flush=True)
                    return self._cache_entities
        except Exception as e:
            print(f"❌ [HA CACHE EXCEPTION] Falha ao pré-carregar entidades do HA: {e}", flush=True)
            return self._cache_entities

    async def get_entity_state(self, entity_id: str) -> dict[str, Any] | None:
        """
        Consulta o estado atual de um dispositivo/sensor no Home Assistant.
        """
        if not self.is_configured:
            return None

        url = f"{self._url}/api/states/{entity_id}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=self._get_headers())
                if resp.status_code == 200:
                    return resp.json()
                return None
        except Exception as e:
            print(f"❌ [HA SERVICE EXCEPTION] Falha ao consultar estado de '{entity_id}': {e}", flush=True)
            return None

    async def list_entities(self, domain: str | None = None) -> list[dict[str, Any]]:
        """
        Retorna as entidades da cache ou busca atualizadas do Home Assistant.
        """
        entities = await self.load_entities_cache()
        if domain:
            prefix = f"{domain}."
            return [s for s in entities if s.get("entity_id", "").startswith(prefix)]
        return entities

    async def find_entity_by_name(self, name_query: str, domain: str = "light") -> str | None:
        """
        Resolve o termo de busca em português ou inglês para a entity_id correspondente no HA.
        - Filtra apenas domínios válidos (light, switch, group)
        - Aplica tradução PT <-> EN (ex: "escritório" -> "Office Light")
        - Aplica normalização sem acentos e busca por pontuação
        """
        entities = await self.list_entities()
        if not entities:
            return None

        q_norm = _normalize_text(name_query)
        if not q_norm:
            return None

        stopwords = {"luz", "lampada", "tomada", "interruptor", "dispositivo", "de", "da", "do", "das", "dos", "a", "o"}
        q_clean_words = [w for w in q_norm.split() if w not in stopwords]
        base_term = " ".join(q_clean_words) if q_clean_words else q_norm

        search_terms = [q_norm, base_term]
        for word in q_clean_words + [q_norm, base_term]:
            if word in TRANSLATION_MAP:
                search_terms.extend(TRANSLATION_MAP[word])

        search_terms = list(dict.fromkeys([t for t in search_terms if t]))

        best_entity_id = None
        highest_score = 0

        for e in entities:
            e_id = e.get("entity_id", "")
            e_domain = e_id.split(".")[0] if "." in e_id else ""

            if e_domain not in ALLOWED_DEVICE_DOMAINS:
                continue

            friendly_name = e.get("attributes", {}).get("friendly_name", "")
            e_id_norm = _normalize_text(e_id)
            friendly_norm = _normalize_text(friendly_name)

            domain_bonus = 10 if e_domain == "light" else (5 if e_domain == "switch" else 0)

            for term in search_terms:
                score = 0
                if term == friendly_norm or term == e_id_norm or f"{domain}.{term}" == e_id_norm:
                    score = 100 + domain_bonus
                elif term in friendly_norm or term in e_id_norm:
                    score = 85 + domain_bonus
                else:
                    term_tokens = set(term.split())
                    fname_tokens = set(friendly_norm.split())
                    overlap = term_tokens.intersection(fname_tokens)
                    if overlap:
                        score = 70 + (len(overlap) * 5) + domain_bonus

                if score > highest_score:
                    highest_score = score
                    best_entity_id = e_id

        if highest_score >= 50:
            return best_entity_id

        return None

    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str,
        service_data: dict[str, Any] | None = None
    ) -> bool:
        """
        Dispara uma chamada de serviço no Home Assistant (ex: domain="light", service="turn_on", entity_id="light.office_light").
        """
        if not self.is_configured:
            print("⚠️ [HA SERVICE] Não configurado. Impossível disparar serviço.", flush=True)
            return False

        url = f"{self._url}/api/services/{domain}/{service}"
        payload = {"entity_id": entity_id}
        if service_data:
            payload.update(service_data)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, headers=self._get_headers(), json=payload)
                if resp.status_code in (200, 201):
                    print(f"🚀 [HA SERVICE] Serviço '{domain}.{service}' disparado com sucesso para '{entity_id}'", flush=True)
                    return True
                else:
                    print(f"❌ [HA SERVICE ERROR] Erro HTTP {resp.status_code} ao chamar {domain}.{service}: {resp.text}", flush=True)
                    return False
        except Exception as e:
            print(f"❌ [HA SERVICE EXCEPTION] Falha ao chamar serviço: {e}", flush=True)
            return False

    async def control_device_with_feedback(
        self,
        domain: str,
        action: str,
        entity_id: str,
        expected_state: str | None = None,
        wait_timeout: float = 3.0,
        poll_interval: float = 0.5,
        session_id: str = "default"
    ) -> dict[str, Any]:
        """
        Executa um comando no Home Assistant e VALIDA O ESTADO VIA FEEDBACK DE SENSOR.
        Se bem-sucedido, armazena o dispositivo no contexto da sessão para conversas futuras.
        """
        if "." not in entity_id:
            entity_id = f"{domain}.{entity_id}"
        else:
            domain = entity_id.split(".")[0]

        action_norm = action.lower().strip()
        if action_norm in ("on", "turn_on", "ligar", "acender"):
            service = "turn_on"
            target_expected_state = "on"
            action_desc = "ligar"
        elif action_norm in ("off", "turn_off", "desligar", "apagar"):
            service = "turn_off"
            target_expected_state = "off"
            action_desc = "desligar"
        elif action_norm in ("toggle", "alternar", "trocar", "chavear"):
            # Para toggle, consulta o estado atual no HA e inverte o estado
            current_st_data = await self.get_entity_state(entity_id)
            current_st = current_st_data.get("state") if current_st_data else "off"
            if current_st == "on":
                service = "turn_off"
                target_expected_state = "off"
                action_desc = "desligar"
            else:
                service = "turn_on"
                target_expected_state = "on"
                action_desc = "ligar"
        else:
            service = action_norm
            target_expected_state = expected_state or "on"
            action_desc = action_norm


        if expected_state:
            target_expected_state = expected_state

        if not self.is_configured:
            msg = f"Home Assistant não está configurado (HA_TOKEN ausente). Não foi possível {action_desc} o dispositivo '{entity_id}'."
            print(f"⚠️ [HA FEEDBACK CHECK] {msg}", flush=True)
            return {
                "success": False,
                "verified": False,
                "entity_id": entity_id,
                "action": service,
                "expected_state": target_expected_state,
                "actual_state": "desconhecido",
                "message": msg
            }

        # 1. Consulta estado inicial
        initial_state_data = await self.get_entity_state(entity_id)
        initial_state = initial_state_data.get("state") if initial_state_data else "desconhecido"
        friendly_name = (
            initial_state_data.get("attributes", {}).get("friendly_name")
            if initial_state_data else entity_id
        ) or entity_id

        print(f"🔍 [HA FEEDBACK] Estado inicial de '{friendly_name}' ({entity_id}): '{initial_state}'", flush=True)

        # 1.1 Checa se o dispositivo JÁ está no estado solicitado antes de enviar qualquer chamada de serviço
        if initial_state == target_expected_state:
            conversation_service.set_last_device(
                session_id=session_id,
                entity_id=entity_id,
                friendly_name=friendly_name,
                target_name=friendly_name,
                domain=domain
            )
            estado_pt = "ligado(a)" if target_expected_state == "on" else "desligado(a)"
            msg = f"O dispositivo '{friendly_name}' já está {estado_pt}."
            print(f"ℹ️ [HA ALREADY IN STATE] '{friendly_name}' ({entity_id}) já se encontra em '{initial_state}'. Chamada de serviço ignorada.", flush=True)
            return {
                "success": True,
                "verified": True,
                "already_in_state": True,
                "entity_id": entity_id,
                "action": service,
                "expected_state": target_expected_state,
                "actual_state": initial_state,
                "message": msg
            }

        # 2. Dispara o serviço no Home Assistant

        service_sent = await self.call_service(domain, service, entity_id)
        if not service_sent:
            msg = f"Falha ao enviar comando de {action_desc} para '{friendly_name}'."
            return {
                "success": False,
                "verified": False,
                "entity_id": entity_id,
                "action": service,
                "expected_state": target_expected_state,
                "actual_state": initial_state,
                "message": msg
            }

        # 3. Polling de verificação de feedback do sensor no HA
        start_time = time.time()
        verified = False
        current_state = initial_state

        print(f"⌛ [HA FEEDBACK] Aguardando validação do sensor para '{friendly_name}' mudar para '{target_expected_state}'...", flush=True)

        while (time.time() - start_time) <= wait_timeout:
            await asyncio.sleep(poll_interval)
            latest_data = await self.get_entity_state(entity_id)
            if latest_data:
                current_state = latest_data.get("state", "desconhecido")
                if current_state == target_expected_state:
                    verified = True
                    break

        # 4. Avaliação estrita do resultado
        if verified:
            # Salva o dispositivo no contexto da conversa para referências futuras
            conversation_service.set_last_device(
                session_id=session_id,
                entity_id=entity_id,
                friendly_name=friendly_name,
                target_name=friendly_name,
                domain=domain
            )
            estado_pt = "ligado(a)" if target_expected_state == "on" else "desligado(a)"
            msg = f"Confirmado pelo sensor: O dispositivo '{friendly_name}' foi {estado_pt} com sucesso."
            print(f"✅ [HA FEEDBACK VERIFIED] {msg}", flush=True)
            return {
                "success": True,
                "verified": True,
                "entity_id": entity_id,
                "action": service,
                "expected_state": target_expected_state,
                "actual_state": current_state,
                "message": msg
            }
        else:
            estado_atual_pt = "ligado(a)" if current_state == "on" else ("desligado(a)" if current_state == "off" else current_state)
            msg = (
                f"Atenção: O comando para {action_desc} '{friendly_name}' foi enviado, "
                f"mas a checagem do sensor indica que o dispositivo continua em '{estado_atual_pt}'."
            )
            print(f"❌ [HA FEEDBACK UNVERIFIED] {msg}", flush=True)
            return {
                "success": False,
                "verified": False,
                "entity_id": entity_id,
                "action": service,
                "expected_state": target_expected_state,
                "actual_state": current_state,
                "message": msg
            }

    async def parse_and_execute_ha_command(self, user_text: str, session_id: str = "default") -> dict[str, Any] | None:
        """
        Analisa o texto do usuário para detectar comandos de controle de luzes/dispositivos
        e executa a validação estrita com feedback de sensor do Home Assistant.
        Suporta anáforas e referências a conversas anteriores (ex: "agora desligue", "desliga ela").
        """
        text_clean = user_text.strip().lower()
        text_clean = re.sub(r'^(pode|poderia|por\s+favor|jarvis|por\s+gentileza|você\s+pode|faça\s+o\s+favor\s+de)\s+', '', text_clean).strip()

        # Padrões de ativação (ON) com variações fonéticas de STT (ex: "lide a luz", "lida")
        on_match = re.search(
            r'\b(liga|ligar|ligue|lida|lide|lido|acende|acender|acenda|ativa|ativar|ative|turn\s*on)\b(?:\s*(?:a|o)?\s*(?:luz|lâmpada|lampada|tomada|interruptor|dispositivo|equipamento)?\s*(?:de|da|do)?\s*(.*))?',
            text_clean
        )
        # Padrões de desativação (OFF) com variações fonéticas de STT
        off_match = re.search(
            r'\b(desliga|desligar|desligue|deslida|deslide|apaga|apagar|apague|desativa|desativar|desative|turn\s*off)\b(?:\s*(?:a|o)?\s*(?:luz|lâmpada|lampada|tomada|interruptor|dispositivo|equipamento)?\s*(?:de|da|do)?\s*(.*))?',
            text_clean
        )

        # Padrões de afirmação no passado (ex: "agora desliguei", "já desliguei", "eu desliguei")
        past_match = re.search(
            r'\b(desliguei|apaguei|desativei|liguei|acendi|ativei)\b(?:\s*(?:a|o)?\s*(?:luz|lâmpada|lampada|tomada|interruptor|dispositivo)?\s*(?:de|da|do)?\s*(.*))?',
            text_clean
        )

        if past_match:
            verb = past_match.group(1).lower()
            last_dev = conversation_service.get_last_device(session_id)
            dev_name = last_dev["friendly_name"] if last_dev else "dispositivo"
            target_entity = last_dev["entity_id"] if last_dev else None
            
            actual_st = "desconhecido"
            if target_entity:
                st_data = await self.get_entity_state(target_entity)
                if st_data:
                    actual_st = st_data.get("state", "desconhecido")

            state_pt = "desligado(a)" if actual_st == "off" else ("ligado(a)" if actual_st == "on" else actual_st)
            msg = f"Entendido! O sensor do Home Assistant confirma que '{dev_name}' está em '{state_pt}'."
            print(f"ℹ️ [HA PAST INTENT] Afirmação no passado detectada ('{verb}'). Confirmação de sensor: \"{msg}\"", flush=True)
            return {
                "success": True,
                "verified": True,
                "message": msg
            }

        # Padrões de alternância (TOGGLE / DOUBLE CLAP / PALMAS)
        toggle_match = re.search(
            r'\b(alterna|alternar|troca|trocar|chaveia|chavear|toggle|double\s*clap|palma|palmas)\b(?:\s*(?:a|o)?\s*(?:luz|lâmpada|lampada|tomada|interruptor|dispositivo|equipamento)?\s*(?:de|da|do)?\s*(.*))?',
            text_clean
        )

        action = None
        raw_target = None

        if toggle_match:
            action = "toggle"
            raw_target = (toggle_match.group(2) or "").strip()
        elif off_match:
            action = "turn_off"
            raw_target = (off_match.group(2) or "").strip()
        elif on_match:
            action = "turn_on"
            raw_target = (on_match.group(2) or "").strip()



        if not action:
            # Se não detectou um verbo de comando, checa se há uma intenção pendente aguardando a especificação do cômodo
            pending_act = conversation_service.get_pending_action(session_id)
            if pending_act:
                target_clean = re.sub(r'[\?\.\!\,]', '', text_clean)
                target_clean = re.sub(r'\b(por\s+favor|agora|jarvis|gentileza|do|da|de|no|na)\b', '', target_clean).strip()
                resolved_entity = await self.find_entity_by_name(target_clean, domain=pending_act.get("domain", "light"))
                if resolved_entity:
                    action = pending_act["action"]
                    domain = resolved_entity.split(".")[0]
                    conversation_service.clear_pending_action(session_id)
                    print(f"🧠 [PENDING INTENT RESOLVED] Aplicando comando pendente '{action}' ao cômodo '{target_clean}' -> entity_id='{resolved_entity}'", flush=True)
                    return await self.control_device_with_feedback(
                        domain=domain,
                        action=action,
                        entity_id=resolved_entity,
                        session_id=session_id
                    )
            return None

        # Limpeza do termo alvo e advérbios de repetição/cortesia
        target_clean = re.sub(r'[\?\.\!\,]', '', raw_target)
        target_clean = re.sub(r'\b(por\s+favor|agora|jarvis|gentileza|de\s+novo|denovo|novamente)\b', '', target_clean).strip()

        target_norm = _normalize_text(target_clean)

        entity_id = None

        # RESOLUÇÃO DE ANÁFORAS / PRONOMES / CÔMODO OMITIDO
        if not target_norm or target_norm in ANAPHORA_PRONOUNS:
            last_dev = conversation_service.get_last_device(session_id)
            if last_dev:
                entity_id = last_dev["entity_id"]
                friendly = last_dev["friendly_name"]
                print(f"🧠 [ANAPHORA RESOLUTION] Mapeado termo pronominal '{target_clean or 'omitido'}' para o último dispositivo do contexto: '{friendly}' ({entity_id})", flush=True)
            else:
                # Registra o comando como pendente para aguardar o complemento do cômodo no próximo turno
                conversation_service.set_pending_action(session_id, action=action, domain="light")
                msg = "Não sei a qual luz ou dispositivo você está se referindo. Por favor especifique o cômodo (ex: 'escritório', 'sala')."
                print(f"⚠️ [ANAPHORA RESOLUTION] {msg}", flush=True)
                return {
                    "success": False,
                    "verified": False,
                    "message": msg
                }
        else:
            # Limpa qualquer ação pendente pois um comando completo foi fornecido
            conversation_service.clear_pending_action(session_id)
            # Tenta resolver a entidade no HA com tradução PT-BR <-> EN e filtro de domínios
            entity_id = await self.find_entity_by_name(target_clean, domain="light")


        if not entity_id:
            available = await self.list_entities()
            avail_lights = [
                e.get("attributes", {}).get("friendly_name") or e.get("entity_id")
                for e in available
                if e.get("entity_id", "").startswith(("light.", "switch."))
            ]
            list_str = f" Dispositivos encontrados: {', '.join(avail_lights[:5])}." if avail_lights else ""
            msg = f"Cômodo ou dispositivo '{target_clean}' não foi encontrado no seu Home Assistant.{list_str}"
            print(f"⚠️ [HA INTENT PARSER] {msg}", flush=True)
            return {
                "success": False,
                "verified": False,
                "message": msg
            }

        domain = entity_id.split(".")[0]
        print(f"🎯 [HA INTENT PARSER] Comando detectado: action='{action}', target='{target_clean or 'contexto'}' -> entity_id='{entity_id}'", flush=True)

        return await self.control_device_with_feedback(
            domain=domain,
            action=action,
            entity_id=entity_id,
            session_id=session_id
        )

ha_service = HAService()
