import pulumi
import pulumi_github
import pulumi_random
import pulumi_openttd


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")
aws_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/aws-core/prod")
cloudflare_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/cloudflare-core/prod")


pulumi_openttd.autotag.register()

translators_password = pulumi_random.RandomPassword(
    "translators-password",
    length=32,
    special=False,
)
sentry_key = pulumi_openttd.get_sentry_key(
    "eints", global_stack.get_output("sentry_ingest_hostname"), global_stack.get_output("domain")
)

SETTINGS = {
    "memory": config.require("memory"),
    "memory_max": config.require("memory-max"),
    "port": config.require("port"),
    "sentry_dsn": sentry_key,
    "sentry_environment": config.require("sentry-environment"),
    "stack": pulumi_openttd.get_stack(),
    "github_org_api_token": config.require_secret("github-org-api-token"),
    "github_oauth2_client_id": config.require("github-oauth2-client-id"),
    "github_oauth2_client_secret": config.require_secret("github-oauth2-client-secret"),
    "translators_password": translators_password.result,
}

volume = pulumi_openttd.VolumeEfs(
    f"volume-cache",
    pulumi_openttd.VolumeEfsArgs(
        name=f"eints-{pulumi_openttd.get_stack()}",
        subnet_arns=aws_core_stack.get_output("private_subnet_arns"),
        subnet_ids=aws_core_stack.get_output("private_subnet_ids"),
        security_group_arn=aws_core_stack.get_output("nomad_security_group_arn"),
        security_group_id=aws_core_stack.get_output("nomad_security_group_id"),
        s3_datasync_arn=aws_core_stack.get_output("s3_datasync_arn"),
        s3_datasync_iam_arn=aws_core_stack.get_output("s3_datasync_iam_arn"),
    ),
)

service = pulumi_openttd.NomadService(
    "eints",
    pulumi_openttd.NomadServiceArgs(
        service="eints",
        settings=SETTINGS,
        dependencies=[volume],
        repository="eints",
    ),
)

pulumi_github.ActionsSecret(
    f"github-secret-translators-password",
    repository=config.require("workflow-github-url").split("/")[-1],
    secret_name=f"TRANSLATORS_{pulumi_openttd.get_stack().upper()}",
    plaintext_value=translators_password.result,
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)
