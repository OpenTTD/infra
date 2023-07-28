import base64
import pulumi
import pulumi_aws
import pulumi_openttd
import pulumi_random

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

        nomad_service_key = pulumi_random.RandomPassword(
            f"{name}-nomad-service-key",
            length=32,
            special=False,
        )
        pulumi_openttd.NomadVariable(
            f"{name}-variable-nomad-service-key",
            pulumi_openttd.NomadVariableArgs(
                path=f"deploy-keys/{name}-asg",
                name="key",
                value=nomad_service_key.result,
                overwrite_if_exists=True,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        user_data = pulumi.Output.all(password=args.console_password, service_key=nomad_service_key.result).apply(
            lambda kwargs: f"""#!/bin/bash

echo 'ec2-user:{kwargs['password']}' | chpasswd

TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE=$(curl -H "X-aws-ec2-metadata-token: ${{TOKEN}}" http://169.254.169.254/latest/meta-data/instance-id)

# Set an IPv6 address so we can talk to the outside world.
MAC=$(curl -H "X-aws-ec2-metadata-token: ${{TOKEN}}" http://169.254.169.254/latest/meta-data/network/interfaces/macs/)
PREFIX=$(curl --fail -H "X-aws-ec2-metadata-token: ${{TOKEN}}" http://169.254.169.254/latest/meta-data/network/interfaces/macs/${{MAC}}ipv6-prefix)
ip -6 addr add $(echo ${{PREFIX}} | sed 's@:0:0:0/80@:0:0:1/128@') dev ens5

# Give some time for the IPv6 to get online.
ping -c 1 -W 1 google.com > /dev/null 2>&1

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

pip install \
    aiohttp \
    pproxy \
    # EOL

sysctl -w net.ipv6.ip_nonlocal_bind=1
echo "net.ipv6.ip_nonlocal_bind=1" >> /etc/sysctl.conf

curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/aws-core/files/nomad-{'public' if args.is_public else 'dc1'}.hcl -o /etc/nomad.d/nomad.hcl
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/aws-core/files/nomad.service -o /etc/systemd/system/nomad.service
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/aws-core/files/nomad-rc.local -o /etc/rc.d/rc.local
chmod +x /etc/rc.d/rc.local

systemctl enable rc-local
systemctl start rc-local
systemctl enable nomad
systemctl start nomad

# Give nomad a moment to start up.
sleep 5
nomad node meta apply dibridge.ip_range=$(echo ${{PREFIX}} | sed 's@:0:0:0/80@:2000:0:0/84@')

# ASG endpoint is IPv4 only; so use aws CLI if we are public, and otherwise route it via our Nomad service (which runs on the public nodes).
if [ -n "{'public' if args.is_public else ''}" ]; then
    aws autoscaling set-instance-health --instance-id ${{INSTANCE}} --health-status Healthy
    aws autoscaling complete-lifecycle-action --lifecycle-action-result CONTINUE --instance-id ${{INSTANCE}} --lifecycle-hook-name installed --auto-scaling-group-name nomad-public-asg
else
    curl -s -H "Content-Type: application/json" -X POST -d '{{"instance":"'${{INSTANCE}}'","state":"Healthy"}}' https://nomad-service.openttd.org/autoscaling/nomad-asg/{kwargs['service_key']}
    curl -s -H "Content-Type: application/json" -X POST -d '{{"instance":"'${{INSTANCE}}'","state":"Continue","lifecycle-hook-name":"installed"}}' https://nomad-service.openttd.org/autoscaling/nomad-asg/{kwargs['service_key']}
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
                        volume_size=10,
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

        sns = pulumi_aws.sns.Topic(
            f"{name}-sns-topic",
            name=f"{name}-sns-topic",
            opts=pulumi.ResourceOptions(parent=self),
        )

        pulumi_aws.sns.TopicSubscription(
            f"{name}-sns-subscription",
            endpoint=nomad_service_key.result.apply(
                lambda service_keys: f"https://nomad-service.openttd.org/autoscaling/{name}-asg/{service_keys}"
            ),
            protocol="https",
            topic=sns.arn,
            opts=pulumi.ResourceOptions(parent=sns),
        )

        sns_role = pulumi_aws.iam.Role(
            f"{name}-sns-role",
            assume_role_policy=pulumi_aws.iam.get_policy_document(
                statements=[
                    pulumi_aws.iam.GetPolicyDocumentStatementArgs(
                        actions=["sts:AssumeRole"],
                        effect="Allow",
                        principals=[
                            pulumi_aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                                type="Service",
                                identifiers=["autoscaling.amazonaws.com"],
                            ),
                        ],
                    ),
                ],
            ).json,
            inline_policies=[
                pulumi_aws.iam.RoleInlinePolicyArgs(
                    name="sns-publish",
                    policy=pulumi_aws.iam.get_policy_document(
                        statements=[
                            pulumi_aws.iam.GetPolicyDocumentStatementArgs(
                                actions=["sns:Publish"],
                                effect="Allow",
                                resources=[sns.arn],
                            ),
                        ],
                    ).json,
                ),
            ],
            name=f"{name}-sns-role",
            opts=pulumi.ResourceOptions(parent=sns),
        )

        pulumi_aws.autoscaling.LifecycleHook(
            f"{name}-lifecycle-hook-launching",
            autoscaling_group_name=asg.name,
            default_result="ABANDON",
            heartbeat_timeout=300,
            lifecycle_transition="autoscaling:EC2_INSTANCE_LAUNCHING",
            name="installed",
            opts=pulumi.ResourceOptions(parent=sns),
        )
        pulumi_aws.autoscaling.LifecycleHook(
            f"{name}-lifecycle-hook-terminating",
            autoscaling_group_name=asg.name,
            default_result="CONTINUE",
            heartbeat_timeout=300,
            lifecycle_transition="autoscaling:EC2_INSTANCE_TERMINATING",
            name="removal",
            notification_target_arn=sns.arn,
            role_arn=sns_role.arn,
            opts=pulumi.ResourceOptions(parent=sns),
        )

        self.register_outputs({})
