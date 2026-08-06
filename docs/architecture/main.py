import json
import asyncio
from typing import Any, Dict, Type
from dataclasses import dataclass
from pydantic import BaseModel, Field, create_model
from pydantic_ai import Agent, RunContext, Tool

# =====================================================================
# 1. SYMULACJA SERWERA MCP I KONTRAKTÓW JSON
# =====================================================================
class MockMCP:
    def __init__(self):
        # Symulacja zawartości surowego pliku JSON z regułami.
        # W rzeczywistości MCP odczytuje to z systemu plików/API.
        self.stage_1_json = """
        {
            "type": "object",
            "properties": {
                "systemZrodlowy": {
                    "type": "string", 
                    "description": "Nazwa systemu np. pcmarket lub subiekt"
                }
            },
            "required": ["systemZrodlowy"]
        }
        """
        self.stage_2_json = """
        {
            "type": "object",
            "properties": {
                "systemZrodlowy": {"type": "string"},
                "columns": {
                    "type": "array",
                    "description": "Definicja kolumn stałoszerokościowych",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "start": {"type": "integer"},
                            "end": {"type": "integer"},
                            "length": {
                                "type": "integer", 
                                "description": "Długość kolumny"
                            }
                        },
                        "required": ["name", "start", "end", "length"],
                        "x-contract-rules": [
                            {
                                "message": "Pole 'length' ZAWSZE musi być równe wyliczeniu: end - start + 1",
                                "path": "length"
                            }
                        ]
                    }
                }
            },
            "required": ["systemZrodlowy", "columns"]
        }
        """

    def evaluate(self, current_data: dict) -> dict:
        """Serwer MCP decyduje co jest wymagane w oparciu o to, co już zebrano."""
        if "systemZrodlowy" not in current_data:
            return json.loads(self.stage_1_json)
        elif "columns" not in current_data:
            return json.loads(self.stage_2_json)
        else:
            return {"status": "COMPLETE"}


# =====================================================================
# 2. CORE SYSTEM: DYNAMICZNY PARSER JSON SCHEMA -> PYDANTIC
# =====================================================================
def json_schema_to_pydantic(name: str, schema: dict) -> Type[BaseModel]:
    """Rekursywnie buduje modele Pydantic na podstawie specyfikacji od MCP."""
    fields = {}
    required_fields = schema.get("required", [])
    
    for prop_name, prop_data in schema.get("properties", {}).items():
        desc = prop_data.get("description", "")
        
        # Wstrzykiwanie reguł x-contract-rules prosto do opisu dla LLM
        rules_source = prop_data.get("items", {}) if prop_data.get("type") == "array" else prop_data
        if "x-contract-rules" in rules_source:
            rules = " ".join([r.get("message", "") for r in rules_source["x-contract-rules"]])
            desc += f" [REGUŁA BIZNESOWA: {rules}]"

        # Mapowanie typów i rekursywne budowanie tablic obiektów
        if prop_data.get("type") == "integer":
            py_type = int
        elif prop_data.get("type") == "array":
            items_schema = prop_data.get("items", {})
            item_model = json_schema_to_pydantic(f"{name}_{prop_name}_Item", items_schema)
            py_type = list[item_model]
        else:
            py_type = str
            
        # Zależności wymagane vs opcjonalne (Slot filling)
        default_val = ... if prop_name in required_fields else None
        fields[prop_name] = (py_type, Field(default_val, description=desc))
        
    return create_model(name, **fields)


# =====================================================================
# 3. CORE SYSTEM: STAN I PĘTLA AGENTA PYDANTIC-AI
# =====================================================================
@dataclass
class CoreState:
    collected_data: Dict[str, Any]

async def chat_loop():
    mcp_server = MockMCP()
    state = CoreState(collected_data={})
    message_history = []
    
    print("--- Start Systemu ---")
    print("Agent: Witaj! Rozpocznijmy konfigurację kontraktu. Jaki system źródłowy chcesz podłączyć?
")

    while True:
        # Krok 1: Pytamy MCP o obecny kontrakt względem tego co mamy
        mcp_response = mcp_server.evaluate(state.collected_data)
        
        if mcp_response.get("status") == "COMPLETE":
            print("
[SYSTEM] MCP zgłosiło kompletność danych!")
            print(f"[Zapisany JSON]: {json.dumps(state.collected_data, indent=2)}")
            break
            
        # Krok 2: Dynamiczne stworzenie modelu Pydantic na obecną rundę
        DynamicContractSchema = json_schema_to_pydantic("DynamicContract", mcp_response)
        
        # Krok 3: Inicjalizacja Agenta z dynamicznym modelem
        agent = Agent(
            'openai:gpt-4o', 
            deps_type=CoreState,
            system_prompt=(
                "Jesteś asystentem integracji. Zbierasz dane od użytkownika krok po kroku. "
                "Zawsze wywołuj narzędzie 'submit_to_mcp' gdy dowiesz się czegoś nowego, "
                "lub by uzupełnić dane podane przez użytkownika wyliczając zależności z REGUŁ."
            )
        )
        
        @agent.tool
        def submit_to_mcp(ctx: RunContext[CoreState], data: DynamicContractSchema) -> str:
            """Aktualizuje słownik danych systemowych."""
            updates = data.model_dump(exclude_unset=True, exclude_none=True)
            ctx.deps.collected_data.update(updates)
            return "Dane zapisane w systemie Core. Czekam na weryfikację MCP."

        # Krok 4: Czekamy na wiadomość użytkownika
        user_msg = input("Ty: ")
        if user_msg.lower() == 'exit':
            break

        # Krok 5: Agent procesuje odpowiedź, używa Toolsów i odpisuje
        result = await agent.run(user_msg, deps=state, message_history=message_history)
        message_history = result.all_messages()
        
        print(f"
Agent: {result.data}")
        print(f"--- [Stan pod maską Core: {state.collected_data}] ---")

if __name__ == "__main__":
    asyncio.run(chat_loop())
