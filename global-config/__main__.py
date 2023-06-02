import pulumi

config = pulumi.Config()

pulumi.export("domain", config.require("domain"))
pulumi.export("cloudflare_account_id", config.require_secret("cloudflare_account_id"))
pulumi.export("cloudflare_zone_id", config.require_secret("cloudflare_zone_id"))
pulumi.export("sentry_ingest_hostname", config.require("sentry_ingest_hostname"))
