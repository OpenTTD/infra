import pulumi
import pulumi_aws
import pulumi_nomad

from dataclasses import dataclass


@dataclass
class VolumeEfsArgs:
    name: str
    subnet_ids: list[str]


class VolumeEfs(pulumi.ComponentResource):
    """
    Create an AWS EFS volume and a Nomad volume to use it.
    """

    def __init__(self, name, args: VolumeEfsArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("openttd:volume:Efs", name, None, opts)

        self.efs = pulumi_aws.efs.FileSystem(
            name,
            tags={
                "Name": args.name,
            },
        )
        args.subnet_ids.apply(lambda subnet_ids: self._mount_target(name, self.efs, subnet_ids))

        self.volume = pulumi_nomad.Volume(
            name,
            capabilities=[
                pulumi_nomad.VolumeCapabilityArgs(
                    access_mode="multi-node-multi-writer",
                    attachment_mode="file-system",
                ),
            ],
            external_id=self.efs.id,
            name=args.name,
            plugin_id="aws-efs0",
            type="csi",
            volume_id=args.name,
            opts=pulumi.ResourceOptions(
                parent=self.efs,
                delete_before_replace=True,
                replace_on_changes=["*"],
            ),
        )

        self.register_outputs(
            {
                "efs_id": self.efs.id,
            }
        )

    def _mount_target(self, name, efs, subnet_ids):
        for subnet_id in subnet_ids:
            pulumi_aws.efs.MountTarget(
                f"{name}-mount-{subnet_id}",
                file_system_id=efs.id,
                subnet_id=subnet_id,
                opts=pulumi.ResourceOptions(parent=efs),
            )
