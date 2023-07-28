import pulumi
import pulumi_aws
import pulumi_openttd

import network
import nomad

config = pulumi.Config()


pulumi_openttd.autotag.register()

PUBLIC_PORTS = [
    ("tcp", 113),   # ident, used by IRC
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
        instance_type="t4g.medium",
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
        instance_type="t4g.micro",
        is_public=True,
        security_groups=[security_group.id, public_security_group.id],
        subnets=network.public_subnets,
        vpc_id=network.vpc.id,
    ),
)

s3_datasync = pulumi_aws.s3.BucketV2(
    "datasync",
    bucket="openttd-datasync",
)

s3_datasync_iam_policy = pulumi_aws.iam.Policy(
    "datasync-iam-policy",
    name="datasync-policy",
    policy=pulumi_aws.iam.get_policy_document(
        statements=[
            pulumi_aws.iam.GetPolicyDocumentStatementArgs(
                actions=[
                    "s3:GetBucketLocation",
                    "s3:ListBucket",
                    "s3:ListBucketMultipartUploads",
                ],
                resources=[s3_datasync.arn],
                effect="Allow",
            ),
            pulumi_aws.iam.GetPolicyDocumentStatementArgs(
                actions=[
                    "s3:AbortMultipartUpload",
                    "s3:DeleteObject",
                    "s3:GetObject",
                    "s3:ListMultipartUploadParts",
                    "s3:GetObjectTagging",
                    "s3:PutObjectTagging",
                    "s3:PutObject",
                ],
                resources=[pulumi.Output.format("{}/*", s3_datasync.arn)],
                effect="Allow",
            ),
        ],
    ).json,
    opts=pulumi.ResourceOptions(),
)

s3_datasync_iam = pulumi_aws.iam.Role(
    "datasync-iam-role",
    assume_role_policy=pulumi_aws.iam.get_policy_document(
        statements=[
            pulumi_aws.iam.GetPolicyDocumentStatementArgs(
                actions=["sts:AssumeRole"],
                principals=[
                    pulumi_aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                        type="Service",
                        identifiers=["datasync.amazonaws.com"],
                    ),
                ],
                effect="Allow",
            ),
        ],
    ).json,
    managed_policy_arns=[
        s3_datasync_iam_policy.arn,
    ],
    name=f"datasync-role",
    opts=pulumi.ResourceOptions(parent=s3_datasync_iam_policy),
)

pulumi.export("ipv6_cidr", network.vpc.ipv6_cidr_block)
pulumi.export("vpc_id", network.vpc.id)
pulumi.export("private_subnet_arns", [subnet.arn for subnet in network.private_subnets])
pulumi.export("private_subnet_ids", [subnet.id for subnet in network.private_subnets])
pulumi.export("public_subnet_ids", [subnet.id for subnet in network.public_subnets])
pulumi.export("nomad_security_group_arn", security_group.arn)
pulumi.export("nomad_security_group_id", security_group.id)
pulumi.export("s3_datasync_arn", s3_datasync.arn)
pulumi.export("s3_datasync_iam_arn", s3_datasync_iam.arn)
