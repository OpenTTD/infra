import pulumi
import pulumi_openttd

from dataclasses import dataclass


@dataclass
class WebArgs:
    domain: str
    hostname: str
    memory_max: str
    memory: str
    port: str
    sentry_environment: str
    sentry_ingest_hostname: str


class Web(pulumi.ComponentResource):
    def __init__(self, name, args: WebArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("app:multiplayer:web", name, None, opts)

        sentry_key = pulumi_openttd.get_sentry_key("master-server-web", args.sentry_ingest_hostname, args.domain)
        api_url = pulumi.Output.format("https://{}-api.{}", args.hostname, args.domain)

        SETTINGS = {
            "api_url": api_url,
            "count": "1" if pulumi.get_stack() == "preview" else "2",
            "memory": args.memory,
            "memory_max": args.memory_max,
            "sentry_dsn": sentry_key,
            "sentry_environment": args.sentry_environment,
            "stack": pulumi.get_stack(),
            "port": args.port,
        }

        pulumi_openttd.NomadService(
            "web",
            pulumi_openttd.NomadServiceArgs(
                dependencies=[],
                prefix="web-",
                repository="master-server-web",
                service="master-server-web",
                settings=SETTINGS,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.register_outputs({})
