import pulumi
import pulumi_aws
import pulumi_nomad

from dataclasses import dataclass


@dataclass
class VolumeEfsArgs:
    name: str
    subnet_arns: list[str]
    subnet_ids: list[str]
    security_group_arn: str
    security_group_id: str
    s3_datasync_arn: str
    s3_datasync_iam_arn: str


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
        args.subnet_ids.apply(lambda subnet_ids: self._mount_target(name, self.efs, subnet_ids, args.security_group_id))

        s3_datasync_location = pulumi_aws.datasync.S3Location(
            f"{name}-datasync-s3",
            s3_bucket_arn=args.s3_datasync_arn,
            subdirectory=f"/{args.name}",
            s3_config=pulumi_aws.datasync.S3LocationS3ConfigArgs(
                bucket_access_role_arn=args.s3_datasync_iam_arn,
            ),
            opts=pulumi.ResourceOptions(parent=self.efs),
            tags={
                "Name": f"{args.name}-s3",
            },
        )
        datasync_location = pulumi_aws.datasync.EfsLocation(
            f"{name}-datasync-efs",
            ec2_config=pulumi_aws.datasync.EfsLocationEc2ConfigArgs(
                security_group_arns=[args.security_group_arn],
                subnet_arn=args.subnet_arns.apply(lambda subnet_arns: subnet_arns[0]),
            ),
            efs_file_system_arn=self.efs.arn,
            opts=pulumi.ResourceOptions(parent=self.efs),
            tags={
                "Name": f"{args.name}-efs",
            },
        )
        pulumi_aws.datasync.Task(
            f"{name}-datasync-task",
            destination_location_arn=s3_datasync_location.arn,
            name=args.name,
            schedule=pulumi_aws.datasync.TaskScheduleArgs(
                schedule_expression="cron(0 3 ? * SAT *)",
            ),
            source_location_arn=datasync_location.arn,
            opts=pulumi.ResourceOptions(parent=self.efs),
            tags={
                "Name": args.name,
            },
        )

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

    def _mount_target(self, name, efs, subnet_ids, security_group_id):
        for subnet_id in subnet_ids:
            pulumi_aws.efs.MountTarget(
                f"{name}-mount-{subnet_id}",
                file_system_id=efs.id,
                subnet_id=subnet_id,
                security_groups=[security_group_id],
                opts=pulumi.ResourceOptions(parent=efs),
            )
