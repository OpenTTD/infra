import pulumi
import pulumi_openttd

import network
import nomad

config = pulumi.Config()

PUBLIC_PORTS = [
    ("tcp", 113),  # ident, used by IRC
    ("tcp", 3973),  # turn-2
    ("tcp", 3974),  # turn-1
    ("tcp", 3975),  # stun
    ("tcp", 3976),  # coordinator
    ("tcp", 3978),  # bananas-server
    ("udp", 3978),  # master
    ("tcp", 4973),  # turn-preview-2
    ("tcp", 4974),  # turn-preview-1
    ("tcp", 4975),  # stun-preview
    ("tcp", 4976),  # coordinator-preview
    ("tcp", 4978),  # bananas-server-preview
    ("udp", 4978),  # master-preview
]


pulumi_openttd.autotag.register()

network = network.Network(
    "network",
    network.NetworkArgs(
        compartment_id=config.require("compartment-id"),
        cidr_block="10.0.0.0/16",
        public_ports=PUBLIC_PORTS,
    ),
)

nomad.Nomad(
    "nomad",
    nomad.NomadArgs(
        compartment_id=config.require("compartment-id"),
        console_password=config.require_secret("console_password"),
        is_public=False,
        subnet_id=network.private_subnet.id,
        subnet_prefix_id=network.private_subnet_prefix.id,
        ipv6_cidr=network.cidr_v6_private,
        ipv6_prefix_cidr=network.cidr_v6_private_prefix,
        size=3,
    ),
)
nomad.Nomad(
    "nomad-public",
    nomad.NomadArgs(
        compartment_id=config.require("compartment-id"),
        console_password=config.require_secret("console_password"),
        is_public=True,
        subnet_id=network.public_subnet.id,
        subnet_prefix_id=network.public_subnet_prefix.id,
        ipv6_cidr=network.cidr_v6_public,
        ipv6_prefix_cidr=network.cidr_v6_public_prefix,
        size=2,
    ),
)

pulumi.export("ipv6_cidr", network.cidr_v6_block)
pulumi.export("ipv4_gateway", network.ipv4_gateway)
