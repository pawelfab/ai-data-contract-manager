from pydantic import BaseModel


class Settings(BaseModel):
    llm_model: str = "openai:gpt-5.6-sol"
    session_backend: str = "memory"
    audit_backend: str = "jsonl"
    contract_forge_transport: str = "mock"
