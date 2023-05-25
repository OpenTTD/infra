import pulumi


def auto_tag(args, auto_tags):
    if args.type_.startswith("aws:") and "tags" in args.props:
        if args.props["tags"] is None:
            args.props["tags"] = {}
        args.props["tags"].update(auto_tags)

        # Always set the Name tag to the resource name.
        # This avoids a lot of "tags" in all resources, as often in the
        # resource the name is already set to the resource itself.
        if "Name" not in args.props["tags"]:
            args.props["tags"]["Name"] = args.name

        return pulumi.ResourceTransformationResult(args.props, args.opts)


def register(auto_tags=None):
    if auto_tags is None:
        auto_tags = {}

    # Make life a bit easier, and make sure we can see when resources are
    # created by Pulumi.
    auto_tags["Managed-By"] = "Pulumi"

    pulumi.runtime.register_stack_transformation(lambda args: auto_tag(args, auto_tags))
