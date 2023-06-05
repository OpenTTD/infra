import base64
import pulumi
import pulumi_cloudflare
import pulumi_github
import pulumi_nomad
import pulumi_random
import pulumi_openttd
import pulumiverse_sentry


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
sentry_key = pulumiverse_sentry.get_sentry_key(
    organization="openttd",
    project="wiki",
)

# sentry.io doesn't support IPv6, so we route it via our own domain.
sentry_key = pulumi.Output.all(
    sentry_ingest_hostname=global_stack.get_output("sentry_ingest_hostname"),
    sentry_key=sentry_key.dsn_public,
    domain=global_stack.get_output("domain"),
).apply(
    lambda args: args["sentry_key"].replace(args["sentry_ingest_hostname"], f"sentry-ingest.{args['domain']}")
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

pulumi_cloudflare.PageRule(
    "page-rule",
    actions=pulumi_cloudflare.PageRuleActionsArgs(
        cache_level="aggressive",
    ),
    target=pulumi.Output.format("{}.{}", config.require("hostname"), global_stack.get_output("domain")),
    zone_id=global_stack.get_output("cloudflare_zone_id"),
)

# Only one of the stacks need to deploy the secrets, as they go to the same repository.
if pulumi.get_stack() == "prod":
    pulumi_github.ActionsSecret(
        "github-secret-nomad-cloudflare-access-id",
        repository="TrueWiki",
        secret_name="NOMAD_CF_ACCESS_CLIENT_ID",
        plaintext_value=cloudflare_core_stack.get_output("service_token_id"),
    )

    pulumi_github.ActionsSecret(
        "github-secret-nomad-cloudflare-access-secret",
        repository="TrueWiki",
        secret_name="NOMAD_CF_ACCESS_CLIENT_SECRET",
        plaintext_value=cloudflare_core_stack.get_output("service_token_secret"),
    )
