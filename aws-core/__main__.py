import pulumi
import pulumi_aws
import pulumi_openttd

import network
import nomad

config = pulumi.Config()


pulumi_openttd.autotag.register()

PUBLIC_PORTS = [
    ("tcp", 3978),  # bananas-server
    ("tcp", 4978),  # bananas-server-preview
]

network = network.Network(
    "network",
    network.NetworkArgs(
        "10.0.0.0/16",
    ),
)

# This SG tags all Nomad hosts, so they can talk freely with each other.
security_group = pulumi_aws.ec2.SecurityGroup(
    f"sg-nomad-cluster",
    name="nomad-cluster",
    vpc_id=network.vpc.id,
)
pulumi_aws.ec2.SecurityGroupRule(
    f"sg-nomad-cluster-egress",
    cidr_blocks=["0.0.0.0/0"],
    from_port=0,
    ipv6_cidr_blocks=["::/0"],
    protocol="-1",
    security_group_id=security_group.id,
    to_port=0,
    type="egress",
    opts=pulumi.ResourceOptions(parent=security_group),
)
pulumi_aws.ec2.SecurityGroupRule(
    f"sg-nomad-cluster-ingress",
    from_port=0,
    protocol="-1",
    security_group_id=security_group.id,
    source_security_group_id=security_group.id,
    to_port=0,
    type="ingress",
    opts=pulumi.ResourceOptions(parent=security_group),
)

public_security_group = pulumi_aws.ec2.SecurityGroup(
    f"sg-nomad-public",
    egress=[],
    ingress=[
        pulumi_aws.ec2.SecurityGroupIngressArgs(
            cidr_blocks=["0.0.0.0/0"],
            from_port=port,
            ipv6_cidr_blocks=["::/0"],
            protocol=protocol,
            to_port=port,
        )
        for (protocol, port) in PUBLIC_PORTS
    ],
    name="nomad-public",
    vpc_id=network.vpc.id,
)

nomad.Nomad(
    "nomad",
    nomad.NomadArgs(
        console_password=config.require_secret("console_password"),
        instance_type="t4g.micro",
        is_public=False,
        security_groups=[security_group.id],
        subnets=network.private_subnets,
        vpc_id=network.vpc.id,
    ),
)
nomad.Nomad(
    "nomad-public",
    nomad.NomadArgs(
        console_password=config.require_secret("console_password"),
        instance_type="t4g.nano",
        is_public=True,
        security_groups=[security_group.id, public_security_group.id],
        subnets=network.public_subnets,
        vpc_id=network.vpc.id,
    ),
)

pulumi.export("ipv6_cidr", network.vpc.ipv6_cidr_block)
pulumi.export("vpc_id", network.vpc.id)
pulumi.export("private_subnet_ids", [subnet.id for subnet in network.private_subnets])
pulumi.export("public_subnet_ids", [subnet.id for subnet in network.public_subnets])
