import pulumi
import pulumi_cloudflare

from dataclasses import dataclass


@dataclass
class GHCRProxyArgs:
    account_id: str
    hostname: str
    zone_id: str
    whitelist_ipv6_cidr: str


class GHCRProxy(pulumi.ComponentResource):
    """
    Currently, ghcr.io is only available on IPv4. As we deploy our infra as
    IPv6-only, we need to proxy requests to ghcr.io through a Cloudflare
    worker to make it work over IPv6.
    """

    def __init__(self, name, args: GHCRProxyArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("openttd:cfw:GHCRProxy", name, None, opts)

        worker = pulumi_cloudflare.WorkerScript(
            f"{name}-worker",
            account_id=args.account_id,
            content=open("files/ghcr_proxy.js").read(),
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

        application = pulumi_cloudflare.AccessApplication(
            f"{name}-app",
            account_id=args.account_id,
            app_launcher_visible=False,
            domain=args.hostname,
            name=name,
            type="self_hosted",
            opts=pulumi.ResourceOptions(parent=self),
        )

        pulumi_cloudflare.AccessPolicy(
            f"{name}-app-policy",
            account_id=args.account_id,
            application_id=application.id,
            decision="bypass",
            includes=[
                pulumi_cloudflare.AccessPolicyIncludeArgs(
                    ips=[
                        args.whitelist_ipv6_cidr,
                    ]
                ),
            ],
            name="IPv6 Whitelist",
            precedence=1,
            opts=pulumi.ResourceOptions(parent=application),
        )

        self.register_outputs({})
