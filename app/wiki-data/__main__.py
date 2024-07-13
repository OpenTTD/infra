import pulumi
import pulumi_github
import pulumi_openttd


config = pulumi.Config()
app_wiki_stack = pulumi.StackReference(f"{pulumi.get_organization()}/app-wiki/{pulumi_openttd.get_stack()}")


pulumi_openttd.autotag.register()


pulumi_github.ActionsSecret(
    f"github-secret-reload-secret",
    repository=config.require("storage-github-url").split("/")[-1],
    secret_name=f"RELOAD_SECRET",
    plaintext_value=app_wiki_stack.get_output("reload_secret"),
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)
pulumi_github.ActionsSecret(
    f"github-secret-nomad-service-key",
    repository=config.require("storage-github-url").split("/")[-1],
    secret_name=f"NOMAD_SERVICE_{pulumi_openttd.get_stack().upper()}_KEY",
    plaintext_value=app_wiki_stack.get_output("nomad_service_key"),
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)
