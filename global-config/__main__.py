import pulumi

config = pulumi.Config()

pulumi.export("domain", config.require("domain"))
