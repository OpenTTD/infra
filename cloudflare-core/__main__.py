import pulumi

import ghcr_proxy
import github_proxy
import tunnel

config = pulumi.Config()

ghcr_proxy.GHCRProxy(
    "ghcr-proxy",
    ghcr_proxy.GHCRProxyArgs(
        account_id=config.require("account_id"),
        hostname=f"ghcr-proxy.{config.require('domain')}",
        zone_id=config.require_secret("zone_id"),
    ),
)

github_proxy.GitHubProxy(
    "github-proxy",
    github_proxy.GitHubProxyArgs(
        account_id=config.require("account_id"),
        hostname=f"github-proxy.{config.require('domain')}",
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
        hostname=f"nomad.{config.require('domain')}",
        service="http://127.0.0.1:4646",
        allow_service_token=True,
    )
)

t.create_routes()

pulumi.export("tunnel_token", t.tunnel.tunnel_token)
pulumi.export("service_token_id", t.service_token.client_id)
pulumi.export("service_token_secret", t.service_token.client_secret)
