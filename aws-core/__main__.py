import pulumi
import pulumi_openttd

import network
import nomad

config = pulumi.Config()


pulumi_openttd.autotag.register()

network = network.Network(
    "network",
    network.NetworkArgs(
        "10.0.0.0/16",
    ),
)

nomad = nomad.Nomad(
    "nomad",
    nomad.NomadArgs(
        subnets=network.subnets,
        console_password=config.require_secret("console_password"),
    ),
)

pulumi.export("ipv6_cidr", network.vpc.ipv6_cidr_block)
pulumi.export("vpc_id", network.vpc.id)
pulumi.export("subnet_ids", [subnet.id for subnet in network.subnets])
