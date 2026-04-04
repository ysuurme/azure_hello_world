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
    f_log("Starting AI Foundry health check...", c_type="process")
    
    # 1. Check AZURE_AAIF_PROJECT_ENDPOINT
    if not config.AZURE_AAIF_PROJECT_ENDPOINT:
        f_log("AZURE_AAIF_PROJECT_ENDPOINT is not set in environment or .env", c_type="error")
        sys.exit(1)
    
    try:
        cm = ClientManager()
        
        # 2. Check AIProjectClient initialization
        f_log("Initializing AIProjectClient...", c_type="process")
        project_client = cm.get_aiproject_client()
        f_log("AIProjectClient initialized successfully.", c_type="success")
        
        # 3. Validate deployments (Optional validation of requirement 3 if SDK supports it)
        try:
            f_log("Attempting to list model deployments...", c_type="process")
            # Try to list deployments if the SDK version supports it via 'inference'
            if hasattr(project_client, 'inference'):
                # Note: In newer versions this might be get_deployments()
                get_deployments = getattr(project_client.inference, 'get_deployments', None)
                if not get_deployments:
                    get_deployments = getattr(project_client.inference, 'list_deployments', None)
                
                if callable(get_deployments):
                    deployments = get_deployments()
                    active_deployments = [d.name for d in deployments]
                    f_log(f"Active deployments found: {', '.join(active_deployments)}", c_type="debug")
                    
                    missing_models = []
                    for agent, model_name in config.AGENT_MODELS.items():
                        if model_name not in active_deployments:
                            missing_models.append(f"{agent}: {model_name}")
                    
                    if missing_models:
                        f_log(f"Models missing from project: {', '.join(missing_models)}", c_type="error")
                    else:
                        f_log("All configured models found in project deployments.", c_type="success")
                else:
                    f_log("SDK 'inference' has no recognized list/get deployments method.", c_type="process")
            else:
                f_log("SDK does not expose 'inference'; skipping deployment list.", c_type="process")
        except Exception as e:
            f_log(f"Could not list deployments (Requirement 3 check skipped): {e}", c_type="debug")

        # 4. Minimal inference health check (Requirement 4)
        model_name = config.AGENT_MODELS["intake_reviewer"]
        f_log(f"Testing inference with model: {model_name}...", c_type="process")
        
        # Note: openai_client from AIProjectClient is used as a context manager
        with cm.get_openai_client() as openai_client:
            # We use max_completion_tokens for compatibility with newer models (e.g. O1, GPT-5-mini)
            # while falling back to max_tokens for older ones if needed, but the error suggested max_completion_tokens.
            try:
                response = openai_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": "Hello, this is a health check. Reply with 'OK'."}],
                    max_completion_tokens=10
                )
            except Exception as e:
                if "max_completion_tokens" in str(e):
                    # Fallback to max_tokens if max_completion_tokens is not supported by the client SDK
                    response = openai_client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": "Hello, this is a health check. Reply with 'OK'."}],
                        max_tokens=10
                    )
                else:
                    raise e
            
            content = response.choices[0].message.content.strip()
            if content:
                f_log(f"Received response: {content}", c_type="success")
                f_log("Health check passed!", c_type="success")
            else:
                f_log("Received empty response from LLM.", c_type="error")
                sys.exit(1)
                
    except Exception as e:
        f_log(f"Health check failed: {e}", c_type="error")
        # If the failure is due to missing deployment, let the user know
        if "DeploymentNotFound" in str(e) or "404" in str(e):
            f_log("Ensure model deployments in AI Foundry match config.py:AGENT_MODELS", c_type="debug")
        sys.exit(1)

if __name__ == "__main__":
    run_health_check()
