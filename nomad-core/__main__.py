import pulumi
import pulumi_nomad

config = pulumi.Config()


job = pulumi_nomad.Job(
    "cloudflared",
    jobspec=open("files/cloudflared.nomad").read(),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
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
