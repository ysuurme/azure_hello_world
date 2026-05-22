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
        from src.agents.design_architecture import DesignArchitectureModule
        from src.agents.diagram_studio import DiagramStudioModule

        self._modules: dict[str, object] = {
            "/design": DesignArchitectureModule(client_manager=client_manager),
            "/diagram": DiagramStudioModule(client_manager=client_manager),
        }

    def dispatch(self, user_input: str, session_state: dict) -> DispatchResult:
        command = user_input.split()[0].lower()

        if command == "/help":
            return self._handle_help(session_state)
        if command == "/exit":
            return self._clear_active_module(session_state)
        if command in self._modules:
            return self._invoke_module(command, user_input, session_state)
        if command.startswith("/"):
            return self._handle_unknown_command(command, session_state)

        active = session_state.get("active_module")
        if active and active in self._modules:
            return self._invoke_module(active, user_input, session_state)
        return DispatchResult(
            response_text=self._build_help_table(),
            updated_state=session_state,
            status="unknown_command",
        )

    def _build_help_table(self) -> str:
        rows = ["| Slash Command | Module | Description |", "|---|---|---|"]
        for cmd, module in self._modules.items():
            name = getattr(module, "name", cmd)
            desc = getattr(module, "description", "")
            rows.append(f"| `{cmd}` | {name} | {desc} |")
        return "\n".join(rows)

    def _handle_help(self, session_state: dict) -> DispatchResult:
        return DispatchResult(
            response_text=self._build_help_table(),
            updated_state=session_state,
            status="completed",
        )

    def _clear_active_module(self, session_state: dict) -> DispatchResult:
        updated = dict(session_state)
        active = updated.pop("active_module", None)
        if active and "module_state" in updated:
            updated["module_state"] = dict(updated["module_state"])
            updated["module_state"].pop(active, None)
        msg = "Session cleared. Type `/help` to see available commands." if active else "No active module to exit."
        return DispatchResult(response_text=msg, updated_state=updated, status="completed")

    def _handle_unknown_command(self, command: str, session_state: dict) -> DispatchResult:
        return DispatchResult(
            response_text=f"Unknown command: `{command}`.\n\n{self._build_help_table()}",
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
