import base64
import pulumi
import pulumi_aws

from dataclasses import dataclass


@dataclass
class NomadArgs:
    console_password: pulumi.Output[str]
    instance_type: str
    is_public: bool
    security_groups: list[str]
    subnets: list[str]
    vpc_id: str


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
        )

        user_data = args.console_password.apply(
            lambda password: f"""#!/bin/bash

echo 'ec2-user:{password}' | chpasswd

TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE=$(curl -H "X-aws-ec2-metadata-token: ${{TOKEN}}" http://169.254.169.254/latest/meta-data/instance-id)

# Set an IPv6 address so we can talk to the outside world.
MAC=$(curl -H "X-aws-ec2-metadata-token: ${{TOKEN}}" http://169.254.169.254/latest/meta-data/network/interfaces/macs/)
PREFIX=$(curl --fail -H "X-aws-ec2-metadata-token: ${{TOKEN}}" http://169.254.169.254/latest/meta-data/network/interfaces/macs/${{MAC}}ipv6-prefix)
ip -6 addr add $(echo ${{PREFIX}} | sed 's@:0:0:0/80@:0:0:1/128@') dev ens5

# Currently fails as ASG endpoint is IPv4 only.
if [ -n "{'public' if args.is_public else ''}" ]; then
    aws autoscaling set-instance-health --instance-id ${{INSTANCE}} --health-status Unhealthy
fi

dnf install -y \
    cni-plugins \
    docker \
    gzip \
    iproute \
    python3-pip \
    shadow-utils \
    tar \
    yum-utils \
    # EOF

dnf config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo
dnf install -y nomad

pip install aiohttp

curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/aws-core/files/nomad-{'public' if args.is_public else 'dc1'}.hcl -o /etc/nomad.d/nomad.hcl
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/aws-core/files/nomad.service -o /etc/systemd/system/nomad.service
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/aws-core/files/nomad-rc.local -o /etc/rc.d/rc.local
chmod +x /etc/rc.d/rc.local

systemctl enable rc-local
systemctl start rc-local
systemctl enable nomad
systemctl start nomad

# Currently fails as ASG endpoint is IPv4 only.
if [ -n "{'public' if args.is_public else ''}" ]; then
    aws autoscaling set-instance-health --instance-id ${{INSTANCE}} --health-status Healthy
    aws autoscaling complete-lifecycle-action --lifecycle-action-result CONTINUE --instance-id ${{INSTANCE}} --lifecycle-hook-name installed --auto-scaling-group-name nomad{'-public' if args.is_public else ''}-asg
fi
"""
        )

        iam_policy = pulumi_aws.iam.Policy(
            f"{name}-iam-policy",
            name=f"{name}-ec2-policy",
            policy=pulumi_aws.iam.get_policy_document(
                statements=[
                    pulumi_aws.iam.GetPolicyDocumentStatementArgs(
                        actions=[
                            "ec2:DescribeInstances",
                            "autoscaling:SetInstanceHealth",
                            "autoscaling:CompleteLifecycleAction",
                        ],
                        resources=["*"],
                        effect="Allow",
                    ),
                ],
            ).json,
            opts=pulumi.ResourceOptions(parent=self),
        )

        iam_role = pulumi_aws.iam.Role(
            f"{name}-iam-role",
            assume_role_policy=pulumi_aws.iam.get_policy_document(
                statements=[
                    pulumi_aws.iam.GetPolicyDocumentStatementArgs(
                        actions=["sts:AssumeRole"],
                        principals=[
                            pulumi_aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                                type="Service",
                                identifiers=["ec2.amazonaws.com"],
                            ),
                        ],
                        effect="Allow",
                    ),
                ],
            ).json,
            managed_policy_arns=[
                iam_policy.arn,
            ],
            name=f"{name}-ec2-role",
            opts=pulumi.ResourceOptions(parent=iam_policy),
        )

        iam_instance_profile = pulumi_aws.iam.InstanceProfile(
            f"{name}-iam-profile",
            name=f"{name}-ec2-profile",
            role=iam_role.name,
            opts=pulumi.ResourceOptions(parent=iam_role),
        )

        launch_template = pulumi_aws.ec2.LaunchTemplate(
            f"{name}-launch-template",
            block_device_mappings=[
                pulumi_aws.ec2.LaunchTemplateBlockDeviceMappingArgs(
                    device_name="/dev/xvda",
                    ebs=pulumi_aws.ec2.LaunchTemplateBlockDeviceMappingEbsArgs(
                        volume_size=10 if args.is_public else 30,
                    ),
                )
            ],
            iam_instance_profile=pulumi_aws.ec2.LaunchTemplateIamInstanceProfileArgs(
                arn=iam_instance_profile.arn,
            ),
            image_id=ami.id,
            instance_type=args.instance_type,
            name=name,
            network_interfaces=[
                pulumi_aws.ec2.LaunchTemplateNetworkInterfaceArgs(
                    associate_public_ip_address=args.is_public,
                    device_index=0,
                    ipv6_prefix_count=1,
                    security_groups=args.security_groups,
                ),
            ],
            tag_specifications=[
                pulumi_aws.ec2.LaunchTemplateTagSpecificationArgs(
                    resource_type="instance",
                    tags={
                        "AutoJoin": f"{name}",
                    },
                ),
            ],
            update_default_version=True,
            user_data=user_data.apply(lambda user_data: base64.b64encode(user_data.encode()).decode()),
            opts=pulumi.ResourceOptions(parent=self),
        )

        asg = pulumi_aws.autoscaling.Group(
            f"{name}-asg",
            health_check_grace_period=30,
            health_check_type="EC2",
            launch_template=pulumi_aws.autoscaling.GroupLaunchTemplateArgs(
                id=launch_template.id,
                version=launch_template.latest_version,
            ),
            max_size=6,
            min_size=1,
            name=f"{name}-asg",
            tags=[
                pulumi_aws.autoscaling.GroupTagArgs(
                    key="Managed-By",
                    propagate_at_launch=True,
                    value="Pulumi",
                ),
                pulumi_aws.autoscaling.GroupTagArgs(
                    key="Name",
                    propagate_at_launch=True,
                    value=name,
                ),
            ],
            termination_policies=[
                "OldestLaunchTemplate",
                "OldestInstance",
            ],
            vpc_zone_identifiers=args.subnets,
            opts=pulumi.ResourceOptions(parent=self),
        )

        if args.is_public:
            pulumi_aws.autoscaling.LifecycleHook(
                f"{name}-lifecycle-hook",
                autoscaling_group_name=asg.name,
                default_result="ABANDON",
                heartbeat_timeout=300,
                lifecycle_transition="autoscaling:EC2_INSTANCE_LAUNCHING",
                name="installed",
            )

        self.register_outputs({})
