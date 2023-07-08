import pulumi
import pulumi_cloudflare
import pulumi_github


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")

if pulumi.get_stack() == "prod":
    project = pulumi_cloudflare.PagesProject(
        "pages",
        account_id=global_stack.get_output("cloudflare_account_id"),
        name=config.require("name"),
        production_branch="main",
    )

    permission_groups = pulumi_cloudflare.get_api_token_permission_groups()
    resources = global_stack.get_output("cloudflare_account_id").apply(
        lambda account_id: {f"com.cloudflare.api.account.{account_id}": "*"}
    )

    api_token = pulumi_cloudflare.ApiToken(
        "api-token",
        name="app/preview",
        policies=[
            pulumi_cloudflare.ApiTokenPolicyArgs(
                resources=resources,
                permission_groups=[
                    permission_groups.account["Pages Write"],
                ],
            ),
        ],
    )

    pulumi_github.ActionsSecret(
        "github-secret-cloudflare-api-token",
        repository="OpenTTD",
        secret_name="PREVIEW_CLOUDFLARE_API_TOKEN",
        plaintext_value=api_token.value,
        opts=pulumi.ResourceOptions(delete_before_replace=True),
    )

    pulumi_github.ActionsSecret(
        "github-secret-cloudflare-account-id",
        repository="OpenTTD",
        secret_name="PREVIEW_CLOUDFLARE_ACCOUNT_ID",
        plaintext_value=global_stack.get_output("cloudflare_account_id"),
        opts=pulumi.ResourceOptions(delete_before_replace=True),
    )

    pulumi_github.ActionsVariable(
        "github-variable-cloudflare-project-name",
        repository="OpenTTD",
        variable_name="PREVIEW_CLOUDFLARE_PROJECT_NAME",
        value=config.require("name"),
        opts=pulumi.ResourceOptions(delete_before_replace=True),
    )

name = f"preview-{pulumi.get_stack()}"
worker = pulumi_cloudflare.WorkerScript(
    f"worker",
    account_id=global_stack.get_output("cloudflare_account_id"),
    content=open(f"files/cfw-preview.js").read().replace("[[ name ]]", config.require("name")),
    logpush=True,
    name=name,
    module=True,
)

pulumi_cloudflare.WorkerDomain(
    f"worker-domain",
    account_id=global_stack.get_output("cloudflare_account_id"),
    hostname=pulumi.Output.format("{}.{}", config.require("hostname"), global_stack.get_output("domain")),
    service=name,
    zone_id=global_stack.get_output("cloudflare_zone_id"),
    opts=pulumi.ResourceOptions(parent=worker),
)
