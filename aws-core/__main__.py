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

nomad.Nomad(
    "nomad",
    nomad.NomadArgs(
        console_password=config.require_secret("console_password"),
        instance_type="t4g.micro",
        is_public=False,
        subnets=network.private_subnets,
    ),
)
nomad.Nomad(
    "nomad-public",
    nomad.NomadArgs(
        console_password=config.require_secret("console_password"),
        instance_type="t4g.nano",
        is_public=True,
        subnets=network.public_subnets,
    ),
)

pulumi.export("ipv6_cidr", network.vpc.ipv6_cidr_block)
pulumi.export("vpc_id", network.vpc.id)
pulumi.export("private_subnet_ids", [subnet.id for subnet in network.private_subnets])
pulumi.export("public_subnet_ids", [subnet.id for subnet in network.public_subnets])
