import pulumi

import tunnel

config = pulumi.Config()

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
    )
)

t.create_routes()

pulumi.export("tunnel_token", t.tunnel.tunnel_token)
