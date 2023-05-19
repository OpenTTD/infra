import pulumi

import autotag
import network
import nomad

config = pulumi.Config()


autotag.register(
    {
        "Managed-By": "Pulumi",
    }
)

network = network.Network(
    "network",
    network.NetworkArgs(
        "10.0.0.0/16",
    ),
)

nomad = nomad.Nomad(
    "nomad",
    nomad.NomadArgs(
        subnets=network.subnets,
        console_password=config.require_secret("console_password"),
    ),
)
