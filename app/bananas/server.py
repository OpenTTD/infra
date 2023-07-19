import hashlib
import pulumi
import pulumi_cloudflare
import pulumi_github
import pulumi_random
import pulumi_openttd

from dataclasses import dataclass


@dataclass
class ServerArgs:
    content_hostname: str
    content_port: str
    content_public_port: str
    cloudflare_account_id: str
    cloudflare_zone_id: str
    domain: str
    hostname: str
    index_github_url: str
    memory: str
    memory_max: str
    s3_bucket: str
    s3_endpoint_url: str
    sentry_environment: str
    sentry_ingest_hostname: str
    web_port: str


class Server(pulumi.ComponentResource):
    def __init__(self, name, args: ServerArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("app:bananas:server", name, None, opts)

        permission_groups = pulumi_cloudflare.get_api_token_permission_groups()
        resources = args.cloudflare_account_id.apply(
            lambda account_id: {f"com.cloudflare.api.account.{account_id}": "*"}
        )

        api_token = pulumi_cloudflare.ApiToken(
            "server-api-token",
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

        reload_secret = pulumi_random.RandomPassword(
            "server-reload-secret",
            length=32,
            special=False,
        )
        cdn_fallback_url = pulumi.Output.format("https://{}-cdn.{}", args.hostname, args.domain)
        sentry_key = pulumi_openttd.get_sentry_key("bananas-server", args.sentry_ingest_hostname, args.domain)

        # Make sure the bootstrap request returns OpenGFX.
        boostrap_command = '"--bootstrap-unique-id", "4f474658",'

        SETTINGS = {
            "bootstrap_command": boostrap_command,
            "cdn_fallback_url": cdn_fallback_url,
            "content_port": args.content_port,
            "content_public_port": args.content_public_port,
            "count": "1" if pulumi.get_stack() == "preview" else "2",
            "index_github_url": args.index_github_url,
            "memory": args.memory,
            "memory_max": args.memory_max,
            "reload_secret": reload_secret.result,
            "sentry_dsn": sentry_key,
            "sentry_environment": args.sentry_environment,
            "stack": pulumi.get_stack(),
            "storage_s3_access_key_id": api_token.id,
            "storage_s3_bucket": args.s3_bucket,
            "storage_s3_endpoint_url": args.s3_endpoint_url,
            "storage_s3_secret_access_key": api_token.value.apply(
                lambda secret: hashlib.sha256(secret.encode()).hexdigest()
            ),
            "web_port": args.web_port,
        }

        service = pulumi_openttd.NomadService(
            "server",
            pulumi_openttd.NomadServiceArgs(
                dependencies=[],
                prefix="server-",
                repository="bananas-server",
                service="bananas-server",
                settings=SETTINGS,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        pulumi_cloudflare.Record(
            f"server-dns",
            name=pulumi.Output.format("{}.{}", args.content_hostname, args.domain),
            proxied=False,
            type="CNAME",
            value="nlb.openttd.org",
            zone_id=args.cloudflare_zone_id,
            opts=pulumi.ResourceOptions(parent=self),
        )

        pulumi_github.ActionsSecret(
            f"server-github-secret-reload-secret",
            repository=args.index_github_url.split("/")[-1],
            secret_name=f"SERVER_RELOAD_SECRET",
            plaintext_value=reload_secret.result,
            opts=pulumi.ResourceOptions(parent=self, delete_before_replace=True),
        )
        pulumi_github.ActionsSecret(
            f"server-github-secret-nomad-service-key",
            repository=args.index_github_url.split("/")[-1],
            secret_name=f"SERVER_NOMAD_SERVICE_{pulumi.get_stack().upper()}_KEY",
            plaintext_value=service.nomad_service_key.result,
            opts=pulumi.ResourceOptions(parent=self, delete_before_replace=True),
        )

        self.register_outputs({})
