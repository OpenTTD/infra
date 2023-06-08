import base64
import pulumi
import pulumi_github
import pulumi_nomad
import pulumi_openttd
import os

from dataclasses import dataclass


@dataclass
class NomadServiceArgs:
    service: str
    settings: dict[str, str]
    dependencies: list[pulumi.Resource]
    service_token_id: str
    service_token_secret: str
    repository: str


class NomadService(pulumi.ComponentResource):
    """
    Create a nomad service with everything related to it.
    """

    def __init__(self, name, args: NomadServiceArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("openttd:nomad:Service", name, None, opts)

        variables = {}
        for key, value in args.settings.items():
            variables[key] = pulumi_openttd.NomadVariable(
                f"setting-{key}",
                pulumi_openttd.NomadVariableArgs(
                    path=f"app/{args.service}-{pulumi.get_stack()}/settings",
                    name=key,
                    value=value,
                    overwrite_if_exists=True,
                ),
                opts=pulumi.ResourceOptions(parent=self),
            )

        variables["version"] = pulumi_openttd.NomadVariable(
            "version",
            pulumi_openttd.NomadVariableArgs(
                path=f"app/{args.service}-{pulumi.get_stack()}/version",
                name="version",
                value=":edge",  # Just the initial value.
                overwrite_if_exists=False,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        jobspec = open(f"files/{args.service}.nomad", "rb").read()
        pulumi_openttd.NomadVariable(
            f"jobspec",
            pulumi_openttd.NomadVariableArgs(
                path=f"app/{args.service}-{pulumi.get_stack()}/jobspec",
                name="jobspec",
                value=base64.b64encode(jobspec).decode(),
                overwrite_if_exists=True,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        pulumi_nomad.Job(
            "job",
            jobspec=pulumi_openttd.get_jobspec(jobspec.decode(), variables),
            hcl2=pulumi_nomad.JobHcl2Args(
                enabled=True,
            ),
            purge_on_destroy=True,
            opts=pulumi.ResourceOptions(parent=self, depends_on=[*args.dependencies, *variables.values()]),
        )

        files_folder = os.path.join(os.path.dirname(__file__), "..", "files")
        jobspec_deploy = open(f"{files_folder}/deploy.nomad", "rb").read().decode()
        jobspec_deploy = jobspec_deploy.replace("[[ stack ]]", pulumi.get_stack()).replace(
            "[[ service ]]", args.service
        )

        pulumi_nomad.Job(
            "job-deploy",
            jobspec=jobspec_deploy,
            hcl2=pulumi_nomad.JobHcl2Args(
                enabled=True,
            ),
            purge_on_destroy=True,
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Only one of the stacks need to deploy the secrets, as they go to the same repository.
        if pulumi.get_stack() == "prod":
            pulumi_github.ActionsSecret(
                "github-secret-nomad-cloudflare-access-id",
                repository=args.repository,
                secret_name="NOMAD_CF_ACCESS_CLIENT_ID",
                plaintext_value=args.service_token_id,
                opts=pulumi.ResourceOptions(parent=self),
            )

            pulumi_github.ActionsSecret(
                "github-secret-nomad-cloudflare-access-secret",
                repository=args.repository,
                secret_name="NOMAD_CF_ACCESS_CLIENT_SECRET",
                plaintext_value=args.service_token_secret,
                opts=pulumi.ResourceOptions(parent=self),
            )

        self.register_outputs({})
