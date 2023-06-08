import hashlib
import pulumi
import pulumi_cloudflare
import pulumi_random
import pulumi_openttd

from dataclasses import dataclass


@dataclass
class ServerArgs:
    content_port: str
    cloudflare_account_id: str
    domain: str
    hostname: str
    index_github_url: str
    memory: str
    s3_bucket: str
    s3_endpoint_url: str
    sentry_environment: str
    sentry_ingest_hostname: str
    service_token_id: str
    service_token_secret: str
    web_port: str


class Server(pulumi.ComponentResource):
    def __init__(self, name, args: ServerArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("app:bananas:server", name, None, opts)

        permission_groups = pulumi_cloudflare.get_api_token_permission_groups()
        resources = args.cloudflare_account_id.apply(
            lambda account_id: {f"com.cloudflare.api.account.{account_id}": "*"}
        )

        api_token = pulumi_cloudflare.ApiToken(
            "api-token",
            name="app/bananas-server",
            policies=[
                pulumi_cloudflare.ApiTokenPolicyArgs(
                    resources=resources,
                    permission_groups=[
                        permission_groups.account["Workers R2 Storage Read"],
                    ],
                ),
            ],
        )

        reload_secret = pulumi_random.RandomString(
            "reload-secret",
            length=32,
            special=False,
        )
        cdn_fallback_url = pulumi.Output.format("https://{}-cdn.{}", args.hostname, args.domain)
        sentry_key = pulumi_openttd.get_sentry_key("bananas-server", args.sentry_ingest_hostname, args.domain)

        # For production, make sure the bootstrap request returns OpenGFX.
        if pulumi.get_stack() == "prod":
            boostrap_command = '"--bootstrap-unique-id", "4f474658",'
        else:
            boostrap_command = ""

        SETTINGS = {
            "bootstrap_command": boostrap_command,
            "cdn_fallback_url": cdn_fallback_url,
            "content_port": args.content_port,
            "count": "1" if pulumi.get_stack() == "preview" else "2",
            "index_github_url": args.index_github_url,
            "memory": args.memory,
            "reload_secret": reload_secret.result,
            "sentry_dsn": sentry_key,
            "sentry_environment": args.sentry_environment,
            "stack": pulumi.get_stack(),
            "storage_s3_access_key_id": api_token.id,
            "storage_s3_bucket": args.s3_bucket,
            "storage_s3_endpoint_url": args.s3_endpoint_url,
            "storage_s3_secret_access_key": api_token.value.apply(lambda secret: hashlib.sha256(secret.encode()).hexdigest()),
            "web_port": args.web_port,
        }

        pulumi_openttd.NomadService(
            "server",
            pulumi_openttd.NomadServiceArgs(
                service="bananas-server",
                settings=SETTINGS,
                dependencies=[],
                service_token_id=args.service_token_id,
                service_token_secret=args.service_token_secret,
                repository="bananas-server",
            ),
        )

        self.register_outputs({})
