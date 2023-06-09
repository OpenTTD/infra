import pulumi

import proxy
import tunnel

config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")
aws_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/aws-core/prod")

# Port -> (Public, Subdomain, Path)
ROUTE_MAPPING = {
    "8646": (False, "nomad", None),
    "11000": (True, "wiki", None),
    "12000": (True, "wiki-preview", None),
    "12010": (True, "bananas-preview-server", None),
    "12012": (True, "bananas-preview-api", "/new-package/tus/*"),
    "12013": (True, "bananas-preview-api", None),
}

proxy.Proxy(
    "ghcr-proxy",
    proxy.ProxyArgs(
        account_id=global_stack.get_output("cloudflare_account_id"),
        hostname=global_stack.get_output("domain").apply(lambda domain: f"ghcr-proxy.{domain}"),
        proxy_to=pulumi.Output.from_input("ghcr.io"),
        type="registry",
        whitelist_ipv6_cidr=aws_core_stack.get_output("ipv6_cidr"),
        zone_id=global_stack.get_output("cloudflare_zone_id"),
    ),
)

proxy.Proxy(
    "github-proxy",
    proxy.ProxyArgs(
        account_id=global_stack.get_output("cloudflare_account_id"),
        hostname=global_stack.get_output("domain").apply(lambda domain: f"github-proxy.{domain}"),
        proxy_to=pulumi.Output.from_input("github.com"),
        type="transparent",
        whitelist_ipv6_cidr=aws_core_stack.get_output("ipv6_cidr"),
        zone_id=global_stack.get_output("cloudflare_zone_id"),
    ),
)

proxy.Proxy(
    "github-api-proxy",
    proxy.ProxyArgs(
        account_id=global_stack.get_output("cloudflare_account_id"),
        hostname=global_stack.get_output("domain").apply(lambda domain: f"github-api-proxy.{domain}"),
        proxy_to=pulumi.Output.from_input("api.github.com"),
        type="transparent",
        whitelist_ipv6_cidr=aws_core_stack.get_output("ipv6_cidr"),
        zone_id=global_stack.get_output("cloudflare_zone_id"),
    ),
)

proxy.Proxy(
    "sentry-ingest-proxy",
    proxy.ProxyArgs(
        account_id=global_stack.get_output("cloudflare_account_id"),
        hostname=global_stack.get_output("domain").apply(lambda domain: f"sentry-ingest.{domain}"),
        proxy_to=global_stack.get_output("sentry_ingest_hostname"),
        type="transparent",
        whitelist_ipv6_cidr=aws_core_stack.get_output("ipv6_cidr"),
        zone_id=global_stack.get_output("cloudflare_zone_id"),
    ),
)

t = tunnel.Tunnel(
    "aws-tunnel",
    tunnel.TunnelArgs(
        account_id=global_stack.get_output("cloudflare_account_id"),
        github_client_id=config.require_secret("github_client_id"),
        github_client_secret=config.require_secret("github_client_secret"),
        github_organization=config.require("github_organization"),
        github_access_group=config.require("github_access_group"),
        zone_id=global_stack.get_output("cloudflare_zone_id"),
    ),
)

for port, (public, name, path) in ROUTE_MAPPING.items():
    t.add_route(
        tunnel.TunnelRoute(
            name=name,
            hostname=pulumi.Output.all(name=name, domain=global_stack.get_output("domain")).apply(lambda args: f"{args['name']}.{args['domain']}"),
            service=f"http://127.0.0.1:{port}",
            path=path,
            protect=not public,
            allow_service_token=not public,
        )
    )

t.create_routes()

pulumi.export("tunnel_token", t.tunnel.tunnel_token)
pulumi.export("service_token_id", t.service_token.client_id)
pulumi.export("service_token_secret", t.service_token.client_secret)
