from contract_forge.domain.protocol import PROTOCOL_VERSION, FieldDescriptor, ForgeDescription
from contract_forge.ports.definition_repository import ContractDefinitionPort

from .schema_utils import join_pointer, resolve_ref


class ContractDescriber:
    def __init__(self, definitions: ContractDefinitionPort) -> None:
        self.definitions = definitions

    def describe(self) -> ForgeDescription:
        definition = self.definitions.load()
        fields = self._fields(definition.schema_document, definition.schema_document, "", required=True)
        return ForgeDescription(protocol_version=PROTOCOL_VERSION, definition_version=definition.version, fields=fields)

    def _fields(self, root: dict, schema: dict, path: str, required: bool) -> list[FieldDescriptor]:
        schema = resolve_ref(root, schema)
        result: list[FieldDescriptor] = []
        if path:
            result.append(
                FieldDescriptor(
                    path_pattern=path,
                    value_type=schema.get("type"),
                    required=required,
                    allowed_values=schema.get("enum"),
                    title=schema.get("title"),
                    description=schema.get("description"),
                )
            )
        if schema.get("type") == "object":
            required_names = set(schema.get("required", []))
            for name, child in schema.get("properties", {}).items():
                result.extend(self._fields(root, child, join_pointer(path, name), name in required_names))
        elif schema.get("type") == "array":
            result.extend(self._fields(root, schema.get("items", {}), join_pointer(path, "*"), required=False))
        return result
