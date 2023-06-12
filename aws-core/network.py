import ipaddress
import pulumi
import pulumi_aws

from dataclasses import dataclass


@dataclass
class NetworkArgs:
    cidr_block: str


class Network(pulumi.ComponentResource):
    def __init__(self, name, args: NetworkArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("openttd:aws:Network", name, None, opts)

        self.vpc = pulumi_aws.ec2.Vpc(
            f"{name}-vpc",
            assign_generated_ipv6_cidr_block=True,
            cidr_block=args.cidr_block,
            enable_dns_hostnames=True,
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.private_gateway = pulumi_aws.ec2.EgressOnlyInternetGateway(
            f"{name}-gateway-private",
            vpc_id=self.vpc.id,
            opts=pulumi.ResourceOptions(parent=self.vpc),
        )
        self.public_gateway = pulumi_aws.ec2.InternetGateway(
            f"{name}-gateway-public",
            vpc_id=self.vpc.id,
            opts=pulumi.ResourceOptions(parent=self.vpc),
        )

        self.private_route_table = pulumi_aws.ec2.RouteTable(
            f"{name}-route-table-private",
            routes=[
                pulumi_aws.ec2.RouteTableRouteArgs(
                    ipv6_cidr_block="::/0",
                    egress_only_gateway_id=self.private_gateway.id,
                ),
            ],
            vpc_id=self.vpc.id,
            opts=pulumi.ResourceOptions(parent=self.vpc),
        )
        self.public_route_table = pulumi_aws.ec2.RouteTable(
            f"{name}-route-table-public",
            routes=[
                pulumi_aws.ec2.RouteTableRouteArgs(
                    ipv6_cidr_block="::/0",
                    gateway_id=self.public_gateway.id,
                ),
                pulumi_aws.ec2.RouteTableRouteArgs(
                    cidr_block="0.0.0.0/0",
                    gateway_id=self.public_gateway.id,
                ),
            ],
            vpc_id=self.vpc.id,
            opts=pulumi.ResourceOptions(parent=self.vpc),
        )

        cidr_v4_block = ipaddress.ip_network(args.cidr_block)
        cidr_v6_block = self.vpc.ipv6_cidr_block.apply(lambda cidr: ipaddress.ip_network(cidr))
        if cidr_v4_block.prefixlen > 16:
            raise ValueError("VPC CIDR block must be at least a /16.")

        # We expect 3 AZs; we use 3 /18s for the private, and 3 /20s for the public.
        subnet_cidr_v4_block = list(cidr_v4_block.subnets(prefixlen_diff=2))
        # We use /64 here, because by all means that should be sufficient.
        subnet_cidr_v6_block = cidr_v6_block.apply(lambda cidr: list(cidr.subnets(new_prefix=64)))

        self.private_subnets = []
        for i, zone in enumerate(pulumi_aws.get_availability_zones().names):
            cidr_v4 = str(subnet_cidr_v4_block[i])
            cidr_v6 = subnet_cidr_v6_block[i].apply(lambda cidr: str(cidr))

            subnet = pulumi_aws.ec2.Subnet(
                f"{name}-subnet-private-{i + 1}",
                assign_ipv6_address_on_creation=True,
                availability_zone=zone,
                cidr_block=cidr_v4,
                ipv6_cidr_block=cidr_v6,
                vpc_id=self.vpc.id,
                opts=pulumi.ResourceOptions(parent=self.vpc),
            )

            pulumi_aws.ec2.RouteTableAssociation(
                f"{name}-subnet-private-{i + 1}-route",
                route_table_id=self.private_route_table.id,
                subnet_id=subnet.id,
                opts=pulumi.ResourceOptions(parent=subnet),
            )

            self.private_subnets.append(subnet)

        subnet_cidr_v4_block = list(subnet_cidr_v4_block[3].subnets(prefixlen_diff=2))

        self.public_subnets = []
        for i, zone in enumerate(pulumi_aws.get_availability_zones().names):
            cidr_v4 = str(subnet_cidr_v4_block[i])
            cidr_v6 = subnet_cidr_v6_block[i + 3].apply(lambda cidr: str(cidr))

            subnet = pulumi_aws.ec2.Subnet(
                f"{name}-subnet-public-{i + 1}",
                assign_ipv6_address_on_creation=True,
                availability_zone=zone,
                cidr_block=cidr_v4,
                ipv6_cidr_block=cidr_v6,
                vpc_id=self.vpc.id,
                opts=pulumi.ResourceOptions(parent=self.vpc),
            )

            pulumi_aws.ec2.RouteTableAssociation(
                f"{name}-subnet-public-{i + 1}-route",
                route_table_id=self.public_route_table.id,
                subnet_id=subnet.id,
                opts=pulumi.ResourceOptions(parent=subnet),
            )

            self.public_subnets.append(subnet)

        self.register_outputs(
            {
                "vpc_id": self.vpc.id,
                "private_subnets": [subnet.id for subnet in self.private_subnets],
                "public_subnets": [subnet.id for subnet in self.public_subnets],
            }
        )
