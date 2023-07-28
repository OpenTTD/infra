import pulumi
import pulumi_openttd


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")


pulumi_openttd.autotag.register()

sentry_key = pulumi_openttd.get_sentry_key(
    "dibridge", global_stack.get_output("sentry_ingest_hostname"), global_stack.get_output("domain")
)

SETTINGS = {
    "discord_channel_id": config.require("discord-channel-id"),
    "discord_token": config.require_secret("discord-token"),
    "irc_channel": config.require("irc-channel"),
    "irc_host": config.require("irc-host"),
    "irc_nick": config.require("irc-nick"),
    "memory_max": config.require("memory-max"),
    "memory": config.require("memory"),
    "sentry_dsn": sentry_key,
    "sentry_environment": config.require("sentry-environment"),
    "stack": pulumi.get_stack(),
}

service = pulumi_openttd.NomadService(
    "dibridge",
    pulumi_openttd.NomadServiceArgs(
        dependencies=[],
        repository="dibridge",
        service="dibridge",
        settings=SETTINGS,
    ),
)
