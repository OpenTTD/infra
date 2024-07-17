import pulumi
import pulumi_cloudflare

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProxyAccessPolicyArgs:
    account_id: str
    whitelist_ipv6_cidr: str
    whitelist_ipv4: Optional[str] = None


@dataclass
class NomadServiceWorkerArgs:
    account_id: str
    hostname: str
    zone_id: str


class NomadServiceWorker(pulumi.ComponentResource):
    def __init__(self, name, args: NomadServiceWorkerArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("openttd:nomad-core:ServiceWorker", name, None, opts)

        worker = pulumi_cloudflare.WorkerScript(
            f"{name}-worker",
            account_id=args.account_id,
            content=open(f"files/nomad-service-worker.js").read(),
            logpush=True,
            name=name,
            module=True,
            opts=pulumi.ResourceOptions(parent=self),
        )

        pulumi_cloudflare.WorkerDomain(
            f"{name}-domain",
            account_id=args.account_id,
            hostname=args.hostname,
            service=name,
            zone_id=args.zone_id,
            opts=pulumi.ResourceOptions(parent=worker),
        )

        self.register_outputs({})
