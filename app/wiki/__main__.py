import pulumi
import pulumi_aws
import pulumi_nomad

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


VARIABLES = {
    "version": ":dev",
    "sentry_dsn": "",
    "storage_github_app_id": "",
    "storage_github_app_key": "",
    "user_github_client_id": "",
    "user_github_client_secret": "",
    "reload_secret": "",
}

SETTINGS = {
    "storage_github_url": "https://github-proxy.openttd.org/OpenTTD/wiki-data-staging",
    "storage_github_history_url": "https://github-proxy.openttd.org/OpenTTD/wiki-data-staging",
    "storage_github_api_url": "https://github-api-proxy.openttd.org",
    "user_github_api_url": "https://github-api-proxy.openttd.org",
    "user_github_url": "https://github-proxy.openttd.org",
    "frontend_url": global_stack.get_output("domain").apply(lambda domain: f"https://{config.require('hostname')}.{domain}"),
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

job = pulumi_nomad.Job(
    "wiki",
    jobspec=open("files/wiki.nomad").read(),
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

for name, value in SETTINGS.items():
    variables.Variable(
        f"setting-{name}",
        variables.VariableArgs(
            job="wiki",
            name=name,
            value=value,
        ),
        opts=pulumi.ResourceOptions(parent=job),
    )
