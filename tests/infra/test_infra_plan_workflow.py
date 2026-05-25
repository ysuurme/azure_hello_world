"""Content tests for the infra-plan.yml CI workflow.

Validates that the Terraform plan gate is configured with correct OIDC auth,
path triggers, exit-code semantics, and sticky PR comment behaviour.
"""

from pathlib import Path

WORKFLOW = Path(__file__).parent.parent.parent / ".github" / "workflows" / "infra-plan.yml"


def _content() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


# --- File presence -----------------------------------------------------------


def test_workflow_file_exists() -> None:
    assert WORKFLOW.exists(), "infra-plan.yml must exist in .github/workflows/"


# --- Trigger configuration ---------------------------------------------------


def test_triggers_on_pull_request() -> None:
    assert "pull_request:" in _content(), "workflow must trigger on pull_request"


def test_path_filter_infra() -> None:
    assert "'infra/**'" in _content() or "- 'infra/**'" in _content() or "infra/**" in _content(), (
        "workflow must path-filter on infra/**"
    )


def test_targets_master_branch() -> None:
    assert "master" in _content(), "workflow must target the master branch"


# --- OIDC permissions --------------------------------------------------------


def test_id_token_write_permission() -> None:
    assert "id-token: write" in _content(), "workflow must declare id-token: write to allow OIDC token issuance"


def test_pull_requests_write_permission() -> None:
    assert "pull-requests: write" in _content(), "workflow must declare pull-requests: write to post PR comments"


# --- No client secret --------------------------------------------------------


def test_no_azure_client_secret() -> None:
    assert "AZURE_CLIENT_SECRET" not in _content(), (
        "workflow must not reference AZURE_CLIENT_SECRET — auth must be OIDC-only"
    )


def test_no_client_secret_input() -> None:
    assert "client-secret" not in _content(), "azure/login must not use client-secret — auth must be OIDC-only"


# --- Azure OIDC auth ---------------------------------------------------------


def test_azure_login_step_present() -> None:
    assert "azure/login" in _content(), "workflow must use azure/login for OIDC authentication"


def test_arm_use_oidc_set() -> None:
    assert 'ARM_USE_OIDC: "true"' in _content() or "ARM_USE_OIDC: 'true'" in _content(), (
        "ARM_USE_OIDC must be set to true for the azurerm provider to use OIDC"
    )


def test_arm_subscription_id_exported() -> None:
    assert "ARM_SUBSCRIPTION_ID" in _content(), (
        "ARM_SUBSCRIPTION_ID must be exported (required by azurerm v4 at plan time)"
    )


def test_arm_client_id_exported() -> None:
    assert "ARM_CLIENT_ID" in _content(), "ARM_CLIENT_ID must be exported for OIDC auth"


def test_arm_tenant_id_exported() -> None:
    assert "ARM_TENANT_ID" in _content(), "ARM_TENANT_ID must be exported for OIDC auth"


# --- Terraform steps ---------------------------------------------------------


def test_setup_terraform_step() -> None:
    assert "hashicorp/setup-terraform" in _content(), "workflow must install Terraform via hashicorp/setup-terraform"


def test_terraform_wrapper_disabled() -> None:
    assert "terraform_wrapper: false" in _content(), (
        "terraform_wrapper must be false so PIPESTATUS captures the raw exit code from terraform plan"
    )


def test_terraform_init_chdir() -> None:
    assert "terraform -chdir=infra init" in _content(), "terraform init must use -chdir=infra"


def test_terraform_plan_detailed_exitcode() -> None:
    assert "-detailed-exitcode" in _content(), (
        "terraform plan must use -detailed-exitcode to distinguish no-change/changes/error"
    )


def test_terraform_plan_no_color() -> None:
    assert "-no-color" in _content(), "terraform plan must use -no-color for clean PR comment output"


def test_terraform_plan_chdir() -> None:
    assert "terraform -chdir=infra plan" in _content(), "terraform plan must use -chdir=infra"


# --- Exit-code semantics -----------------------------------------------------


def test_exit_code_captured() -> None:
    assert "PLAN_EXIT" in _content(), "plan exit code must be captured for conditional failure logic"


def test_exit_1_fails_job() -> None:
    # The workflow must explicitly fail on exit 1 (plan error)
    assert "exit 1" in _content(), "exit code 1 (plan error) must cause the job to fail"


# --- Sticky PR comment -------------------------------------------------------


def test_pr_comment_step_present() -> None:
    assert "github-script" in _content() or "actions/github-script" in _content(), (
        "workflow must post a PR comment via actions/github-script"
    )


def test_comment_marker_for_stickiness() -> None:
    assert "terraform-plan" in _content(), (
        "a unique marker must be used to find and update the existing comment rather than creating a new one"
    )


def test_comment_updates_existing() -> None:
    assert "updateComment" in _content(), (
        "workflow must update an existing plan comment on subsequent pushes (sticky comment)"
    )


def test_comment_creates_if_absent() -> None:
    assert "createComment" in _content(), "workflow must create a new comment when none exists yet"


def test_comment_step_runs_always() -> None:
    assert "if: always()" in _content(), (
        "the PR comment step must run even when the plan step fails, so errors are visible in the PR"
    )
