import ipaddress
import pulumi
import pulumi_oci

from dataclasses import dataclass


@dataclass
class NetworkArgs:
    compartment_id: str
    cidr_block: str
    public_ports: list[tuple[str, int]]


class Network(pulumi.ComponentResource):
    def __init__(self, name, args: NetworkArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("openttd:oci:Network", name, None, opts)

        self.vcn = pulumi_oci.core.Vcn(
            f"{name}-vcn",
            compartment_id=args.compartment_id,
            cidr_blocks=[args.cidr_block],
            dns_label=name,
            is_ipv6enabled=True,
            opts=pulumi.ResourceOptions(parent=self),
        )

        internet_route_table = pulumi_oci.core.RouteTable(
            f"{name}-route-table-internet",
            compartment_id=args.compartment_id,
            vcn_id=self.vcn.id,
            route_rules=[],
            opts=pulumi.ResourceOptions(parent=self.vcn, ignore_changes=["route_rules"]),
        )

        self.gateway_private = pulumi_oci.core.NatGateway(
            f"{name}-gateway-private",
            compartment_id=args.compartment_id,
            vcn_id=self.vcn.id,
            block_traffic=False,
            opts=pulumi.ResourceOptions(parent=self.vcn),
        )
        self.ipv4_gateway = self.gateway_private.nat_ip
        self.gateway_public = pulumi_oci.core.InternetGateway(
            f"{name}-gateway-public",
            compartment_id=args.compartment_id,
            route_table_id=internet_route_table.id,
            vcn_id=self.vcn.id,
            enabled=True,
            opts=pulumi.ResourceOptions(parent=self.vcn),
        )

        self.private_route_table = pulumi_oci.core.RouteTable(
            f"{name}-route-table-private",
            compartment_id=args.compartment_id,
            vcn_id=self.vcn.id,
            route_rules=[
                pulumi_oci.core.RouteTableRouteRuleArgs(
                    description="Traffic to Internet",
                    destination="0.0.0.0/0",
                    destination_type="CIDR_BLOCK",
                    network_entity_id=self.gateway_private.id,
                ),
                pulumi_oci.core.RouteTableRouteRuleArgs(
                    description="Traffic to Internet",
                    destination="::/0",
                    destination_type="CIDR_BLOCK",
                    network_entity_id=self.gateway_public.id,
                ),
            ],
            opts=pulumi.ResourceOptions(parent=self.vcn, ignore_changes=["route_rules"]),
        )
        self.public_route_table = pulumi_oci.core.RouteTable(
            f"{name}-route-table-public",
            compartment_id=args.compartment_id,
            vcn_id=self.vcn.id,
            route_rules=[
                pulumi_oci.core.RouteTableRouteRuleArgs(
                    description="Traffic to Internet",
                    destination="0.0.0.0/0",
                    destination_type="CIDR_BLOCK",
                    network_entity_id=self.gateway_public.id,
                ),
                pulumi_oci.core.RouteTableRouteRuleArgs(
                    description="Traffic to Internet",
                    destination="::/0",
                    destination_type="CIDR_BLOCK",
                    network_entity_id=self.gateway_public.id,
                ),
            ],
            opts=pulumi.ResourceOptions(parent=self.vcn, ignore_changes=["route_rules"]),
        )

        common_egress_security_rules = [
            pulumi_oci.core.SecurityListEgressSecurityRuleArgs(
                description="Allow all traffic to the internet",
                destination="0.0.0.0/0",
                destination_type="CIDR_BLOCK",
                protocol="all",
            ),
            pulumi_oci.core.SecurityListEgressSecurityRuleArgs(
                description="Allow all traffic to the internet",
                destination="::/0",
                destination_type="CIDR_BLOCK",
                protocol="all",
            ),
        ]

        common_ingress_security_rules = [
            pulumi_oci.core.SecurityListIngressSecurityRuleArgs(
                description="Internal traffic",
                source=args.cidr_block,
                source_type="CIDR_BLOCK",
                protocol="all",
            ),
            pulumi_oci.core.SecurityListIngressSecurityRuleArgs(
                description="Internal traffic",
                source=self.vcn.ipv6cidr_blocks.apply(lambda cidr: cidr[0]),
                source_type="CIDR_BLOCK",
                protocol="all",
            ),
            pulumi_oci.core.SecurityListIngressSecurityRuleArgs(
                source="0.0.0.0/0",
                source_type="CIDR_BLOCK",
                protocol="1",  # ICMP
                icmp_options=pulumi_oci.core.SecurityListIngressSecurityRuleIcmpOptionsArgs(
                    code=4,
                    type=3,
                ),
            ),
            pulumi_oci.core.SecurityListIngressSecurityRuleArgs(
                source="::/0",
                source_type="CIDR_BLOCK",
                protocol="58",  # ICMPv6
                icmp_options=pulumi_oci.core.SecurityListIngressSecurityRuleIcmpOptionsArgs(
                    type=2,
                ),
            ),
        ]

        public_ingress = []
        for protocol, port in args.public_ports:
            if protocol == "tcp":
                public_ingress.extend(
                    [
                        pulumi_oci.core.SecurityListIngressSecurityRuleArgs(
                            source=source,
                            source_type="CIDR_BLOCK",
                            protocol="6",
                            tcp_options=pulumi_oci.core.SecurityListIngressSecurityRuleTcpOptionsArgs(
                                max=port,
                                min=port,
                            ),
                        )
                        for source in ["0.0.0.0/0", "::/0"]
                    ]
                )
            elif protocol == "udp":
                public_ingress.extend(
                    [
                        pulumi_oci.core.SecurityListIngressSecurityRuleArgs(
                            source=source,
                            source_type="CIDR_BLOCK",
                            protocol="17",
                            udp_options=pulumi_oci.core.SecurityListIngressSecurityRuleUdpOptionsArgs(
                                max=port,
                                min=port,
                            ),
                        )
                        for source in ["0.0.0.0/0", "::/0"]
                    ]
                )
            else:
                raise ValueError("Unsupported protocol")

        self.private_security_list = pulumi_oci.core.SecurityList(
            f"{name}-security-list-private",
            compartment_id=args.compartment_id,
            vcn_id=self.vcn.id,
            egress_security_rules=common_egress_security_rules,
            ingress_security_rules=common_ingress_security_rules,
            opts=pulumi.ResourceOptions(parent=self.vcn),
        )
        self.public_security_list = pulumi_oci.core.SecurityList(
            f"{name}-security-list-public",
            compartment_id=args.compartment_id,
            vcn_id=self.vcn.id,
            egress_security_rules=common_egress_security_rules,
            ingress_security_rules=common_ingress_security_rules + public_ingress,
            opts=pulumi.ResourceOptions(parent=self.vcn),
        )

        cidr_v4_block = ipaddress.ip_network(args.cidr_block)
        cidr_v6_block = self.vcn.ipv6cidr_blocks.apply(lambda cidr: ipaddress.ip_network(cidr[0]))
        self.cidr_v6_block = cidr_v6_block.apply(lambda cidr: str(cidr))
        if cidr_v4_block.prefixlen > 16:
            raise ValueError("VCN CIDR block must be at least a /16.")

        subnet_cidr_v4_block = list(cidr_v4_block.subnets(prefixlen_diff=2))
        subnet_cidr_v6_block = cidr_v6_block.apply(lambda cidr: list(cidr.subnets(new_prefix=64)))

        cidr_v4_private = str(subnet_cidr_v4_block[0])
        self.cidr_v6_private = subnet_cidr_v6_block[0].apply(lambda cidr: str(cidr))
        self.private_subnet = pulumi_oci.core.Subnet(
            f"{name}-subnet-private",
            compartment_id=args.compartment_id,
            vcn_id=self.vcn.id,
            dns_label="private",
            cidr_block=cidr_v4_private,
            ipv6cidr_block=self.cidr_v6_private,
            prohibit_internet_ingress=False,
            prohibit_public_ip_on_vnic=False,
            route_table_id=self.private_route_table.id,
            security_list_ids=[self.private_security_list.id],
            opts=pulumi.ResourceOptions(parent=self.vcn),
        )
        cidr_v4_public = str(subnet_cidr_v4_block[1])
        self.cidr_v6_public = subnet_cidr_v6_block[1].apply(lambda cidr: str(cidr))
        self.public_subnet = pulumi_oci.core.Subnet(
            f"{name}-subnet-public",
            compartment_id=args.compartment_id,
            vcn_id=self.vcn.id,
            dns_label="public",
            cidr_block=cidr_v4_public,
            ipv6cidr_block=self.cidr_v6_public,
            prohibit_internet_ingress=False,
            prohibit_public_ip_on_vnic=False,
            route_table_id=self.public_route_table.id,
            security_list_ids=[self.public_security_list.id],
            opts=pulumi.ResourceOptions(parent=self.vcn),
        )

        # OCI doesn't allow IPv6 prefix delegation to instances. So we have a
        # second subnet, and on-instance-start, instances add routes to the
        # routing tables to route traffic from an IPv6 prefix to their
        # instance.
        cidr_v4_private = str(subnet_cidr_v4_block[2])
        self.cidr_v6_private_prefix = subnet_cidr_v6_block[2].apply(lambda cidr: str(cidr))
        self.private_subnet_prefix = pulumi_oci.core.Subnet(
            f"{name}-subnet-private-prefix",
            compartment_id=args.compartment_id,
            vcn_id=self.vcn.id,
            cidr_block=cidr_v4_private,
            ipv6cidr_block=self.cidr_v6_private_prefix,
            prohibit_internet_ingress=False,
            prohibit_public_ip_on_vnic=False,
            security_list_ids=[self.private_security_list.id],
            opts=pulumi.ResourceOptions(parent=self.vcn),
        )
        cidr_v4_public = str(subnet_cidr_v4_block[3])
        self.cidr_v6_public_prefix = subnet_cidr_v6_block[3].apply(lambda cidr: str(cidr))
        self.public_subnet_prefix = pulumi_oci.core.Subnet(
            f"{name}-subnet-public-prefix",
            compartment_id=args.compartment_id,
            vcn_id=self.vcn.id,
            cidr_block=cidr_v4_public,
            ipv6cidr_block=self.cidr_v6_public_prefix,
            prohibit_internet_ingress=False,
            prohibit_public_ip_on_vnic=False,
            security_list_ids=[self.public_security_list.id],
            opts=pulumi.ResourceOptions(parent=self.vcn),
        )

        self.register_outputs(
            {
                "vcn_id": self.vcn.id,
                "private_subnet_id": self.private_subnet.id,
                "public_subnet_id": self.public_subnet.id,
            }
        )
