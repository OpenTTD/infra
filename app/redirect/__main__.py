import pulumi
import pulumi_cloudflare


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")

HOSTNAMES = [
    "bugs",
    "download",
    "forum",
    "github",
    "grfsearch",
    "nightly",
    "noai",
    "nogo",
    "security",
]

name = f"redirect-{pulumi.get_stack()}"
worker = pulumi_cloudflare.WorkerScript(
    "worker",
    account_id=global_stack.get_output("cloudflare_account_id"),
    content=global_stack.get_output("domain").apply(
        lambda domain: open(f"files/cfw-redirect.js").read().replace("[[ domain ]]", domain)
    ),
    logpush=True,
    name=name,
    module=True,
)

for hostname in HOSTNAMES:
    pulumi_cloudflare.WorkerDomain(
        f"worker-domain-{hostname}",
        account_id=global_stack.get_output("cloudflare_account_id"),
        hostname=pulumi.Output.format("{}.{}", hostname, global_stack.get_output("domain")),
        service=name,
        zone_id=global_stack.get_output("cloudflare_zone_id"),
        opts=pulumi.ResourceOptions(parent=worker),
    )

pulumi_cloudflare.WorkerDomain(
    f"worker-domain-root",
    account_id=global_stack.get_output("cloudflare_account_id"),
    hostname=global_stack.get_output("domain"),
    service=name,
    zone_id=global_stack.get_output("cloudflare_zone_id"),
    opts=pulumi.ResourceOptions(parent=worker),
)

pulumi_cloudflare.WorkerDomain(
    f"worker-altdomain-root",
    account_id=global_stack.get_output("cloudflare_account_id"),
    hostname=config.require("alt-domain"),
    service=name,
    zone_id=config.require_secret("alt-cloudflare-zone-id"),
    opts=pulumi.ResourceOptions(parent=worker),
)

pulumi_cloudflare.WorkerDomain(
    f"worker-altdomain-www",
    account_id=global_stack.get_output("cloudflare_account_id"),
    hostname=f"www.{config.require('alt-domain')}",
    service=name,
    zone_id=config.require_secret("alt-cloudflare-zone-id"),
    opts=pulumi.ResourceOptions(parent=worker),
)
