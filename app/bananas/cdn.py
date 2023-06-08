import pulumi
import pulumi_cloudflare
import pulumi_random
import pulumi_openttd

from dataclasses import dataclass


@dataclass
class CdnArgs:
    cloudflare_account_id: str


class Cdn(pulumi.ComponentResource):
    def __init__(self, name, args: CdnArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("app:bananas:cdn", name, None, opts)

        # r2 = pulumi_cloudflare.R2Bucket(
        #     "r2",
        #     account_id=args.cloudflare_account_id,
        #     location="weur",
        #     name=f"bananas-{pulumi.get_stack()}",
        # )

        self.bucket_name = f"bananas-{pulumi.get_stack()}"
        self.bucket_endpoint_url = "https://656eb7bf45569b729d05c1da49dfde7c.r2.cloudflarestorage.com"

        self.register_outputs({})
