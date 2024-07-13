import pulumi
import pulumi_cloudflare
import pulumi_openttd

from dataclasses import dataclass


@dataclass
class GameCoordinatorArgs:
    cloudflare_zone_id: str
    coordinator_hostname: str
    coordinator_memory_max: str
    coordinator_memory: str
    coordinator_port: str
    coordinator_public_port: str
    domain: str
    sentry_environment: str
    sentry_ingest_hostname: str
    shared_secret: str
    stun_hostname: str
    stun_memory_max: str
    stun_memory: str
    stun_port: str
    stun_public_port: str
    turn_1_port: str
    turn_1_public_port: str
    turn_2_port: str
    turn_2_public_port: str
    turn_hostname: str
    turn_memory_max: str
    turn_memory: str


class GameCoordinator(pulumi.ComponentResource):
    def __init__(self, name, args: GameCoordinatorArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("app:multiplayer:gamecoordinator", name, None, opts)

        sentry_key = pulumi_openttd.get_sentry_key("game-coordinator", args.sentry_ingest_hostname, args.domain)
        target = pulumi.get_stack().split("-")[1]

        SETTINGS = {
            "affinity_port": "6001" if pulumi_openttd.get_stack() == "preview" else "6002",
            "coordinator_memory_max": args.coordinator_memory_max,
            "coordinator_memory": args.coordinator_memory,
            "coordinator_port": args.coordinator_port,
            "coordinator_public_port": args.coordinator_public_port,
            "count": "1" if pulumi_openttd.get_stack() == "preview" else "2",
            "domain": args.domain,
            "sentry_dsn": sentry_key,
            "sentry_environment": args.sentry_environment,
            "shared_secret": args.shared_secret,
            "stack": pulumi_openttd.get_stack(),
            "stun_memory_max": args.stun_memory_max,
            "stun_memory": args.stun_memory,
            "stun_port": args.stun_port,
            "stun_public_port": args.stun_public_port,
            "target": target,
            "turn_1_port": args.turn_1_port,
            "turn_1_public_port": args.turn_1_public_port,
            "turn_2_port": args.turn_2_port,
            "turn_2_public_port": args.turn_2_public_port,
            "turn_hostname": args.turn_hostname,
            "turn_memory_max": args.turn_memory_max,
            "turn_memory": args.turn_memory,
        }

        pulumi_openttd.NomadService(
            "game-coordinator",
            pulumi_openttd.NomadServiceArgs(
                dependencies=[],
                prefix="gc-",
                repository="game-coordinator",
                service="game-coordinator",
                settings=SETTINGS,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        pulumi_cloudflare.Record(
            f"coordinator-dns",
            name=pulumi.Output.format("{}.{}", args.coordinator_hostname, args.domain),
            proxied=False,
            type="CNAME",
            value=f"nlb-{target}.openttd.org",
            zone_id=args.cloudflare_zone_id,
            opts=pulumi.ResourceOptions(parent=self),
        )
        pulumi_cloudflare.Record(
            f"stun-dns",
            name=pulumi.Output.format("{}.{}", args.stun_hostname, args.domain),
            proxied=False,
            type="CNAME",
            value=f"nlb-{target}.openttd.org",
            zone_id=args.cloudflare_zone_id,
            opts=pulumi.ResourceOptions(parent=self),
        )
        for i in range(2):
            pulumi_cloudflare.Record(
                f"turn-{i + 1}-dns",
                name=pulumi.Output.format("{}-{}.{}", args.turn_hostname, i + 1, args.domain),
                proxied=False,
                type="CNAME",
                value=f"nlb-{target}.openttd.org",
                zone_id=args.cloudflare_zone_id,
                opts=pulumi.ResourceOptions(parent=self),
            )

        self.register_outputs({})
