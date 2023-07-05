import pulumi
import pulumi_cloudflare
import pulumi_openttd

from dataclasses import dataclass


@dataclass
class MasterServerArgs:
    api_memory_max: str
    api_memory: str
    api_port: str
    cloudflare_zone_id: str
    domain: str
    master_hostname: str
    master_memory_max: str
    master_memory: str
    master_port: str
    master_public_port: str
    sentry_environment: str
    sentry_ingest_hostname: str


class MasterServer(pulumi.ComponentResource):
    def __init__(self, name, args: MasterServerArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("app:multiplayer:masterserver", name, None, opts)

        sentry_key = pulumi_openttd.get_sentry_key("master-server", args.sentry_ingest_hostname, args.domain)

        SETTINGS = {
            "api_memory_max": args.api_memory_max,
            "api_memory": args.api_memory,
            "api_port": args.api_port,
            "count": "1" if pulumi.get_stack() == "preview" else "2",
            "domain": args.domain,
            "master_memory_max": args.master_memory_max,
            "master_memory": args.master_memory,
            "master_port": args.master_port,
            "master_public_port": args.master_public_port,
            "sentry_dsn": sentry_key,
            "sentry_environment": args.sentry_environment,
            "stack": pulumi.get_stack(),
        }

        pulumi_openttd.NomadService(
            "master-server",
            pulumi_openttd.NomadServiceArgs(
                dependencies=[],
                prefix="ms-",
                repository="master-server",
                service="master-server",
                settings=SETTINGS,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        pulumi_cloudflare.Record(
            f"master-dns",
            name=pulumi.Output.format("{}.{}", args.master_hostname, args.domain),
            proxied=False,
            type="CNAME",
            value="nlb.openttd.org",
            zone_id=args.cloudflare_zone_id,
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.register_outputs({})
