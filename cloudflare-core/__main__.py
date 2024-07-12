import pulumi
import pulumi_cloudflare

from dataclasses import dataclass

import logpush
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
    "8686": RouteMappingArgs(subdomain="nomad", protected=True),
    "10000": RouteMappingArgs(subdomain="nomad-service"),
    "10010": RouteMappingArgs(subdomain="nomad-prom", protected=True),
    "11000": RouteMappingArgs(subdomain="wiki"),
    "11010": RouteMappingArgs(subdomain="bananas-server"),
    "11012": RouteMappingArgs(subdomain="bananas-api", path="/new-package/tus/*"),
    "11013": RouteMappingArgs(subdomain="bananas-api"),
    "11014": RouteMappingArgs(subdomain="bananas"),
    "11020": RouteMappingArgs(subdomain="dorpsgek"),
    "11030": RouteMappingArgs(subdomain="translator"),
    "11045": RouteMappingArgs(subdomain="servers-api"),
    "11046": RouteMappingArgs(subdomain="servers"),
    "12000": RouteMappingArgs(subdomain="wiki-preview"),
    "12010": RouteMappingArgs(subdomain="bananas-preview-server"),
    "12012": RouteMappingArgs(subdomain="bananas-preview-api", path="/new-package/tus/*"),
    "12013": RouteMappingArgs(subdomain="bananas-preview-api"),
    "12014": RouteMappingArgs(subdomain="bananas-preview"),
    "12020": RouteMappingArgs(subdomain="dorpsgek-preview"),
    "12030": RouteMappingArgs(subdomain="translator-preview"),
    "12045": RouteMappingArgs(subdomain="servers-preview-api"),
    "12046": RouteMappingArgs(subdomain="servers-preview"),
}

# Subdomains where HTTP is allowed.
# Old OpenTTD clients didn't have HTTPS support, as such, there are some
# subdomains where HTTP is still required.
HTTP_ALLOWED = [
    "bananas-preview-cdn",
    "binaries-preview",
    "bananas-cdn",
    "binaries",
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

access_policy = proxy.ProxyAccessPolicy(
    "access-policy",
    proxy.ProxyAccessPolicyArgs(
        account_id=global_stack.get_output("cloudflare_account_id"),
        whitelist_ipv6_cidr=aws_core_stack.get_output("ipv6_cidr"),
    ),
)

proxy.Proxy(
    "ghcr-proxy",
    proxy.ProxyArgs(
        access_policy=access_policy.access_policy,
        account_id=global_stack.get_output("cloudflare_account_id"),
        hostname=global_stack.get_output("domain").apply(lambda domain: f"ghcr-proxy.{domain}"),
        proxy_to=pulumi.Output.from_input("ghcr.io"),
        type="registry",
        zone_id=global_stack.get_output("cloudflare_zone_id"),
    ),
)

proxy.Proxy(
    "github-proxy",
    proxy.ProxyArgs(
        access_policy=access_policy.access_policy,
        account_id=global_stack.get_output("cloudflare_account_id"),
        hostname=global_stack.get_output("domain").apply(lambda domain: f"github-proxy.{domain}"),
        proxy_to=pulumi.Output.from_input("github.com"),
        type="transparent",
        zone_id=global_stack.get_output("cloudflare_zone_id"),
    ),
)

proxy.Proxy(
    "github-api-proxy",
    proxy.ProxyArgs(
        access_policy=access_policy.access_policy,
        account_id=global_stack.get_output("cloudflare_account_id"),
        hostname=global_stack.get_output("domain").apply(lambda domain: f"github-api-proxy.{domain}"),
        proxy_to=pulumi.Output.from_input("api.github.com"),
        type="transparent",
        zone_id=global_stack.get_output("cloudflare_zone_id"),
    ),
)

proxy.Proxy(
    "discord-proxy",
    proxy.ProxyArgs(
        access_policy=access_policy.access_policy,
        account_id=global_stack.get_output("cloudflare_account_id"),
        hostname=global_stack.get_output("domain").apply(lambda domain: f"discord-proxy.{domain}"),
        proxy_to=pulumi.Output.from_input("discord.com"),
        type="transparent",
        zone_id=global_stack.get_output("cloudflare_zone_id"),
    ),
)

proxy.Proxy(
    "sentry-ingest-proxy",
    proxy.ProxyArgs(
        access_policy=access_policy.access_policy,
        account_id=global_stack.get_output("cloudflare_account_id"),
        hostname=global_stack.get_output("domain").apply(lambda domain: f"sentry-ingest.{domain}"),
        proxy_to=global_stack.get_output("sentry_ingest_hostname"),
        type="transparent",
        zone_id=global_stack.get_output("cloudflare_zone_id"),
    ),
)

proxy.Proxy(
    "grafana-prometheus-proxy",
    proxy.ProxyArgs(
        access_policy=access_policy.access_policy,
        account_id=global_stack.get_output("cloudflare_account_id"),
        hostname=global_stack.get_output("domain").apply(lambda domain: f"grafana-prometheus-proxy.{domain}"),
        proxy_to=global_stack.get_output("grafana_prometheus_hostname"),
        type="transparent",
        zone_id=global_stack.get_output("cloudflare_zone_id"),
    ),
)

tunnel_access = t.TunnelAccess(
    "tunnel",
    t.TunnelAccessArgs(
        account_id=global_stack.get_output("cloudflare_account_id"),
        github_client_id=config.require_secret("github_client_id"),
        github_client_secret=config.require_secret("github_client_secret"),
        github_organization=config.require("github_organization"),
        github_access_group=config.require("github_access_group"),
    ),
)

t = t.Tunnel(
    "aws-tunnel",
    t.TunnelArgs(
        account_id=global_stack.get_output("cloudflare_account_id"),
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

t.create_routes(tunnel_access.policies)

logpush.LogPush(
    "logpush",
    logpush.LogPushArgs(
        cloudflare_account_id=global_stack.get_output("cloudflare_account_id"),
    ),
)

pulumi.export("tunnel_token", t.tunnel.tunnel_token)
pulumi.export("service_token_id", tunnel_access.service_token.client_id)
pulumi.export("service_token_secret", tunnel_access.service_token.client_secret)
