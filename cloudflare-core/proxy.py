import pulumi
import pulumi_cloudflare

from dataclasses import dataclass


@dataclass
class ProxyArgs:
    account_id: str
    hostname: str
    type: str  # Either "registry" or "transparent".
    proxy_to: str
    whitelist_ipv6_cidr: str
    zone_id: str


class Proxy(pulumi.ComponentResource):
    """
    Currently, most of GitHub is only available on IPv4. This of course is
    a bit weird in 2023, but here we are.
    As we deploy our infrastructure as IPv6-only, we need a way to reach
    GitHub's services over IPv6.
    For this we use Cloudflare Workers, which relay the requests to GitHub.
    To make sure that these proxies aren't abused, we use Cloudflare Access
    to only allow requests from our IPv6 ranges.
    """

    def __init__(self, name, args: ProxyArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("openttd:cfw:Proxy", name, None, opts)

        worker = pulumi_cloudflare.WorkerScript(
            f"{name}-worker",
            account_id=args.account_id,
            content=args.proxy_to.apply(lambda proxy_to: open(f"files/proxy_{args.type}.js").read().replace("@@HOSTNAME@@", proxy_to)),
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
