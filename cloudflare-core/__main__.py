import pulumi

import ghcr_proxy
import github_proxy
import tunnel

config = pulumi.Config()
global_config = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")
aws_core_config = pulumi.StackReference(f"{pulumi.get_organization()}/aws-core/prod")

ghcr_proxy.GHCRProxy(
    "ghcr-proxy",
    ghcr_proxy.GHCRProxyArgs(
        account_id=config.require("account_id"),
        hostname=global_config.get_output("domain").apply(lambda domain: f"ghcr-proxy.{domain}"),
        zone_id=config.require_secret("zone_id"),
        whitelist_ipv6_cidr=aws_core_config.get_output("ipv6_cidr"),
    ),
)

github_proxy.GitHubProxy(
    "github-proxy",
    github_proxy.GitHubProxyArgs(
        account_id=config.require("account_id"),
        hostname=global_config.get_output("domain").apply(lambda domain: f"github-proxy.{domain}"),
        zone_id=config.require_secret("zone_id"),
        whitelist_ipv6_cidr=aws_core_config.get_output("ipv6_cidr"),
    ),
)

t = tunnel.Tunnel(
    "aws-tunnel",
    tunnel.TunnelArgs(
        account_id=config.require("account_id"),
        github_client_id=config.require_secret("github_client_id"),
        github_client_secret=config.require_secret("github_client_secret"),
        github_organization=config.require("github_organization"),
        github_access_group=config.require("github_access_group"),
    ),
)

t.add_route(
    tunnel.TunnelRoute(
        name="nomad",
        hostname=global_config.get_output("domain").apply(lambda domain: f"nomad.{domain}"),
        service="http://127.0.0.1:4646",
        allow_service_token=True,
    )
)

t.create_routes()

pulumi.export("tunnel_token", t.tunnel.tunnel_token)
pulumi.export("service_token_id", t.service_token.client_id)
pulumi.export("service_token_secret", t.service_token.client_secret)
