import time
import asyncio
import httpx
import unicodedata
import re
from typing import Any
from backend.config import settings

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

class HAService:
    """
    Serviço de integração assíncrono com a API REST do Home Assistant.
    Fornece pré-carregamento de entidades na inicialização, resolução inteligente por nome
    (com tradução PT-BR <-> EN), filtro estrito de domínios e validação de feedback de sensores/estados.
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

        # Stopwords comuns a ignorar na análise de cômodos
        stopwords = {"luz", "lampada", "tomada", "interruptor", "dispositivo", "de", "da", "do", "das", "dos", "a", "o"}
        q_clean_words = [w for w in q_norm.split() if w not in stopwords]
        base_term = " ".join(q_clean_words) if q_clean_words else q_norm

        # Expansão de sinônimos/traduções (ex: "escritorio" -> ["escritorio", "office", "desk", "study"])
        search_terms = [q_norm, base_term]
        for word in q_clean_words + [q_norm, base_term]:
            if word in TRANSLATION_MAP:
                search_terms.extend(TRANSLATION_MAP[word])

        # Remove duplicadas mantendo ordem
        search_terms = list(dict.fromkeys([t for t in search_terms if t]))

        best_entity_id = None
        highest_score = 0

        for e in entities:
            e_id = e.get("entity_id", "")
            e_domain = e_id.split(".")[0] if "." in e_id else ""

            # FILTRO ESTRITO: Apenas domínios válidos de atuação física (ignora button, sensor, automation, etc.)
            if e_domain not in ALLOWED_DEVICE_DOMAINS:
                continue

            friendly_name = e.get("attributes", {}).get("friendly_name", "")
            e_id_norm = _normalize_text(e_id)
            friendly_norm = _normalize_text(friendly_name)

            # Prioriza domínio principal 'light' se solicitado
            domain_bonus = 10 if e_domain == "light" else (5 if e_domain == "switch" else 0)

            for term in search_terms:
                score = 0
                # 1. Correspondência exata
                if term == friendly_norm or term == e_id_norm or f"{domain}.{term}" == e_id_norm:
                    score = 100 + domain_bonus
                # 2. Termo como substring exata no nome amigável ou ID (ex: "office" em "office light")
                elif term in friendly_norm or term in e_id_norm:
                    score = 85 + domain_bonus
                # 3. Sobreposição de tokens
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
        poll_interval: float = 0.5
    ) -> dict[str, Any]:
        """
        Executa um comando no Home Assistant e VALIDA O ESTADO VIA FEEDBACK DE SENSOR.
        Só confirma sucesso se o estado verificado no HA bater com o esperado após a execução.
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

    async def parse_and_execute_ha_command(self, user_text: str) -> dict[str, Any] | None:
        """
        Analisa o texto do usuário para detectar comandos de controle de luzes/dispositivos
        e executa a validação estrita com feedback de sensor do Home Assistant.
        """
        text_clean = user_text.strip().lower()
        text_clean = re.sub(r'^(pode|poderia|por\s+favor|jarvis|por\s+gentileza|você\s+pode|faça\s+o\s+favor\s+de)\s+', '', text_clean).strip()

        # Padrões de ativação (ON)
        on_match = re.search(
            r'\b(liga|ligar|ligue|acende|acender|acenda|ativa|ativar|ative|turn\s*on)\b\s*(?:a|o)?\s*(?:luz|lâmpada|lampada|tomada|interruptor|dispositivo|equipamento)?\s*(?:de|da|do)?\s*(.+)',
            text_clean
        )
        # Padrões de desativação (OFF)
        off_match = re.search(
            r'\b(desliga|desligar|desligue|apaga|apagar|apague|desativa|desativar|desative|turn\s*off)\b\s*(?:a|o)?\s*(?:luz|lâmpada|lampada|tomada|interruptor|dispositivo|equipamento)?\s*(?:de|da|do)?\s*(.+)',
            text_clean
        )

        action = None
        target_name = None

        if off_match:
            action = "turn_off"
            target_name = off_match.group(2).strip()
        elif on_match:
            action = "turn_on"
            target_name = on_match.group(2).strip()

        if not action or not target_name:
            return None

        target_name = re.sub(r'[\?\.\!\,]', '', target_name)
        target_name = re.sub(r'\b(por\s+favor|agora|jarvis|gentileza)\b', '', target_name).strip()

        if not target_name:
            return None

        # Tenta resolver a entidade no HA com tradução PT-BR <-> EN e filtro estrito de domínios
        entity_id = await self.find_entity_by_name(target_name, domain="light")

        if not entity_id:
            # Lista luzes e interruptores reais disponíveis no HA do usuário para dar feedback informativo
            available = await self.list_entities()
            avail_lights = [
                e.get("attributes", {}).get("friendly_name") or e.get("entity_id")
                for e in available
                if e.get("entity_id", "").startswith(("light.", "switch."))
            ]
            list_str = f" Luzes/Dispositivos encontrados: {', '.join(avail_lights[:5])}." if avail_lights else ""
            msg = f"Cômodo ou dispositivo '{target_name}' não foi encontrado no seu Home Assistant.{list_str}"
            print(f"⚠️ [HA INTENT PARSER] {msg}", flush=True)
            return {
                "success": False,
                "verified": False,
                "message": msg
            }

        domain = entity_id.split(".")[0]
        print(f"🎯 [HA INTENT PARSER] Comando detectado: action='{action}', target='{target_name}' -> entity_id='{entity_id}'", flush=True)

        return await self.control_device_with_feedback(
            domain=domain,
            action=action,
            entity_id=entity_id
        )

ha_service = HAService()
