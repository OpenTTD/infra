import pulumi
import pulumi_cloudflare
import pulumi_github


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")

project = pulumi_cloudflare.PagesProject(
    "pages",
    account_id=global_stack.get_output("cloudflare_account_id"),
    name=config.require("name"),
    production_branch="main",
)

record = pulumi_cloudflare.PagesDomain(
    "pages-domain",
    account_id=global_stack.get_output("cloudflare_account_id"),
    domain=pulumi.Output.format("{}.{}", config.require("hostname"), global_stack.get_output("domain")),
    project_name=config.require("name"),
    opts=pulumi.ResourceOptions(depends_on=[project]),
)

pulumi_cloudflare.Record(
    "record",
    name=config.require("hostname"),
    proxied=True,
    type="CNAME",
    value=project.subdomain,
    zone_id=global_stack.get_output("cloudflare_zone_id"),
    opts=pulumi.ResourceOptions(depends_on=[record]),
)

permission_groups = pulumi_cloudflare.get_api_token_permission_groups()
resources = global_stack.get_output("cloudflare_account_id").apply(
    lambda account_id: {f"com.cloudflare.api.account.{account_id}": "*"}
)

api_token = pulumi_cloudflare.ApiToken(
    "api-token",
    name="app/website",
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
    repository="website",
    secret_name="CLOUDFLARE_API_TOKEN",
    plaintext_value=api_token.value,
)

pulumi_github.ActionsSecret(
    "github-secret-cloudflare-account-id",
    repository="website",
    secret_name="CLOUDFLARE_ACCOUNT_ID",
    plaintext_value=global_stack.get_output("cloudflare_account_id"),
)

pulumi_github.ActionsVariable(
    "github-variable-cloudflare-project-name",
    repository="website",
    variable_name="CLOUDFLARE_PROJECT_NAME",
    value=config.require("name"),
)
