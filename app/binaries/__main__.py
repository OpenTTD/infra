import pulumi
import pulumi_cloudflare


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")

# r2 = pulumi_cloudflare.R2Bucket(
#     "r2",
#     account_id=args.cloudflare_account_id,
#     location="weur",
#     name=f"installer-{pulumi.get_stack()}",
# )

bucket_name = f"installer-{pulumi.get_stack()}"

name = f"binaries-{pulumi.get_stack()}"
worker = pulumi_cloudflare.WorkerScript(
    f"worker",
    account_id=global_stack.get_output("cloudflare_account_id"),
    content=global_stack.get_output("domain").apply(
        lambda domain: open(f"files/cfw-binaries.js")
        .read()
        .replace("[[ hostname ]]", config.require("bananas_hostname"))
        .replace("[[ domain ]]", domain)
    ),
    name=name,
    module=True,
    r2_bucket_bindings=[
        pulumi_cloudflare.WorkerScriptR2BucketBindingArgs(
            name="BUCKET_INSTALLER",
            bucket_name=bucket_name,
        )
    ],
)

pulumi_cloudflare.WorkerDomain(
    f"worker-domain",
    account_id=global_stack.get_output("cloudflare_account_id"),
    hostname=pulumi.Output.format("{}.{}", config.require("hostname"), global_stack.get_output("domain")),
    service=name,
    zone_id=global_stack.get_output("cloudflare_zone_id"),
    opts=pulumi.ResourceOptions(parent=worker),
)
