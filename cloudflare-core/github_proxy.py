import pulumi
import pulumi_cloudflare

from dataclasses import dataclass


@dataclass
class GitHubProxyArgs:
    account_id: str
    hostname: str
    zone_id: str


class GitHubProxy(pulumi.ComponentResource):
    """
    Currently, github.com is only available on IPv4. As we deploy our infra as
    IPv6-only, we need to proxy requests to github through a Cloudflare
    worker to make it work over IPv6.
    """

    def __init__(self, name, args: GitHubProxyArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("openttd:cfw:GitHubProxy", name, None, opts)

        worker = pulumi_cloudflare.WorkerScript(
            f"{name}-worker",
            account_id=args.account_id,
            content=open("files/github_proxy.js").read(),
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
