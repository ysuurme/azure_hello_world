import sys

import src.config as config
from src.utils.m_ai_client import ClientManager
from src.utils.m_log import f_log


def run_health_check() -> None:
    """Run a health check on the AI Foundry project connectivity.

    Validates:
    1. AZURE_AAIF_PROJECT_ENDPOINT is set.
    2. AIProjectClient can be initialized.
    3. Azure authentication is working (DefaultAzureCredential).
    4. Minimal inference health check (send a simple prompt, assert non-empty response).
    """
    f_log("Starting AI Foundry health check...", level="process")

    # 1. Check AZURE_AAIF_PROJECT_ENDPOINT
    if not config.AZURE_AAIF_PROJECT_ENDPOINT:
        f_log("AZURE_AAIF_PROJECT_ENDPOINT is not set in environment or .env", level="error")
        sys.exit(1)

    try:
        cm = ClientManager()

        # 2. Check AIProjectClient initialization
        f_log("Initializing AIProjectClient...", level="process")
        project_client = cm.get_aiproject_client()
        f_log("AIProjectClient initialized successfully.", level="success")

        # 3. Validate deployments (Optional validation of requirement 3 if SDK supports it)
        try:
            f_log("Attempting to list model deployments...", level="process")
            # Try to list deployments if the SDK version supports it via 'inference'
            if hasattr(project_client, "inference"):
                # Note: In newer versions this might be get_deployments()
                get_deployments = getattr(project_client.inference, "get_deployments", None)
                if not get_deployments:
                    get_deployments = getattr(project_client.inference, "list_deployments", None)

                if callable(get_deployments):
                    deployments = get_deployments()
                    active_deployments = [d.name for d in deployments]
                    f_log(f"Active deployments found: {', '.join(active_deployments)}", level="debug")

                    missing_models = []
                    for agent, model_name in config.AGENT_MODELS.items():
                        if model_name not in active_deployments:
                            missing_models.append(f"{agent}: {model_name}")

                    if missing_models:
                        f_log(f"Models missing from project: {', '.join(missing_models)}", level="error")
                    else:
                        f_log("All configured models found in project deployments.", level="success")
                else:
                    f_log("SDK 'inference' has no recognized list/get deployments method.", level="process")
            else:
                f_log("SDK does not expose 'inference'; skipping deployment list.", level="process")
        except Exception as e:
            f_log(f"Could not list deployments (Requirement 3 check skipped): {e}", level="debug")

        # 4. Minimal inference health check (Requirement 4)
        model_name = config.AGENT_MODELS["intake_reviewer"]
        f_log(f"Testing inference with model: {model_name}...", level="process")

        # Note: openai_client from AIProjectClient is used as a context manager
        with cm.get_openai_client() as openai_client:
            # We use max_completion_tokens for compatibility with newer models (e.g. O1, GPT-5-mini)
            # while falling back to max_tokens for older ones if needed, but the error suggested max_completion_tokens.
            try:
                response = openai_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": "Hello, this is a health check. Reply with 'OK'."}],
                    max_completion_tokens=10,
                )
            except Exception as e:
                if "max_completion_tokens" in str(e):
                    # Fallback to max_tokens if max_completion_tokens is not supported by the client SDK
                    response = openai_client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": "Hello, this is a health check. Reply with 'OK'."}],
                        max_tokens=10,
                    )
                else:
                    raise e

            content = response.choices[0].message.content.strip()
            if content:
                f_log(f"Received response: {content}", level="success")
                f_log("Health check passed!", level="success")
            else:
                f_log("Received empty response from LLM.", level="error")
                sys.exit(1)

    except Exception as e:
        f_log(f"Health check failed: {e}", level="error")
        # If the failure is due to missing deployment, let the user know
        if "DeploymentNotFound" in str(e) or "404" in str(e):
            f_log("Ensure model deployments in AI Foundry match config.py:AGENT_MODELS", level="debug")
        sys.exit(1)


if __name__ == "__main__":
    run_health_check()
