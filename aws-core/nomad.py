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

curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/aws-core/files/nomad.hcl -o /etc/nomad.d/nomad.hcl
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/aws-core/files/nomad.service -o /etc/systemd/system/nomad.service
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/aws-core/files/nomad-rc.local -o /etc/rc.local
chmod +x /etc/rc.local
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/aws-core/files/nomad-proxy.service -o /etc/systemd/system/nomad-proxy.service
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/aws-core/files/nomad-proxy.py -o /usr/bin/nomad-proxy
chmod +x /usr/bin/nomad-proxy

# Run rc.local now, to avoid a reboot.
/etc/rc.local

systemctl enable nomad
systemctl start nomad
systemctl enable nomad-proxy
systemctl start nomad-proxy
"""
        )

        eni = pulumi_aws.ec2.NetworkInterface(
            f"{name}-eni",
            subnet_id=args.subnets[0],
            ipv6_address_count=1,
            ipv6_prefix_count=1,
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.instance = pulumi_aws.ec2.Instance(
            f"{name}-instance",
            ami=ami,
            instance_type="t4g.micro",
            network_interfaces=[
                pulumi_aws.ec2.InstanceNetworkInterfaceArgs(
                    network_interface_id=eni.id,
                    device_index=0,
                )
            ],
            root_block_device=pulumi_aws.ec2.InstanceRootBlockDeviceArgs(
                volume_size=30,
            ),
            user_data=user_data,
            user_data_replace_on_change=True,
            # vps_security_group_ids=[],  # TODO -- add security group; using "default" is a bad idea
            tags={
                "AutoJoin": "production",
            },
            opts=pulumi.ResourceOptions(
                parent=self,
                delete_before_replace=True,
            ),
        )

        self.register_outputs({})
