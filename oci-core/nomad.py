import base64
import ipaddress
import pulumi
import pulumi_oci

from dataclasses import dataclass


@dataclass
class NomadArgs:
    console_password: pulumi.Output[str]
    compartment_id: str
    is_public: bool
    subnet_id: pulumi.Output[str]
    subnet_prefix_id: pulumi.Output[str]
    ipv6_cidr: pulumi.Output[str]
    ipv6_prefix_cidr: pulumi.Output[str]
    size: int


class Nomad(pulumi.ComponentResource):
    def __init__(self, name, args: NomadArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("openttd:oci:Nomad", name, None, opts)

        image_id = (
            pulumi_oci.core.get_images(
                compartment_id=args.compartment_id,
                operating_system="Oracle Linux",
                operating_system_version="9",
                shape="VM.Standard.A1.Flex",
                sort_by="TIMECREATED",
                sort_order="DESC",
            )
            .images[0]
            .id
        )

        availability_domain = (
            pulumi_oci.identity.get_availability_domains(compartment_id=args.compartment_id)
            .availability_domains[0]
            .name
        )

        user_data = pulumi.Output.all(password=args.console_password).apply(
            lambda kwargs: f"""#!/bin/bash

echo 'opc:{kwargs['password']}' | chpasswd

NODE_NUMBER=$(hostname | rev | cut -d- -f1 | rev | xargs -n 1 printf "%x")

# For NIC 0, assign a known IPv6.
CIDR_BLOCK=$(oci-metadata --get "vnics/*/ipv6SubnetCidrBlock" --json | jq -r '.vnics[0].ipv6SubnetCidrBlock' | sed 's/0000:0000:0000:0000/:/')
PREFIX=$(echo ${{CIDR_BLOCK}} | sed "s@:/64@${{NODE_NUMBER}}:0:0:0/80@")
LOCAL_IP=$(echo ${{PREFIX}} | sed 's@:0:0:0/80@:0:0:1@')
LOCAL_VNIC=$(oci-metadata -j | jq '.vnics[0].vnicId' -r)
oci-network-config add-secondary-addr -I ${{LOCAL_IP}} -O ${{LOCAL_VNIC}}

# For NIC 1, assign a known IPv6.
CIDR_BLOCK=$(oci-metadata --get "vnics/*/ipv6SubnetCidrBlock" --json | jq -r '.vnics[1].ipv6SubnetCidrBlock' | sed 's/0000:0000:0000:0000/:/')
PREFIX=$(echo ${{CIDR_BLOCK}} | sed "s@:/64@${{NODE_NUMBER}}:0:0:0/80@")
LOCAL_IP=$(echo ${{PREFIX}} | sed 's@:0:0:0/80@:0:0:1@')
LOCAL_VNIC=$(oci-metadata -j | jq '.vnics[1].vnicId' -r)
oci-network-config add-secondary-addr -I ${{LOCAL_IP}} -O ${{LOCAL_VNIC}}

# Disable NIC 1, as all IPv6 traffic will arrive on NIC 0.
ip link set enp1s0 down

# Give some time for the IPv6 to get online.
ping -c 1 -W 1 google.com > /dev/null 2>&1

dnf config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
dnf install -y \
    docker-ce \
    nomad \
    python3-pip \
    # EOF

pip install \
    aiohttp \
    oci-cli \
    pproxy \
    # EOL

sysctl -w net.ipv6.ip_nonlocal_bind=1
echo "net.ipv6.ip_nonlocal_bind=1" >> /etc/sysctl.conf

# Ensure we can "sudo" via RunCommands.
echo "ocarun ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/101-oracle-cloud-agent-run-command

curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/oci-core/files/nomad-{'public' if args.is_public else 'dc1'}.hcl -o /etc/nomad.d/nomad.hcl
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/oci-core/files/nomad.service -o /etc/systemd/system/nomad.service
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/oci-core/files/oci-list-pool-ips.sh -o /usr/bin/oci-list-pool-ips.sh
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/oci-core/files/oci-update-route-table.sh -o /usr/bin/oci-update-route-table.sh
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/oci-core/files/nomad-rc.local -o /etc/rc.d/rc.local

sed -i s/@COMPARTMENT_ID@/{args.compartment_id}/g /usr/bin/oci-list-pool-ips.sh
sed -i s/@COMPARTMENT_ID@/{args.compartment_id}/g /usr/bin/oci-update-route-table.sh
chmod +x /etc/rc.d/rc.local
chmod +x /usr/bin/oci-list-pool-ips.sh
chmod +x /usr/bin/oci-update-route-table.sh

# Disable the firewall. We block traffic on the VCN level.
systemctl stop firewalld
systemctl disable firewalld
systemctl mask firewalld

# Enable the IPv6 prefix routes in all Route Tables.
oci-update-route-table.sh

systemctl enable rc-local
systemctl start rc-local
systemctl enable nomad
systemctl start nomad

# Give nomad a moment to start up.
while true; do
    nomad node meta apply dibridge.ip_range=$(echo ${{PREFIX}} | sed 's@:0:0:0/80@:2000:0:0/84@')
    if [ $? -eq 0 ]; then
        break
    fi
    sleep 1
done

"""
        )

        instance_config = pulumi_oci.core.InstanceConfiguration(
            f"{name}-instance-config",
            compartment_id=args.compartment_id,
            instance_details=pulumi_oci.core.InstanceConfigurationInstanceDetailsArgs(
                instance_type="compute",
                block_volumes=[],
                launch_details=pulumi_oci.core.InstanceConfigurationInstanceDetailsLaunchDetailsArgs(
                    agent_config=pulumi_oci.core.InstanceConfigurationInstanceDetailsLaunchDetailsAgentConfigArgs(
                        is_management_disabled=False,
                    ),
                    compartment_id=args.compartment_id,
                    create_vnic_details=pulumi_oci.core.InstanceConfigurationInstanceDetailsLaunchDetailsCreateVnicDetailsArgs(
                        assign_ipv6ip=False,
                        assign_public_ip=args.is_public,
                        subnet_id=args.subnet_id,
                        skip_source_dest_check=True,
                        freeform_tags={
                            "AutoJoin": name,
                        },
                    ),
                    instance_options=pulumi_oci.core.InstanceConfigurationInstanceDetailsLaunchDetailsInstanceOptionsArgs(
                        are_legacy_imds_endpoints_disabled=False,
                    ),
                    is_pv_encryption_in_transit_enabled=True,
                    metadata={
                        "user_data": user_data.apply(lambda user_data: base64.b64encode(user_data.encode()).decode()),
                    },
                    defined_tags={
                        "Infra.Managed-By": "InstanceConfiguration",
                        "Infra.Name": name,
                    },
                    shape="VM.Standard.A1.Flex",
                    shape_config=pulumi_oci.core.InstanceConfigurationInstanceDetailsLaunchDetailsShapeConfigArgs(
                        memory_in_gbs=4,
                        ocpus=1,
                    ),
                    source_details=pulumi_oci.core.InstanceConfigurationInstanceDetailsLaunchDetailsSourceDetailsArgs(
                        source_type="image",
                        image_id=image_id,
                        boot_volume_size_in_gbs=50,
                    ),
                ),
                secondary_vnics=[
                    pulumi_oci.core.InstanceConfigurationInstanceDetailsSecondaryVnicArgs(
                        display_name="IPv6 Prefix",
                        create_vnic_details=pulumi_oci.core.InstanceConfigurationInstanceDetailsSecondaryVnicCreateVnicDetailsArgs(
                            assign_ipv6ip=False,
                            assign_public_ip=False,
                            subnet_id=args.subnet_prefix_id,
                        ),
                    ),
                ],
            ),
            source="NONE",
            opts=pulumi.ResourceOptions(parent=self),
        )

        pulumi_oci.core.InstancePool(
            f"{name}-instance-pool",
            compartment_id=args.compartment_id,
            instance_configuration_id=instance_config.id,
            instance_display_name_formatter=f"{name}-${{launchCount}}",
            placement_configurations=[
                pulumi_oci.core.InstancePoolPlacementConfigurationArgs(
                    availability_domain=availability_domain,
                    primary_vnic_subnets=pulumi_oci.core.InstancePoolPlacementConfigurationPrimaryVnicSubnetsArgs(
                        subnet_id=args.subnet_id,
                    ),
                    secondary_vnic_subnets=[
                        pulumi_oci.core.InstancePoolPlacementConfigurationSecondaryVnicSubnetArgs(
                            display_name="IPv6 Prefix",
                            subnet_id=args.subnet_prefix_id,
                        ),
                    ],
                ),
            ],
            size=args.size,
            opts=pulumi.ResourceOptions(parent=self, ignore_changes=["size"]),
        )

        self.register_outputs({})
