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
    "nginx",
    jobspec=open("files/nginx.nomad").read(),
    hcl2=pulumi_nomad.JobHcl2Args(
        enabled=True,
    ),
    purge_on_destroy=True,
)
