from __future__ import annotations

from dataclasses import dataclass
import uuid
from typing import Awaitable, Callable

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import Conversation, ToolExecution


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    handler: Callable[[BaseModel], Awaitable[BaseModel]]
    requires_confirmation: bool = True


class ToolRegistry:
    """Typed registry for Phase 2 actions; Phase 1 intentionally registers none."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ValueError(f"Tool already registered: {definition.name}")
        self._tools[definition.name] = definition

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    @property
    def names(self) -> set[str]:
        return set(self._tools)


class ToolService:
    """Validates, persists, confirms, and executes registered typed tools."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def prepare(
        self,
        session: AsyncSession,
        conversation: Conversation,
        request_id: str,
        tool_name: str,
        raw_input: dict,
    ) -> ToolExecution:
        definition = self.registry.get(tool_name)
        if definition is None:
            raise AppError(
                422, "unknown_tool", "The requested action is not registered"
            )
        validated = definition.input_schema.model_validate(raw_input)
        status = "pending_confirmation" if definition.requires_confirmation else "ready"
        execution = ToolExecution(
            conversation_id=conversation.id,
            request_id=request_id,
            tool_name=tool_name,
            status=status,
            input_json=validated.model_dump(mode="json"),
        )
        session.add(execution)
        await session.flush()
        if definition.requires_confirmation:
            conversation.state = {
                **conversation.state,
                "pending_action": {
                    "execution_id": str(execution.id),
                    "tool": tool_name,
                    "status": status,
                },
            }
            await session.flush()
        return execution

    async def execute(
        self,
        session: AsyncSession,
        execution_id: uuid.UUID,
        *,
        confirmed: bool,
    ) -> ToolExecution:
        execution = await session.get(ToolExecution, execution_id)
        if execution is None:
            raise AppError(
                404, "tool_execution_not_found", "Tool execution was not found"
            )
        definition = self.registry.get(execution.tool_name)
        if definition is None:
            raise AppError(
                409, "tool_unavailable", "The registered action is no longer available"
            )
        if definition.requires_confirmation and not confirmed:
            raise AppError(
                409, "confirmation_required", "Explicit confirmation is required"
            )
        validated_input = definition.input_schema.model_validate(execution.input_json)
        execution.status = "running"
        await session.flush()
        try:
            raw_output = await definition.handler(validated_input)
            output = definition.output_schema.model_validate(raw_output)
            execution.output_json = output.model_dump(mode="json")
            execution.status = "completed"
        except Exception:
            execution.status = "failed"
            await session.flush()
            raise
        await session.flush()
        return execution
