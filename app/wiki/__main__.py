import base64
import pulumi
import pulumi_nomad
import pulumi_random
import pulumi_openttd


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")
aws_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/aws-core/prod")


pulumi_openttd.autotag.register()

reload_secret = pulumi_random.RandomString(
    "reload-secret",
    length=32,
    special=False,
)
frontend_url = pulumi.Output.format("https://{}.{}", config.require("hostname"), global_stack.get_output("domain"))

SETTINGS = {
    "frontend_url": frontend_url,
    "memory": config.require("memory"),
    "reload_secret": reload_secret.result,
    "sentry_dsn": "",
    "sentry_environment": config.require("sentry-environment"),
    "stack": pulumi.get_stack(),
    "storage_github_app_id": "",
    "storage_github_app_key": "",
    "storage_github_history_url": config.require("storage-github-url"),
    "storage_github_url": config.require("storage-github-url"),
    "user_github_client_id": "",
    "user_github_client_secret": "",
}

volume = pulumi_openttd.VolumeEfs(
    f"volume-cache",
    pulumi_openttd.VolumeEfsArgs(
        name=f"wiki-{pulumi.get_stack()}-cache",
        subnet_ids=aws_core_stack.get_output("subnet_ids"),
    ),
)

variables = {}
for key, value in SETTINGS.items():
    variables[key] = pulumi_openttd.NomadVariable(
        f"setting-{key}",
        pulumi_openttd.NomadVariableArgs(
            path=f"app/wiki-{pulumi.get_stack()}/settings",
            name=key,
            value=value,
            overwrite_if_exists=True,
        ),
    )

variables["version"] = pulumi_openttd.NomadVariable(
    "version",
    pulumi_openttd.NomadVariableArgs(
        path=f"app/wiki-{pulumi.get_stack()}/version",
        name="version",
        value=":dev",  # Just the initial value.
        overwrite_if_exists=False,
    ),
)

jobspec = open("files/wiki.nomad", "rb").read()
pulumi_openttd.NomadVariable(
    f"jobspec",
    pulumi_openttd.NomadVariableArgs(
        path=f"app/wiki-{pulumi.get_stack()}/jobspec",
        name="jobspec",
        value=base64.b64encode(jobspec).decode(),
        overwrite_if_exists=True,
    ),
)

job = pulumi_nomad.Job(
    "job",
    jobspec=pulumi_openttd.get_jobspec(jobspec.decode(), variables),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
    opts=pulumi.ResourceOptions(depends_on=[volume, *variables.values()]),
)

jobspec_deploy = open("files/deploy.nomad", "rb").read().decode()
jobspec_deploy = jobspec_deploy.replace("[[ stack ]]", pulumi.get_stack())

job = pulumi_nomad.Job(
    "job-deploy",
    jobspec=jobspec_deploy,
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)
