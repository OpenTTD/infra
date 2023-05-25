import pulumi
import pulumi_aws
import pulumi_nomad
import pulumi_random

import autotag
import variables

config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")
aws_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/aws-core/prod")


autotag.register(
    {
        "Managed-By": "Pulumi",
    }
)

secret = pulumi_random.RandomString(
    f"wiki-reload-secret",
    length=32,
    special=False,
)


VARIABLES = {
    "sentry_dsn": "",
    "storage_github_app_id": "",
    "storage_github_app_key": "",
    "user_github_client_id": "",
    "user_github_client_secret": "",
    "version": ":dev",
}

SETTINGS = {
    "frontend_url": pulumi.Output.format(
        "https://{}.{}", config.require("hostname"), global_stack.get_output("domain")
    ),
    "memory": config.require("memory"),
    "reload_secret": secret.result,
    "sentry_environment": config.require("sentry-environment"),
    "storage_github_history_url": config.require("storage-github-url"),
    "storage_github_url": config.require("storage-github-url"),
}


def mount_target(efs, subnet_ids):
    for subnet_id in subnet_ids:
        pulumi_aws.efs.MountTarget(
            f"wiki-cache-mount-{subnet_id}",
            file_system_id=efs.id,
            subnet_id=subnet_id,
            opts=pulumi.ResourceOptions(parent=efs),
        )


efs = pulumi_aws.efs.FileSystem(
    "wiki-cache",
)
aws_core_stack.get_output("subnet_ids").apply(lambda subnet_ids: mount_target(efs, subnet_ids))

volume = pulumi_nomad.Volume(
    "wiki-cache",
    capabilities=[
        pulumi_nomad.VolumeCapabilityArgs(
            access_mode="multi-node-multi-writer",
            attachment_mode="file-system",
        ),
    ],
    external_id=efs.id,
    plugin_id="aws-efs0",
    type="csi",
    volume_id="wiki-cache",
    opts=pulumi.ResourceOptions(parent=efs),
)


def replace_settings(jobspec, **settings):
    for key, value in settings.items():
        jobspec = jobspec.replace(f"[[ {key} ]]", str(value))
    return jobspec


jobspec = pulumi.Output.from_input(open("files/wiki.nomad").read())
jobspec = pulumi.Output.all(jobspec=jobspec, **SETTINGS).apply(
    lambda args: replace_settings(**args), run_with_unknowns=True
)

job = pulumi_nomad.Job(
    "wiki",
    jobspec=jobspec,
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
    opts=pulumi.ResourceOptions(depends_on=[volume]),
)

for name, value in VARIABLES.items():
    variables.Variable(
        f"variable-{name}",
        variables.VariableArgs(
            job="wiki",
            name=name,
            value=value,
            overwrite_if_exists=False,
        ),
        opts=pulumi.ResourceOptions(parent=job),
    )
