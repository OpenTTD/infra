import hashlib
import pulumi
import pulumi_cloudflare
import pulumi_github
import pulumi_openttd


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")

r2_survey = pulumi_cloudflare.R2Bucket(
    "r2",
    account_id=global_stack.get_output("cloudflare_account_id"),
    location="WEUR",
    name=f"survey-{pulumi_openttd.get_stack()}",
    opts=pulumi.ResourceOptions(protect=True),
)
r2_survey_packed = pulumi_cloudflare.R2Bucket(
    "r2-packed",
    account_id=global_stack.get_output("cloudflare_account_id"),
    location="WEUR",
    name=f"survey-packed-{pulumi_openttd.get_stack()}",
    opts=pulumi.ResourceOptions(protect=True),
)

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
r2_resources = pulumi.Output.all(
    account_id=global_stack.get_output("cloudflare_account_id"),
    r2_survey=r2_survey.name,
    r2_survey_packed=r2_survey_packed.name,
).apply(
    lambda kwargs: {
        f"com.cloudflare.edge.r2.bucket.{kwargs['account_id']}_default_{kwargs['r2_survey']}": "*",
        f"com.cloudflare.edge.r2.bucket.{kwargs['account_id']}_default_{kwargs['r2_survey_packed']}": "*",
    }
)

r2_api_token = pulumi_cloudflare.ApiToken(
    "r2-api-token",
    name="app/survey-web-r2",
    policies=[
        pulumi_cloudflare.ApiTokenPolicyArgs(
            resources=r2_resources,
            permission_groups=[
                permission_groups.permissions["Workers R2 Storage Bucket Item Write"],
            ],
        ),
    ],
)

resources = global_stack.get_output("cloudflare_account_id").apply(
    lambda account_id: {f"com.cloudflare.api.account.{account_id}": "*"}
)

api_token = pulumi_cloudflare.ApiToken(
    "api-token",
    name="app/survey-web",
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
    "github-secret-r2-access-key-id",
    repository="survey-web",
    secret_name="R2_SURVEY_ACCESS_KEY_ID",
    plaintext_value=r2_api_token.id,
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)
pulumi_github.ActionsSecret(
    "github-secret-r2-secret-access-key",
    repository="survey-web",
    secret_name="R2_SURVEY_SECRET_ACCESS_KEY",
    plaintext_value=r2_api_token.value.apply(lambda secret: hashlib.sha256(secret.encode()).hexdigest()),
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)
pulumi_github.ActionsSecret(
    "github-secret-r2-endpoint",
    repository="survey-web",
    secret_name="R2_SURVEY_ENDPOINT",
    plaintext_value=global_stack.get_output("cloudflare_account_id").apply(
        lambda account_id: f"https://{account_id}.r2.cloudflarestorage.com"
    ),
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)


pulumi_github.ActionsSecret(
    "github-secret-cloudflare-api-token",
    repository="survey-web",
    secret_name="CLOUDFLARE_API_TOKEN",
    plaintext_value=api_token.value,
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)
pulumi_github.ActionsSecret(
    "github-secret-cloudflare-account-id",
    repository="survey-web",
    secret_name="CLOUDFLARE_ACCOUNT_ID",
    plaintext_value=global_stack.get_output("cloudflare_account_id"),
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)
pulumi_github.ActionsVariable(
    "github-variable-cloudflare-project-name",
    repository="survey-web",
    variable_name="CLOUDFLARE_PROJECT_NAME",
    value=config.require("name"),
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)
