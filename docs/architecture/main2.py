import json
import asyncio
from typing import Any, Dict, Type
from dataclasses import dataclass
from pydantic import BaseModel, Field, create_model
from pydantic_ai import Agent, RunContext, Tool

# =====================================================================
# 1. ROZDZIELONE DANE: KONTRAKT BAZOWY vs REGUŁY POMOCNICZE
# =====================================================================
class SchemaEngine:
    def __init__(self):
        # 1. Główny niezmienny kontrakt (np. plik contract.json)
        # Zdefiniowane są tu TYLKO twarde typy i powiązania (x-contract-rules)
        self.base_contract = {
            "type": "object",
            "properties": {
                "systemZrodlowy": {"type": "string"},
                "converter": {
                    "type": "object",
                    "properties": {
                        "sys_name": {"type": "string"},
                        "nazwaPliku": {"type": "string"},
                        "formatWyjsciowy": {"type": "string"}
                    },
                    "required": ["sys_name", "nazwaPliku", "formatWyjsciowy"]
                }
            },
            # Subiekt wymaga converter'a, InneSystemy tego nie wymagają
            "required": ["systemZrodlowy"] 
        }

        # 2. Osobny plik z pomocniczymi regułami UX / Autofill (np. ux_rules.json)
        self.ux_rules = [
            {
                "condition": {"field": "systemZrodlowy", "equals": "subiekt"},
                "target_path": "converter",
                "action": "suggest",
                "instruction": (
                    "Dla systemu Subiekt wymuś od użytkownika obiekt converter. "
                    "Zaproponuj: 1) sys_name = 'subiekt', 2) formatWyjsciowy = 'parquet', "
                    "3) nazwaPliku = 'subiekt-{data}.txt'. Zapytaj o datę, zanim użyjesz narzędzia."
                )
            }
        ]

    def build_schema_for_current_state(self, current_state: dict) -> dict:
        """Tworzy połączony schemat w locie: Kontrakt + Aktywne Reguły UX"""
        import copy
        # Zaczynamy od skopiowania twardego kontraktu
        schema_overlay = copy.deepcopy(self.base_contract)
        sys_name = current_state.get("systemZrodlowy", "").lower()
        
        if not sys_name:
            # Tura 1: Pobieramy tylko system źródłowy
            schema_overlay["required"] = ["systemZrodlowy"]
            # Ukrywamy resztę kontraktu dla LLM, by skupił się tylko na tym
            schema_overlay["properties"] = {"systemZrodlowy": schema_overlay["properties"]["systemZrodlowy"]}
            return schema_overlay

        # Tura 2+: Znamy system. Nakładamy odpowiednie restrykcje i podpowiedzi UX.
        if sys_name == "subiekt":
            # Twarda reguła kontraktu: Subiekt wymaga convertera
            schema_overlay["required"] = ["systemZrodlowy", "converter"]
            
            # Wyszukujemy i nakładamy miękkie reguły pomocnicze UX z osobnego pliku
            for rule in self.ux_rules:
                if rule["condition"]["equals"] == sys_name and rule["target_path"] in schema_overlay["properties"]:
                    # Wstrzykujemy pomocniczą instrukcję tylko jako "description" w JSON Schema (dla LLM-a)
                    target_prop = schema_overlay["properties"][rule["target_path"]]
                    target_prop["description"] = target_prop.get("description", "") + f" [ZASADA POMOCNICZA: {rule['instruction']}]"
                    
            return schema_overlay
            
        return {"status": "COMPLETE"} # Jeśli inny system niż subiekt - koniec (w tym uproszczonym przykładzie)

# =====================================================================
# 2. PARSER (Pozostaje bez zmian - po prostu czyta złączony Schema)
# =====================================================================
def json_schema_to_pydantic(name: str, schema: dict) -> Type[BaseModel]:
    fields = {}
    required_fields = schema.get("required", [])
    
    for prop_name, prop_data in schema.get("properties", {}).items():
        desc = prop_data.get("description", "")

        # Rekursja dla zagnieżdżonych struktur, ignorujemy w tym podglądzie pełne wstrzykiwanie x-contract-rules (jak w poprz. odp.)
        if prop_data.get("type") == "object" and "properties" in prop_data:
            py_type = json_schema_to_pydantic(f"{name}_{prop_name}", prop_data)
        else:
            py_type = str

        default_val = ... if prop_name in required_fields else None
        fields[prop_name] = (py_type, Field(default_val, description=desc))
        
    return create_model(name, **fields)

# =====================================================================
# 3. CORE SYSTEM (Logika Agenta)
# =====================================================================
@dataclass
class CoreState:
    collected_data: Dict[str, Any]

async def chat_loop():
    engine = SchemaEngine()
    state = CoreState(collected_data={})
    message_history = []
    
    while True:
        # Pytamy nasz "Silnik Złączający", co robić dalej
        current_schema_def = engine.build_schema_for_current_state(state.collected_data)
        
        if current_schema_def.get("status") == "COMPLETE":
            print("
[SYSTEM] MCP WALIDACJA OK!")
            break
            
        # Parser konwertuje połączony (Kontrakt + UX Rules) na Pydantic
        DynamicContractSchema = json_schema_to_pydantic("DynamicContract", current_schema_def)
        
        agent = Agent(
            'openai:gpt-4o',
            deps_type=CoreState,
            system_prompt=(
                "Jesteś asystentem uzupełniania danych biznesowych. "
                "Będziesz dostawał narzędzie (submit_to_mcp) z wymaganymi polami. "
                "Jeżeli w opisie pola widzisz [ZASADA POMOCNICZA: ...], nie wymyślaj danych! "
                "Przekaż tę sugestię użytkownikowi i poproś o niezbędne braki (np. datę) "
                "ZANIM wywołasz narzędzie."
            )
        )
        
        @agent.tool
        def submit_to_mcp(ctx: RunContext[CoreState], data: DynamicContractSchema) -> str:
            ctx.deps.collected_data.update(data.model_dump(exclude_unset=True, exclude_none=True))
            return "Dane zapisane w bazie, pętla może kontynuować."

        user_msg = input("
Ty: ")
        result = await agent.run(user_msg, deps=state, message_history=message_history)
        message_history = result.all_messages()
        print(f"Agent: {result.data}")
