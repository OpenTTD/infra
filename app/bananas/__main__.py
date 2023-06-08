import pulumi
import pulumi_github
import pulumi_openttd

import cdn
import server


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")
aws_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/aws-core/prod")
cloudflare_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/cloudflare-core/prod")


pulumi_openttd.autotag.register()

cdn = cdn.Cdn(
    "cdn",
    cdn.CdnArgs(
        cloudflare_account_id=global_stack.get_output("cloudflare_account_id"),
    ),
)

server.Server(
    "server",
    server.ServerArgs(
        content_port=config.require("server-content-port"),
        cloudflare_account_id=global_stack.get_output("cloudflare_account_id"),
        domain=global_stack.get_output("domain"),
        hostname=config.require("hostname"),
        index_github_url=config.require("index-github-url"),
        memory=config.require("server-memory"),
        s3_bucket=cdn.bucket_name,
        s3_endpoint_url=cdn.bucket_endpoint_url,
        sentry_environment=config.require("sentry-environment"),
        sentry_ingest_hostname=global_stack.get_output("sentry_ingest_hostname"),
        service_token_id=cloudflare_core_stack.get_output("service_token_id"),
        service_token_secret=cloudflare_core_stack.get_output("service_token_secret"),
        web_port=config.require("server-web-port"),
    ),
)


# Temporary till all these have their own stack.
if pulumi.get_stack() == "prod":
    for repository in ("bananas-api", "bananas-frontend-web"):
        pulumi_github.ActionsSecret(
            f"github-secret-{repository}-nomad-cloudflare-access-id",
            repository=repository,
            secret_name="NOMAD_CF_ACCESS_CLIENT_ID",
            plaintext_value=cloudflare_core_stack.get_output("service_token_id"),
        )

        pulumi_github.ActionsSecret(
            f"github-secret-{repository}-nomad-cloudflare-access-secret",
            repository=repository,
            secret_name="NOMAD_CF_ACCESS_CLIENT_SECRET",
            plaintext_value=cloudflare_core_stack.get_output("service_token_secret"),
        )
