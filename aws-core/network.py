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

        vpc_name = f"{name}-vpc"
        self.vpc = pulumi_aws.ec2.Vpc(
            vpc_name,
            assign_generated_ipv6_cidr_block=True,
            cidr_block=args.cidr_block,
            tags={
                "Name": vpc_name,
            },
            opts=pulumi.ResourceOptions(parent=self),
        )

        gateway_name = f"{name}-gateway"
        self.gateway = pulumi_aws.ec2.EgressOnlyInternetGateway(
            gateway_name,
            vpc_id=self.vpc.id,
            tags={
                "Name": gateway_name,
            },
            opts=pulumi.ResourceOptions(parent=self),
        )

        route_table_name = f"{name}-route-table"
        self.route_table = pulumi_aws.ec2.RouteTable(
            route_table_name,
            routes=[
                pulumi_aws.ec2.RouteTableRouteArgs(
                    ipv6_cidr_block="::/0",
                    egress_only_gateway_id=self.gateway.id,
                ),
            ],
            vpc_id=self.vpc.id,
            tags={
                "Name": route_table_name,
            },
            opts=pulumi.ResourceOptions(parent=self),
        )

        cidr_v4_block = ipaddress.ip_network(args.cidr_block)
        cidr_v6_block = self.vpc.ipv6_cidr_block.apply(lambda cidr: ipaddress.ip_network(cidr))
        if cidr_v4_block.prefixlen > 16:
            raise ValueError("VPC CIDR block must be at least a /16.")

        # Split in 4 subnets; most regions only have 2 or 3 AZs, so we should be fine here.
        subnet_cidr_v4_block = list(cidr_v4_block.subnets(prefixlen_diff=2))
        # We use /64 here, because by all means that should be sufficient.
        subnet_cidr_v6_block = cidr_v6_block.apply(lambda cidr: list(cidr.subnets(new_prefix=64)))

        self.subnets = []
        for i, zone in enumerate(pulumi_aws.get_availability_zones().names):
            subnet_name = f"{name}-subnet-{i + 1}"

            cidr_v4 = str(subnet_cidr_v4_block[i])
            cidr_v6 = subnet_cidr_v6_block[i].apply(lambda cidr: str(cidr))

            subnet = pulumi_aws.ec2.Subnet(
                subnet_name,
                assign_ipv6_address_on_creation=True,
                availability_zone=zone,
                cidr_block=cidr_v4,
                ipv6_cidr_block=cidr_v6,
                vpc_id=self.vpc.id,
                tags={
                    "Name": subnet_name,
                },
                opts=pulumi.ResourceOptions(parent=self),
            )

            pulumi_aws.ec2.RouteTableAssociation(
                f"{name}-subnet-{i + 1}-route",
                route_table_id=self.route_table.id,
                subnet_id=subnet.id,
                opts=pulumi.ResourceOptions(parent=self),
            )

            self.subnets.append(subnet)

        self.register_outputs(
            {
                "vpc_id": self.vpc.id,
                "subnets": [subnet.id for subnet in self.subnets],
            }
        )
