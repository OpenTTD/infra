import pulumi
import pulumi_cloudflare
import pulumi_nomad
import pulumi_openttd

config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")
cloudflare_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/cloudflare-core/prod")

cloudflare_tunnel = pulumi_openttd.NomadVariable(
    "variable-cloudflare-tunnel",
    pulumi_openttd.NomadVariableArgs(
        path="nomad/jobs/cloudflared",
        name="tunnel_token",
        value=cloudflare_core_stack.get_output("tunnel_token"),
        overwrite_if_exists=True,
    ),
)
pulumi_nomad.Job(
    "cloudflared",
    jobspec=open("files/cloudflared.nomad").read(),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
    opts=pulumi.ResourceOptions(depends_on=[cloudflare_tunnel]),
)

pulumi_nomad.Job(
    "csi-efs",
    jobspec=open("files/csi-efs.nomad").read(),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)

pulumi_nomad.Job(
    "nginx-dc1",
    jobspec=open("files/nginx-dc1.nomad").read(),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)

pulumi_nomad.Job(
    "nginx-public",
    jobspec=open("files/nginx-public.nomad").read(),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)

pulumi_nomad.Job(
    "pproxy",
    jobspec=open("files/pproxy.nomad").read(),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)

content = pulumi.Output.all(
    grafana_cloud_password=config.require_secret("grafana-cloud-password"),
    grafana_cloud_url=config.require_secret("grafana-cloud-url"),
    grafana_cloud_username=config.require_secret("grafana-cloud-username"),
).apply(
    lambda kwargs: open("files/prometheus.nomad")
    .read()
    .replace("[[ grafana_cloud_password ]]", kwargs["grafana_cloud_password"])
    .replace("[[ grafana_cloud_url ]]", kwargs["grafana_cloud_url"])
    .replace("[[ grafana_cloud_username ]]", kwargs["grafana_cloud_username"])
)
pulumi_nomad.Job(
    "prometheus",
    jobspec=content,
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)

# This is purely to visualise the system consumes memory.
pulumi_nomad.Job(
    "system",
    jobspec=open("files/system.nomad").read(),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)

permission_groups = pulumi_cloudflare.get_api_token_permission_groups()
resources = global_stack.get_output("cloudflare_zone_id").apply(
    lambda zone_id: {f"com.cloudflare.api.account.zone.{zone_id}": "*"}
)
nomad_service_api_token = pulumi_cloudflare.ApiToken(
    "nomad-service-api-token",
    name="nomad-core/service",
    policies=[
        pulumi_cloudflare.ApiTokenPolicyArgs(
            resources=resources,
            permission_groups=[
                permission_groups.zone["DNS Write"],
            ],
        ),
    ],
)

content = pulumi.Output.all(
    api_token=nomad_service_api_token.value, zone_id=global_stack.get_output("cloudflare_zone_id")
).apply(
    lambda kwargs: open("files/nlb-dns-update.py")
    .read()
    .replace("[[ cloudflare_zone_id ]]", kwargs["zone_id"])
    .replace("[[ cloudflare_api_token ]]", kwargs["api_token"])
)
pulumi_nomad.Job(
    "nlb-dns-update",
    jobspec=content.apply(lambda content: open("files/nlb-dns-update.nomad").read().replace("[[ content ]]", content)),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)

content = open("files/nomad-service.py").read()
pulumi_nomad.Job(
    "nomad-service",
    jobspec=open("files/nomad-service.nomad").read().replace("[[ content ]]", content),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)

content = open("files/nomad-proxy.py").read()
pulumi_nomad.Job(
    "nomad-proxy",
    jobspec=open("files/nomad-proxy.nomad").read().replace("[[ content ]]", content),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)
