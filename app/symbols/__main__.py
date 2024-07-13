import pulumi
import pulumi_cloudflare
import pulumi_github
import pulumi_tls
import pulumi_openttd


config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")

r2 = pulumi_cloudflare.R2Bucket(
    "r2",
    account_id=global_stack.get_output("cloudflare_account_id"),
    location="WEUR",
    name=f"symbols-{pulumi_openttd.get_stack()}",
    opts=pulumi.ResourceOptions(protect=True),
)

key_pairs = {}
public_keys = ""

# For every project that allows uploading, generate a private/public key pair,
# and assign that to GitHub secrets / Cloudflare Worker. This way, only the
# repository that should have upload access , can actually upload to it.
for repository in config.require_object("whitelist-projects"):
    # Generate an RSA key pair for each entry.
    key_pair = pulumi_tls.PrivateKey(f"key-pair-{repository.lower()}", algorithm="RSA", rsa_bits=2048)
    key_pairs[repository] = key_pair

    if pulumi_openttd.get_stack() == "prod":
        # Add the private key to GitHub secrets.
        pulumi_github.ActionsSecret(
            f"{repository.lower()}-github-secret-upload-key",
            repository=repository,
            secret_name="SYMBOLS_SIGNING_KEY",
            plaintext_value=key_pair.private_key_pem,
            opts=pulumi.ResourceOptions(parent=key_pair, delete_before_replace=True),
        )

    # Strip the header and footer from the public-key.
    public_key = key_pair.public_key_pem.apply(
        lambda key: key.replace("-----BEGIN PUBLIC KEY-----", "").replace("-----END PUBLIC KEY-----", "")
    )

    # Replace the public-key in the content blob.
    public_keys = pulumi.Output.all(public_keys=public_keys, repository=repository, public_key=public_key).apply(
        lambda kwargs: kwargs["public_keys"] + f'  "{kwargs["repository"]}": `{kwargs["public_key"]}`,\n'
    )

content = open("files/cfw-symbols.js").read()
content = pulumi.Output.all(content=content, public_keys=public_keys).apply(
    lambda kwargs: kwargs["content"].replace("[[ public_keys ]]", kwargs["public_keys"])
)

name = f"symbols-{pulumi_openttd.get_stack()}"
worker = pulumi_cloudflare.WorkerScript(
    "worker",
    account_id=global_stack.get_output("cloudflare_account_id"),
    content=content,
    logpush=True,
    name=name,
    module=True,
    r2_bucket_bindings=[
        pulumi_cloudflare.WorkerScriptR2BucketBindingArgs(
            name="BUCKET_SYMBOLS",
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
