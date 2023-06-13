import pulumi
import pulumi_cloudflare

from dataclasses import dataclass

import proxy
import tunnel

config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")
aws_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/aws-core/prod")


@dataclass
class RouteMappingArgs:
    subdomain: str
    protected: bool = False
    path: str = None


# Port -> (Public, Subdomain, Path)
ROUTE_MAPPING = {
    "8646": RouteMappingArgs(subdomain="nomad", protected=True),
    "10000": RouteMappingArgs(subdomain="nomad-service"),
    "11000": RouteMappingArgs(subdomain="wiki"),
    "12000": RouteMappingArgs(subdomain="wiki-preview"),
    "12010": RouteMappingArgs(subdomain="bananas-preview-server"),
    "12012": RouteMappingArgs(subdomain="bananas-preview-api", path="/new-package/tus/*"),
    "12013": RouteMappingArgs(subdomain="bananas-preview-api"),
    "12014": RouteMappingArgs(subdomain="bananas-preview"),
}

# Subdomains where HTTP is allowed.
# Old OpenTTD clients didn't have HTTPS support, as such, there are some
# subdomains where HTTP is still required.
HTTP_ALLOWED = [
    "bananas-preview-cdn",
    "binaries-preview",
]

HTTP_ALLOWED_FQDN = global_stack.get_output("domain").apply(
    lambda domain: [f'"{subdomain}.{domain}"' for subdomain in HTTP_ALLOWED]
)
http_redirect_expression = HTTP_ALLOWED_FQDN.apply(
    lambda fqdns: f"(not ssl and http.host ne {' and http.host ne '.join(fqdns)})"
)

pulumi_cloudflare.Ruleset(
    "http-redirect-ruleset",
    kind="zone",
    name="HTTP -> HTTPS redirect",
    phase="http_request_dynamic_redirect",
    zone_id=global_stack.get_output("cloudflare_zone_id"),
    rules=[
        pulumi_cloudflare.RulesetRuleArgs(
            action="redirect",
            action_parameters=pulumi_cloudflare.RulesetRuleActionParametersArgs(
                from_value=pulumi_cloudflare.RulesetRuleActionParametersFromValueArgs(
                    preserve_query_string=True,
                    status_code=301,
                    target_url=pulumi_cloudflare.RulesetRuleActionParametersFromValueTargetUrlArgs(
                        expression='concat("https://", http.host, http.request.uri.path)',
                    ),
                ),
            ),
            description="HTTP -> HTTPS redirect",
            expression=http_redirect_expression,
        ),
    ],
)

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

for port, route in ROUTE_MAPPING.items():
    t.add_route(
        tunnel.TunnelRoute(
            name=route.subdomain,
            hostname=pulumi.Output.all(name=route.subdomain, domain=global_stack.get_output("domain")).apply(
                lambda args: f"{args['name']}.{args['domain']}"
            ),
            service=f"http://127.0.0.1:{port}",
            path=route.path,
            protect=route.protected,
        )
    )

t.create_routes()

pulumi.export("tunnel_token", t.tunnel.tunnel_token)
