import base64
import pulumi
import pulumi_github
import pulumi_nomad
import pulumi_openttd
import pulumi_random

from dataclasses import dataclass


@dataclass
class NomadServiceArgs:
    service: str
    settings: dict[str, str]
    dependencies: list[pulumi.Resource]
    repository: str
    prefix: str = ""


class NomadService(pulumi.ComponentResource):
    """
    Create a nomad service with everything related to it.
    """

    def __init__(self, name, args: NomadServiceArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("openttd:nomad:Service", name, None, opts)

        variables = {}
        for key, value in args.settings.items():
            variables[key] = pulumi_openttd.NomadVariable(
                f"{args.prefix}setting-{key}",
                pulumi_openttd.NomadVariableArgs(
                    path=f"app/{args.service}-{pulumi_openttd.get_stack()}/settings",
                    name=key,
                    value=value,
                    overwrite_if_exists=True,
                ),
                opts=pulumi.ResourceOptions(parent=self),
            )

        variables["version"] = pulumi_openttd.NomadVariable(
            f"{args.prefix}version",
            pulumi_openttd.NomadVariableArgs(
                path=f"app/{args.service}-{pulumi_openttd.get_stack()}/version",
                name="version",
                value=":edge",  # Just the initial value.
                overwrite_if_exists=False,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        jobspec = open(f"files/{args.service}.nomad", "rb").read()
        pulumi_openttd.NomadVariable(
            f"{args.prefix}jobspec",
            pulumi_openttd.NomadVariableArgs(
                path=f"app/{args.service}-{pulumi_openttd.get_stack()}/jobspec",
                name="jobspec",
                value=base64.b64encode(jobspec).decode(),
                overwrite_if_exists=True,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        pulumi_nomad.Job(
            f"{args.prefix}job",
            jobspec=pulumi_openttd.get_jobspec(jobspec.decode(), variables),
            purge_on_destroy=True,
            opts=pulumi.ResourceOptions(parent=self, depends_on=[*args.dependencies, *variables.values()]),
        )

        self.nomad_service_key = pulumi_random.RandomPassword(
            f"{args.prefix}nomad-service-key",
            length=32,
            special=False,
        )
        pulumi_openttd.NomadVariable(
            f"{args.prefix}variable-nomad-service-key",
            pulumi_openttd.NomadVariableArgs(
                path=f"deploy-keys/{args.service}-{pulumi_openttd.get_stack()}",
                name="key",
                value=self.nomad_service_key.result,
                overwrite_if_exists=True,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )
        pulumi_github.ActionsSecret(
            f"{args.prefix}github-secret-nomad-service-key",
            repository=args.repository,
            secret_name=f"NOMAD_SERVICE_{pulumi_openttd.get_stack().upper()}_KEY",
            plaintext_value=self.nomad_service_key.result,
            opts=pulumi.ResourceOptions(parent=self, delete_before_replace=True),
        )

        self.register_outputs({})
