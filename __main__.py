import pulumi

import autotag
import network

config = pulumi.Config()


autotag.register(
    {
        "Managed-By": "Pulumi",
    }
)

network = network.Network("network", network.NetworkArgs("10.0.0.0/16"))
