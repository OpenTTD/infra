import pulumi

import proxy
import tunnel

config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")
aws_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/aws-core/prod")

proxy.Proxy(
    "ghcr-proxy",
    proxy.ProxyArgs(
        account_id=config.require("account_id"),
        hostname=global_stack.get_output("domain").apply(lambda domain: f"ghcr-proxy.{domain}"),
        proxy_to="ghcr.io",
        type="registry",
        whitelist_ipv6_cidr=aws_core_stack.get_output("ipv6_cidr"),
        zone_id=config.require_secret("zone_id"),
    ),
)

proxy.Proxy(
    "github-proxy",
    proxy.ProxyArgs(
        account_id=config.require("account_id"),
        hostname=global_stack.get_output("domain").apply(lambda domain: f"github-proxy.{domain}"),
        proxy_to="github.com",
        type="transparent",
        whitelist_ipv6_cidr=aws_core_stack.get_output("ipv6_cidr"),
        zone_id=config.require_secret("zone_id"),
    ),
)

proxy.Proxy(
    "github-api-proxy",
    proxy.ProxyArgs(
        account_id=config.require("account_id"),
        hostname=global_stack.get_output("domain").apply(lambda domain: f"github-api-proxy.{domain}"),
        proxy_to="api.github.com",
        type="transparent",
        whitelist_ipv6_cidr=aws_core_stack.get_output("ipv6_cidr"),
        zone_id=config.require_secret("zone_id"),
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
        hostname=global_stack.get_output("domain").apply(lambda domain: f"nomad.{domain}"),
        service="http://127.0.0.1:8646",
        allow_service_token=True,
    )
)

t.create_routes()

pulumi.export("tunnel_token", t.tunnel.tunnel_token)
pulumi.export("service_token_id", t.service_token.client_id)
pulumi.export("service_token_secret", t.service_token.client_secret)
