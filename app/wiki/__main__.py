import pulumi
import pulumi_nomad
import pulumi_random
import pulumi_openttd


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")
aws_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/aws-core/prod")


pulumi_openttd.autotag.register()

VARIABLES = {
    "sentry_dsn": "",
    "storage_github_app_id": "",
    "storage_github_app_key": "",
    "user_github_client_id": "",
    "user_github_client_secret": "",
    "version": ":dev",
}

SETTINGS = {
    "memory": config.require("memory"),
    "name": config.require("name"),
    "sentry_environment": config.require("sentry-environment"),
    "storage_github_history_url": config.require("storage-github-url"),
    "storage_github_url": config.require("storage-github-url"),
    "frontend_url": pulumi.Output.format(
        "https://{}.{}", config.require("hostname"), global_stack.get_output("domain")
    ),
    "reload_secret": pulumi_random.RandomString(
        "wiki-reload-secret",
        length=32,
        special=False,
    ).result,
}

volume = pulumi_openttd.VolumeEfs(
    f"{config.require('name')}-cache",
    pulumi_openttd.VolumeEfsArgs(
        subnet_ids=aws_core_stack.get_output("subnet_ids"),
    ),
)

job = pulumi_nomad.Job(
    config.require("name"),
    jobspec=pulumi_openttd.get_jobspec("files/wiki.nomad", SETTINGS),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
    opts=pulumi.ResourceOptions(depends_on=[volume]),
)

for key, value in VARIABLES.items():
    pulumi_openttd.NomadVariable(
        f"variable-{key}",
        pulumi_openttd.NomadVariableArgs(
            job=config.require("name"),
            name=key,
            value=value,
            overwrite_if_exists=False,
        ),
        opts=pulumi.ResourceOptions(parent=job),
    )
