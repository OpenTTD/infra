import pulumi
import pulumi_cloudflare
import pulumi_github
import pulumi_random
import pulumi_openttd


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")
aws_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/aws-core/prod")
cloudflare_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/cloudflare-core/prod")


pulumi_openttd.autotag.register()

reload_secret = pulumi_random.RandomPassword(
    "reload-secret",
    length=32,
    special=False,
)
frontend_url = pulumi.Output.format("https://{}.{}", config.require("hostname"), global_stack.get_output("domain"))
sentry_key = pulumi_openttd.get_sentry_key(
    "wiki", global_stack.get_output("sentry_ingest_hostname"), global_stack.get_output("domain")
)

SETTINGS = {
    "frontend_url": frontend_url,
    "memory": config.require("memory"),
    "memory_max": config.require("memory-max"),
    "port": config.require("port"),
    "reload_secret": reload_secret.result,
    "sentry_dsn": sentry_key,
    "sentry_environment": config.require("sentry-environment"),
    "stack": pulumi.get_stack(),
    "storage_github_app_id": config.require("storage-github-app-id"),
    "storage_github_app_key": config.require_secret("storage-github-app-key"),
    "storage_github_history_url": config.require("storage-github-history-url"),
    "storage_github_url": config.require("storage-github-url"),
    "user_github_client_id": config.require("user-github-client-id"),
    "user_github_client_secret": config.require_secret("user-github-client-secret"),
}

volume = pulumi_openttd.VolumeEfs(
    f"volume-cache",
    pulumi_openttd.VolumeEfsArgs(
        name=f"wiki-{pulumi.get_stack()}-cache",
        subnet_arns=aws_core_stack.get_output("private_subnet_arns"),
        subnet_ids=aws_core_stack.get_output("private_subnet_ids"),
        security_group_arn=aws_core_stack.get_output("nomad_security_group_arn"),
        security_group_id=aws_core_stack.get_output("nomad_security_group_id"),
        s3_datasync_arn=aws_core_stack.get_output("s3_datasync_arn"),
        s3_datasync_iam_arn=aws_core_stack.get_output("s3_datasync_iam_arn"),
    ),
)

service = pulumi_openttd.NomadService(
    "wiki",
    pulumi_openttd.NomadServiceArgs(
        service="wiki",
        settings=SETTINGS,
        dependencies=[volume],
        repository="TrueWiki",
    ),
)

pulumi_cloudflare.PageRule(
    "page-rule",
    actions=pulumi_cloudflare.PageRuleActionsArgs(
        cache_level="aggressive",
    ),
    target=pulumi.Output.format("{}.{}/*", config.require("hostname"), global_stack.get_output("domain")),
    zone_id=global_stack.get_output("cloudflare_zone_id"),
    opts=pulumi.ResourceOptions(ignore_changes=["priority"]),
)

pulumi.export("reload_secret", reload_secret.result)
pulumi.export("nomad_service_key", service.nomad_service_key.result)
