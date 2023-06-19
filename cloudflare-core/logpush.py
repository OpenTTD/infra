import json
import hashlib
import pulumi
import pulumi_cloudflare

from dataclasses import dataclass


@dataclass
class LogPushArgs:
    cloudflare_account_id: str


class LogPush(pulumi.ComponentResource):
    def __init__(self, name, args: LogPushArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("openttd:cfw:LogPush", name, None, opts)

        r2 = pulumi_cloudflare.R2Bucket(
            "r2",
            account_id=args.cloudflare_account_id,
            location="WEUR",
            name="logs",
            opts=pulumi.ResourceOptions(protect=True, parent=self),
        )

        permission_groups = pulumi_cloudflare.get_api_token_permission_groups()
        resources = args.cloudflare_account_id.apply(
            lambda account_id: {f"com.cloudflare.api.account.{account_id}": "*"}
        )

        r2_token = pulumi_cloudflare.ApiToken(
            "r2-token",
            name="cloudflare-core/logpush",
            policies=[
                pulumi_cloudflare.ApiTokenPolicyArgs(
                    resources=resources,
                    permission_groups=[
                        permission_groups.account["Workers R2 Storage Write"],
                    ],
                ),
            ],
            opts=pulumi.ResourceOptions(parent=self),
        )

        secret_access_key = r2_token.value.apply(lambda secret: hashlib.sha256(secret.encode()).hexdigest())

        destination_conf = pulumi.Output.all(
            bucket_name=r2.name,
            account_id=args.cloudflare_account_id,
            access_key_id=r2_token.id,
            secret_access_key=secret_access_key,
        ).apply(
            lambda kwargs: f"r2://{kwargs['bucket_name']}?account-id={kwargs['account_id']}&access-key-id={kwargs['access_key_id']}&secret-access-key={kwargs['secret_access_key']}"
        )

        pulumi_cloudflare.LogpushJob(
            "logpush",
            account_id=args.cloudflare_account_id,
            dataset="workers_trace_events",
            destination_conf=destination_conf,
            enabled=True,
            filter=json.dumps(
                {
                    "where": {
                        "and": [
                            {
                                "key": "Outcome",
                                "operator": "!eq",
                                "value": "ok",
                            },
                            {
                                "key": "Outcome",
                                "operator": "!eq",
                                "value": "canceled",
                            },
                        ]
                    }
                },
                separators=(",", ":"),
            ),
            name="workers-logs",
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.register_outputs({})
