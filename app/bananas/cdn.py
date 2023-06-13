import pulumi
import pulumi_cloudflare

from dataclasses import dataclass


@dataclass
class CdnArgs:
    cloudflare_account_id: str
    cloudflare_zone_id: str
    domain: str
    hostname: str


class Cdn(pulumi.ComponentResource):
    def __init__(self, name, args: CdnArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("app:bananas:cdn", name, None, opts)

        r2 = pulumi_cloudflare.R2Bucket(
            "r2",
            account_id=args.cloudflare_account_id,
            location="WEUR",
            name=f"bananas-{pulumi.get_stack()}",
            opts=pulumi.ResourceOptions(protect=True),
        )

        self.bucket_name = r2.name
        self.bucket_endpoint_url = args.cloudflare_account_id.apply(lambda account_id: f"https://{account_id}.r2.cloudflarestorage.com")

        name = f"bananas-cdn-{pulumi.get_stack()}"
        worker = pulumi_cloudflare.WorkerScript(
            f"worker",
            account_id=args.cloudflare_account_id,
            content=open(f"files/cfw-cdn.js").read(),
            name=name,
            module=True,
            r2_bucket_bindings=[
                pulumi_cloudflare.WorkerScriptR2BucketBindingArgs(
                    name="BUCKET_CDN",
                    bucket_name=self.bucket_name,
                )
            ],
            opts=pulumi.ResourceOptions(parent=self),
        )

        pulumi_cloudflare.WorkerDomain(
            f"worker-domain",
            account_id=args.cloudflare_account_id,
            hostname=pulumi.Output.format("{}-cdn.{}", args.hostname, args.domain),
            service=name,
            zone_id=args.cloudflare_zone_id,
            opts=pulumi.ResourceOptions(parent=worker),
        )

        self.register_outputs({})
