import pulumi
import pulumi_cloudflare
import pulumi_random

from dataclasses import dataclass


@dataclass
class TunnelArgs:
    account_id: str
    github_client_id: str
    github_client_secret: str
    github_organization: str
    github_access_group: str


@dataclass
class TunnelRoute:
    hostname: str
    service: str


class Tunnel(pulumi.ComponentResource):
    def __init__(self, name, args: TunnelArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("openttd:cf:Tunnel", name, None, opts)

        self._routes = []
        self._name = name

        secret = pulumi_random.RandomId(
            f"{name}-secret",
            byte_length=32,
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.tunnel = pulumi_cloudflare.Tunnel(
            name,
            account_id=args.account_id,
            name=name,
            secret=secret.b64_std,
            config_src="cloudflare",
            opts=pulumi.ResourceOptions(parent=self, delete_before_replace=True),
        )

        idp = pulumi_cloudflare.AccessIdentityProvider(
            f"{name}-idp",
            account_id=args.account_id,
            configs=[
                pulumi_cloudflare.AccessIdentityProviderConfigArgs(
                    client_id=args.github_client_id,
                    client_secret=args.github_client_secret,
                ),
            ],
            name="GitHub",
            type="github",
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.access_group = pulumi_cloudflare.AccessGroup(
            f"{name}-group",
            account_id=args.account_id,
            includes=[
                pulumi_cloudflare.AccessGroupIncludeArgs(
                    githubs=[
                        pulumi_cloudflare.AccessGroupIncludeGithubArgs(
                            identity_provider_id=idp.id,
                            name=args.github_organization,
                            teams=[
                                args.github_access_group,
                            ],
                        ),
                    ],
                ),
            ],
            name=f"{name} Group",
            opts=pulumi.ResourceOptions(parent=idp),
        )

        self.register_outputs(
            {
                "id": self.tunnel.id,
                "tunnel_token": self.tunnel.tunnel_token,
            }
        )

    def add_route(self, route: TunnelRoute):
        self._routes.append(route)

    def create_routes(self):
        ingress_rules = []
        for route in self._routes:
            ingress_rules.append(
                pulumi_cloudflare.TunnelConfigConfigIngressRuleArgs(
                    hostname=route.hostname,
                    service=route.service,
                )
            )

            name = route.hostname.split(".")[0]

            application = pulumi_cloudflare.AccessApplication(
                f"{self._name}-app-{name}",
                account_id=self.tunnel.account_id,
                domain=route.hostname,
                name=name,
                type="self_hosted",
                opts=pulumi.ResourceOptions(parent=self),
            )

            pulumi_cloudflare.AccessPolicy(
                f"{self._name}-app-{name}-policy",
                account_id=self.tunnel.account_id,
                application_id=application.id,
                decision="allow",
                includes=[
                    pulumi_cloudflare.AccessPolicyIncludeArgs(
                        groups=[
                            self.access_group.id,
                        ],
                    ),
                ],
                name="Policy",
                precedence=1,
                opts=pulumi.ResourceOptions(parent=application),
            )

        ingress_rules.append(
            pulumi_cloudflare.TunnelConfigConfigIngressRuleArgs(
                service="http_status:404",
            )
        )

        self.config = pulumi_cloudflare.TunnelConfig(
            f"{self._name}-config",
            account_id=self.tunnel.account_id,
            tunnel_id=self.tunnel.id,
            config=pulumi_cloudflare.TunnelConfigConfigArgs(
                ingress_rules=ingress_rules,
            ),
            opts=pulumi.ResourceOptions(parent=self.tunnel),
        )
