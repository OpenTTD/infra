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

sentry_key = pulumi_openttd.get_sentry_key(
    "dorpsgek", global_stack.get_output("sentry_ingest_hostname"), global_stack.get_output("domain")
)

channels = ""
for channel in config.require("channels").split(";"):
    channels += f'"--channel", "{channel}",'

SETTINGS = {
    "addressed_by": config.require("addressed-by"),
    "channels": channels,
    "discord_unfiltered_webhook_url": config.require_secret("discord-unfiltered-webhook-url"),
    "discord_webhook_url": config.require_secret("discord-webhook-url"),
    "github_app_id": config.require("github-app-id"),
    "github_app_private_key": config.require_secret("github-app-private-key"),
    "github_app_webhook_secret": config.require_secret("github-app-webhook-secret"),
    "irc_username": config.require("irc-username"),
    "memory_max": config.require("memory-max"),
    "memory": config.require("memory"),
    "nickserv_password": config.require_secret("nickserv-password"),
    "port": config.require("port"),
    "sentry_dsn": sentry_key,
    "sentry_environment": config.require("sentry-environment"),
    "stack": pulumi.get_stack(),
}

volume = pulumi_openttd.VolumeEfs(
    f"volume-cache",
    pulumi_openttd.VolumeEfsArgs(
        name=f"dorpsgek-{pulumi.get_stack()}",
        subnet_arns=aws_core_stack.get_output("private_subnet_arns"),
        subnet_ids=aws_core_stack.get_output("private_subnet_ids"),
        security_group_arn=aws_core_stack.get_output("nomad_security_group_arn"),
        security_group_id=aws_core_stack.get_output("nomad_security_group_id"),
        s3_datasync_arn=aws_core_stack.get_output("s3_datasync_arn"),
        s3_datasync_iam_arn=aws_core_stack.get_output("s3_datasync_iam_arn"),
    ),
)

service = pulumi_openttd.NomadService(
    "dorpsgek",
    pulumi_openttd.NomadServiceArgs(
        service="dorpsgek",
        settings=SETTINGS,
        dependencies=[volume],
        repository="Dorpsgek",
    ),
)

name = f"weblogs-{pulumi.get_stack()}"
worker = pulumi_cloudflare.WorkerScript(
    f"worker",
    account_id=global_stack.get_output("cloudflare_account_id"),
    content=global_stack.get_output("domain").apply(
        lambda domain: open(f"files/cfw-weblogs.js")
        .read()
        .replace("[[ hostname ]]", config.require("hostname"))
        .replace("[[ domain ]]", domain)
    ),
    logpush=True,
    name=name,
    module=True,
)

pulumi_cloudflare.WorkerDomain(
    f"worker-domain",
    account_id=global_stack.get_output("cloudflare_account_id"),
    hostname=pulumi.Output.format("{}.{}", config.require("weblogs-hostname"), global_stack.get_output("domain")),
    service=name,
    zone_id=global_stack.get_output("cloudflare_zone_id"),
    opts=pulumi.ResourceOptions(parent=worker),
)
