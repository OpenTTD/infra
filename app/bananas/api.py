import hashlib
import pulumi
import pulumi_cloudflare
import pulumi_github
import pulumi_random
import pulumi_openttd

from dataclasses import dataclass


@dataclass
class ApiArgs:
    client_file: str
    cloudflare_account_id: str
    domain: str
    index_github_app_id: str
    index_github_app_key: str
    index_github_url: str
    memory: str
    s3_bucket: str
    s3_endpoint_url: str
    sentry_environment: str
    sentry_ingest_hostname: str
    tusd_port: str
    user_github_client_id: str
    user_github_client_secret: str
    web_port: str


class Api(pulumi.ComponentResource):
    def __init__(self, name, args: ApiArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("app:bananas:api", name, None, opts)

        permission_groups = pulumi_cloudflare.get_api_token_permission_groups()
        resources = args.cloudflare_account_id.apply(
            lambda account_id: {f"com.cloudflare.api.account.{account_id}": "*"}
        )

        api_token = pulumi_cloudflare.ApiToken(
            "api-api-token",
            name="app/bananas-api",
            policies=[
                pulumi_cloudflare.ApiTokenPolicyArgs(
                    resources=resources,
                    permission_groups=[
                        permission_groups.account["Workers R2 Storage Write"],
                    ],
                ),
            ],
        )

        reload_secret = pulumi_random.RandomPassword(
            "api-reload-secret",
            length=32,
            special=False,
        )
        sentry_key = pulumi_openttd.get_sentry_key("bananas-api", args.sentry_ingest_hostname, args.domain)

        SETTINGS = {
            "client_file": f"clients-{args.client_file}.yaml",
            "index_github_app_id": args.index_github_app_id,
            "index_github_app_key": args.index_github_app_key,
            "index_github_url": args.index_github_url,
            "memory": args.memory,
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
            "tusd_port": args.tusd_port,
            "user_github_client_id": args.user_github_client_id,
            "user_github_client_secret": args.user_github_client_secret,
            "web_port": args.web_port,
        }

        service = pulumi_openttd.NomadService(
            "api",
            pulumi_openttd.NomadServiceArgs(
                dependencies=[],
                prefix="api-",
                repository="bananas-api",
                service="bananas-api",
                settings=SETTINGS,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        pulumi_github.ActionsSecret(
            f"api-github-secret-reload-secret",
            repository=args.index_github_url.split("/")[-1],
            secret_name=f"API_RELOAD_SECRET",
            plaintext_value=reload_secret.result,
            opts=pulumi.ResourceOptions(parent=self, delete_before_replace=True),
        )
        pulumi_github.ActionsSecret(
            f"api-github-secret-nomad-service-key",
            repository=args.index_github_url.split("/")[-1],
            secret_name=f"API_NOMAD_SERVICE_{pulumi.get_stack().upper()}_KEY",
            plaintext_value=service.nomad_service_key.result,
            opts=pulumi.ResourceOptions(parent=self, delete_before_replace=True),
        )

        self.register_outputs({})
