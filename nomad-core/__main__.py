import pulumi
import pulumi_nomad
import pulumi_openttd

config = pulumi.Config()
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
job = pulumi_nomad.Job(
    "cloudflared",
    jobspec=open("files/cloudflared.nomad").read(),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
    opts=pulumi.ResourceOptions(depends_on=[cloudflare_tunnel]),
)

job = pulumi_nomad.Job(
    "csi-efs",
    jobspec=open("files/csi-efs.nomad").read(),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)

job = pulumi_nomad.Job(
    "nginx-dc1",
    jobspec=open("files/nginx-dc1.nomad").read(),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)

job = pulumi_nomad.Job(
    "nginx-public",
    jobspec=open("files/nginx-public.nomad").read(),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)

job = pulumi_nomad.Job(
    "pproxy",
    jobspec=open("files/pproxy.nomad").read(),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)

content = open("files/nomad-service.py").read()
job = pulumi_nomad.Job(
    "nomad-service",
    jobspec=open("files/nomad-service.nomad").read().replace("[[ content ]]", content),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)

content = open("files/nomad-proxy.py").read()
job = pulumi_nomad.Job(
    "nomad-proxy",
    jobspec=open("files/nomad-proxy.nomad").read().replace("[[ content ]]", content),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)
