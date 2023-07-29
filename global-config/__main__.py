import pulumi

config = pulumi.Config()

pulumi.export("cloudflare_account_id", config.require_secret("cloudflare-account-id"))
pulumi.export("cloudflare_zone_id", config.require_secret("cloudflare-zone-id"))
pulumi.export("domain", config.require("domain"))
pulumi.export("grafana_prometheus_hostname", config.require("grafana-prometheus-hostname"))
pulumi.export("sentry_ingest_hostname", config.require("sentry-ingest-hostname"))
