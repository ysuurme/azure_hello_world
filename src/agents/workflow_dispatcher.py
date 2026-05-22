from __future__ import annotations

from dataclasses import dataclass, field

from src.utils.m_log import f_log


@dataclass
class DispatchResult:
    response_text: str
    updated_state: dict
    artifacts: dict = field(default_factory=dict)
    status: str = "completed"


class WorkflowDispatcher:
    """Routes slash-command input to the matching registered capability module."""

    def __init__(self, client_manager) -> None:
        from src.agents.diagram_studio import DiagramStudioModule

        self._modules: dict[str, object] = {
            "/diagram": DiagramStudioModule(client_manager=client_manager),
        }

    def dispatch(self, user_input: str, session_state: dict) -> DispatchResult:
        command = user_input.split()[0].lower()

        if command not in self._modules:
            return self._route_to_active_or_unknown(command, user_input, session_state)

        return self._invoke_module(command, user_input, session_state)

    def _route_to_active_or_unknown(self, command: str, user_input: str, session_state: dict) -> DispatchResult:
        active = session_state.get("active_module")
        if active and active in self._modules:
            return self._invoke_module(active, user_input, session_state)
        known = ", ".join(self._modules.keys())
        return DispatchResult(
            response_text=f"Unknown command `{command}`. Available: {known}.",
            updated_state=session_state,
            status="unknown_command",
        )

    def _invoke_module(self, command: str, user_input: str, session_state: dict) -> DispatchResult:
        module = self._modules[command]
        module_state = session_state.get("module_state", {}).get(command, {})
        try:
            response = module.handle(user_input, module_state)
        except Exception as e:
            f_log(f"Module {command} raised an exception: {e}", level="error")
            return DispatchResult(
                response_text=f"Module error in `{command}`: {e}",
                updated_state=session_state,
                status="error",
            )
        updated = dict(session_state)
        updated["active_module"] = command
        updated.setdefault("module_state", {})[command] = response.updated_state
        return DispatchResult(
            response_text=response.response_text,
            updated_state=updated,
            artifacts=response.artifacts,
            status=response.status,
        )
