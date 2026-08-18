---
scope: src/adcm/ports
last_verified: working-tree-2026-08-18
---

# Symbol catalog: ports

- `audit_sink.py::AuditSinkPort.append(event: AuditEvent) -> None`
- `capability.py::CapabilityHandlerPort.execute(capability: str, args: dict[str, Any]) -> dict[str, Any]`
- `contract_forge.py::ContractForgePort.evaluate_draft(request: ContractInput) -> ContractEvaluationResult`
- `contract_forge.py::ContractForgePort.validate_final(request: ContractInput) -> FinalValidationResult`
- `contract_forge.py::ContractForgePort.render_yaml(request: RenderRequest) -> RenderedContract`
- `semantic_interpreter.py::SemanticInterpreterPort.interpret_turn(text: str, context: AgentContext) -> TurnInterpretation`
- `session_repository.py::SessionRepositoryPort.load(session_id: UUID) -> ConversationState | None`
- `session_repository.py::SessionRepositoryPort.save(state: ConversationState) -> None`

All methods are async. Protocols specify application-facing behavior and do not own retries, authentication, transactions, or provider lifecycle.

