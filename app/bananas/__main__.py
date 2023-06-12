import pulumi
import pulumi_github
import pulumi_openttd

import api
import cdn
import server
import web


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")
aws_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/aws-core/prod")
cloudflare_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/cloudflare-core/prod")


pulumi_openttd.autotag.register()

cdn = cdn.Cdn(
    "cdn",
    cdn.CdnArgs(
        cloudflare_account_id=global_stack.get_output("cloudflare_account_id"),
        cloudflare_zone_id=global_stack.get_output("cloudflare_zone_id"),
        domain=global_stack.get_output("domain"),
        hostname=config.require("hostname"),
    ),
)

server.Server(
    "server",
    server.ServerArgs(
        content_port=config.require("server-content-port"),
        content_public_port=config.require("server-content-public-port"),
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

api.Api(
    "api",
    api.ApiArgs(
        client_file=config.require("api-client-file"),
        cloudflare_account_id=global_stack.get_output("cloudflare_account_id"),
        domain=global_stack.get_output("domain"),
        index_github_app_id=config.require("api-index-github-app-id"),
        index_github_app_key=config.require_secret("api-index-github-app-key"),
        index_github_url=config.require("index-github-url"),
        memory=config.require("api-memory"),
        s3_bucket=cdn.bucket_name,
        s3_endpoint_url=cdn.bucket_endpoint_url,
        sentry_environment=config.require("sentry-environment"),
        sentry_ingest_hostname=global_stack.get_output("sentry_ingest_hostname"),
        service_token_id=cloudflare_core_stack.get_output("service_token_id"),
        service_token_secret=cloudflare_core_stack.get_output("service_token_secret"),
        tusd_port=config.require("api-tusd-port"),
        user_github_client_id=config.require("api-user-github-client-id"),
        user_github_client_secret=config.require_secret("api-user-github-client-secret"),
        web_port=config.require("api-web-port"),
    ),
)

web.Web(
    "web",
    web.WebArgs(
        domain=global_stack.get_output("domain"),
        hostname=config.require("hostname"),
        memory=config.require("web-memory"),
        port=config.require("web-port"),
        sentry_environment=config.require("sentry-environment"),
        sentry_ingest_hostname=global_stack.get_output("sentry_ingest_hostname"),
        service_token_id=cloudflare_core_stack.get_output("service_token_id"),
        service_token_secret=cloudflare_core_stack.get_output("service_token_secret"),
    ),
)
