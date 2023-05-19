import pulumi
import pulumi_aws

from dataclasses import dataclass


@dataclass
class NomadArgs:
    subnets: list[str]
    console_password: pulumi.Output[str]


class Nomad(pulumi.ComponentResource):
    def __init__(self, name, args: NomadArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("openttd:aws:Nomad", name, None, opts)

        ami = pulumi_aws.ec2.get_ami(
            filters=[
                pulumi_aws.ec2.GetAmiFilterArgs(
                    name="name",
                    values=["al2023-ami-2*-arm64"],
                )
            ],
            owners=["amazon"],
            most_recent=True,
        ).id

        user_data = args.console_password.apply(
            lambda password: f"""#!/bin/bash

dnf install -y \
    cni-plugins \
    gzip \
    iproute \
    docker \
    shadow-utils \
    tar \
    yum-utils \
    # EOF

dnf config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo
dnf install -y nomad

echo 'ec2-user:{password}' | chpasswd

curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/files/nomad.hcl -o /etc/nomad.d/nomad.hcl
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/files/nomad.service -o /etc/systemd/system/nomad.service

systemctl enable docker
systemctl start docker

systemctl enable nomad
systemctl start nomad
"""
        )

        instance_name = f"{name}-instance"
        self.instance = pulumi_aws.ec2.Instance(
            instance_name,
            ami=ami,
            instance_type="t4g.micro",
            root_block_device=pulumi_aws.ec2.InstanceRootBlockDeviceArgs(
                volume_size=30,
            ),
            subnet_id=args.subnets[0],
            user_data=user_data,
            user_data_replace_on_change=True,
            # vps_security_group_ids=[],  # TODO -- add security group; using "default" is a bad idea
            tags={
                "AutoJoin": "production",
                "Name": instance_name,
            },
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.register_outputs({})
