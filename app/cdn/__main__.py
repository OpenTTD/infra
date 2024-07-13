import hashlib
import pulumi
import pulumi_cloudflare
import pulumi_github
import pulumi_openttd
import pulumi_tls


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")

r2 = pulumi_cloudflare.R2Bucket(
    "r2",
    account_id=global_stack.get_output("cloudflare_account_id"),
    location="WEUR",
    name=f"cdn-{pulumi_openttd.get_stack()}",
    opts=pulumi.ResourceOptions(protect=True),
)

key_pairs = {}
public_keys = ""

# For every folder that allows uploading, generate a private/public key pair,
# and assign that to GitHub secrets / Cloudflare Worker. This way, only the
# repository that should have upload access to a given folder, can actually
# upload to it.
for folder, repository in config.require_object("whitelist-upload-folders").items():
    key_pair = key_pairs.get(repository)

    if not key_pair:
        # Generate an RSA key pair for each entry.
        key_pair = pulumi_tls.PrivateKey(f"key-pair-{repository.lower()}", algorithm="RSA", rsa_bits=2048)
        key_pairs[repository] = key_pair

        if pulumi_openttd.get_stack() == "prod":
            # Add the private key to GitHub secrets.
            pulumi_github.ActionsSecret(
                f"{repository.lower()}-github-secret-upload-key",
                repository=repository,
                secret_name="CDN_SIGNING_KEY",
                plaintext_value=key_pair.private_key_pem,
                opts=pulumi.ResourceOptions(parent=key_pair, delete_before_replace=True),
            )

            # Add deployment app to GitHub secrets.
            pulumi_github.ActionsSecret(
                f"{repository.lower()}-github-secret-deployment-app-id",
                repository=repository,
                secret_name="DEPLOYMENT_APP_ID",
                plaintext_value=config.require("deployment-app-id"),
                opts=pulumi.ResourceOptions(delete_before_replace=True),
            )
            pulumi_github.ActionsSecret(
                f"{repository.lower()}-github-secret-deployment-app-private-key",
                repository=repository,
                secret_name="DEPLOYMENT_APP_PRIVATE_KEY",
                plaintext_value=config.require_secret("deployment-app-private-key"),
                opts=pulumi.ResourceOptions(delete_before_replace=True),
            )

    # Strip the header and footer from the public-key.
    public_key = key_pair.public_key_pem.apply(
        lambda key: key.replace("-----BEGIN PUBLIC KEY-----", "").replace("-----END PUBLIC KEY-----", "")
    )

    # Replace the public-key in the content blob.
    public_keys = pulumi.Output.all(public_keys=public_keys, folder=folder, public_key=public_key).apply(
        lambda kwargs: kwargs["public_keys"] + f'  "{kwargs["folder"]}": `{kwargs["public_key"]}`,\n'
    )

content = open("files/cfw-cdn.js").read()
content = pulumi.Output.all(content=content, public_keys=public_keys).apply(
    lambda kwargs: kwargs["content"].replace("[[ public_keys ]]", kwargs["public_keys"])
)

name = f"cdn-{pulumi_openttd.get_stack()}"
worker = pulumi_cloudflare.WorkerScript(
    "worker",
    account_id=global_stack.get_output("cloudflare_account_id"),
    content=content,
    logpush=True,
    name=name,
    module=True,
    r2_bucket_bindings=[
        pulumi_cloudflare.WorkerScriptR2BucketBindingArgs(
            name="BUCKET_CDN",
            bucket_name=r2.name,
        )
    ],
    opts=pulumi.ResourceOptions(depends_on=list(key_pairs.values())),
)

pulumi_cloudflare.WorkerDomain(
    "worker-domain",
    account_id=global_stack.get_output("cloudflare_account_id"),
    hostname=pulumi.Output.format("{}.{}", config.require("hostname"), global_stack.get_output("domain")),
    service=name,
    zone_id=global_stack.get_output("cloudflare_zone_id"),
    opts=pulumi.ResourceOptions(parent=worker),
)

if pulumi_openttd.get_stack() == "prod":
    permission_groups = pulumi_cloudflare.get_api_token_permission_groups()
    resources = pulumi.Output.all(account_id=global_stack.get_output("cloudflare_account_id"), s3_bucket=r2.name).apply(
        lambda kwargs: {f"com.cloudflare.edge.r2.bucket.{kwargs['account_id']}_default_{kwargs['s3_bucket']}": "*"}
    )

    # Create Write token to give CDN generator in workflows repository full access to the bucket.
    api_token = pulumi_cloudflare.ApiToken(
        "cdn-api-token",
        name="app/cdn",
        policies=[
            pulumi_cloudflare.ApiTokenPolicyArgs(
                resources=resources,
                permission_groups=[
                    permission_groups.permissions["Workers R2 Storage Bucket Item Write"],
                ],
            ),
        ],
        opts=pulumi.ResourceOptions(parent=r2, protect=False),
    )

    pulumi_github.ActionsSecret(
        "workflows-github-secret-r2-endpoint",
        repository=config.require("workflows-repository"),
        secret_name="CDN_R2_ENDPOINT",
        plaintext_value=global_stack.get_output("cloudflare_account_id").apply(
            lambda account_id: f"https://{account_id}.r2.cloudflarestorage.com"
        ),
        opts=pulumi.ResourceOptions(parent=r2, delete_before_replace=True, protect=False),
    )

    pulumi_github.ActionsSecret(
        "workflows-github-secret-r2-bucket",
        repository=config.require("workflows-repository"),
        secret_name="CDN_R2_BUCKET",
        plaintext_value=r2.name,
        opts=pulumi.ResourceOptions(parent=r2, delete_before_replace=True, protect=False),
    )

    pulumi_github.ActionsSecret(
        "workflows-github-secret-r2-region",
        repository=config.require("workflows-repository"),
        secret_name="CDN_R2_REGION",
        plaintext_value=r2.location,
        opts=pulumi.ResourceOptions(parent=r2, delete_before_replace=True, protect=False),
    )

    pulumi_github.ActionsSecret(
        "workflows-github-secret-r2-access-id",
        repository=config.require("workflows-repository"),
        secret_name="CDN_R2_ACCESS_KEY_ID",
        plaintext_value=api_token.id,
        opts=pulumi.ResourceOptions(parent=api_token, delete_before_replace=True),
    )

    pulumi_github.ActionsSecret(
        "workflows-github-secret-r2-access-key",
        repository=config.require("workflows-repository"),
        secret_name="CDN_R2_SECRET_ACCESS_KEY",
        plaintext_value=api_token.value.apply(lambda secret: hashlib.sha256(secret.encode()).hexdigest()),
        opts=pulumi.ResourceOptions(parent=api_token, delete_before_replace=True),
    )

    # Also give the workflow repository access to the deployment app.
    pulumi_github.ActionsSecret(
        "workflows-github-secret-deployment-app-id",
        repository=config.require("workflows-repository"),
        secret_name="DEPLOYMENT_APP_ID",
        plaintext_value=config.require("deployment-app-id"),
        opts=pulumi.ResourceOptions(delete_before_replace=True),
    )
    pulumi_github.ActionsSecret(
        "workflows-github-secret-deployment-app-private-key",
        repository=config.require("workflows-repository"),
        secret_name="DEPLOYMENT_APP_PRIVATE_KEY",
        plaintext_value=config.require_secret("deployment-app-private-key"),
        opts=pulumi.ResourceOptions(delete_before_replace=True),
    )
