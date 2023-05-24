import pulumi


def auto_tag(args, auto_tags):
    if args.type_.startswith("aws:") and "tags" in args.props:
        if args.props["tags"] is None:
            args.props["tags"] = {}
        args.props["tags"].update(auto_tags)

        if "Name" not in args.props["tags"]:
            args.props["tags"]["Name"] = args.name

        return pulumi.ResourceTransformationResult(args.props, args.opts)


def register(auto_tags):
    pulumi.runtime.register_stack_transformation(lambda args: auto_tag(args, auto_tags))
