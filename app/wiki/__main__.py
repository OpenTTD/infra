import pulumi
import pulumi_cloudflare
import pulumi_random
import pulumi_openttd


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")
aws_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/aws-core/prod")
cloudflare_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/cloudflare-core/prod")


pulumi_openttd.autotag.register()

reload_secret = pulumi_random.RandomString(
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
        subnet_ids=aws_core_stack.get_output("private_subnet_ids"),
    ),
)

pulumi_openttd.NomadService(
    "wiki",
    pulumi_openttd.NomadServiceArgs(
        service="wiki",
        settings=SETTINGS,
        dependencies=[volume],
        service_token_id=cloudflare_core_stack.get_output("service_token_id"),
        service_token_secret=cloudflare_core_stack.get_output("service_token_secret"),
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
)
