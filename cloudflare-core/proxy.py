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
class ProxyArgs:
    access_policies: list[int]
    account_id: str
    hostname: str
    type: str  # Either "registry" or "transparent".
    proxy_to: str
    zone_id: str


class ProxyAccessPolicy(pulumi.ComponentResource):
    def __init__(self, name, args: ProxyAccessPolicyArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("openttd:cfw:ProxyAccessPolicy", name, None, opts)

        self.access_policy = pulumi_cloudflare.AccessPolicy(
            f"{name}-app-policy",
            account_id=args.account_id,
            decision="bypass",
            includes=[
                pulumi_cloudflare.AccessPolicyIncludeArgs(
                    ips=[
                        args.whitelist_ipv6_cidr,
                    ]
                    + ([args.whitelist_ipv4] if args.whitelist_ipv4 else []),
                ),
            ],
            name=f"IPv6 Whitelist ({name})",
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.register_outputs({})


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
            content=args.proxy_to.apply(
                lambda proxy_to: open(f"files/proxy_{args.type}.js").read().replace("[[ hostname ]]", proxy_to)
            ),
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

        pulumi_cloudflare.AccessApplication(
            f"{name}-app",
            account_id=args.account_id,
            app_launcher_visible=False,
            domain=args.hostname,
            name=name,
            policies=args.access_policies,
            type="self_hosted",
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.register_outputs({})
