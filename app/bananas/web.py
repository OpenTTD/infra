import pulumi
import pulumi_openttd

from dataclasses import dataclass


@dataclass
class WebArgs:
    domain: str
    hostname: str
    memory: str
    memory_max: str
    port: str
    sentry_environment: str
    sentry_ingest_hostname: str


class Web(pulumi.ComponentResource):
    def __init__(self, name, args: WebArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("app:bananas:web", name, None, opts)

        sentry_key = pulumi_openttd.get_sentry_key("bananas-frontend-web", args.sentry_ingest_hostname, args.domain)
        frontend_url = pulumi.Output.format("https://{}.{}", args.hostname, args.domain)
        api_url = pulumi.Output.format("https://{}-api.{}", args.hostname, args.domain)

        SETTINGS = {
            "api_url": api_url,
            "frontend_url": frontend_url,
            "memory": args.memory,
            "memory_max": args.memory_max,
            "sentry_dsn": sentry_key,
            "sentry_environment": args.sentry_environment,
            "stack": pulumi_openttd.get_stack(),
            "port": args.port,
        }

        pulumi_openttd.NomadService(
            "web",
            pulumi_openttd.NomadServiceArgs(
                dependencies=[],
                prefix="web-",
                repository="bananas-frontend-web",
                service="bananas-web",
                settings=SETTINGS,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.register_outputs({})
