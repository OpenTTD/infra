import pulumi


def auto_tag(args, auto_tags):
    if args.type_.startswith("aws:") and "tags" in args.props:
        args.props["tags"] = {**(args.props["tags"] or {}), **auto_tags}
        return pulumi.ResourceTransformationResult(args.props, args.opts)


def register(auto_tags):
    pulumi.runtime.register_stack_transformation(lambda args: auto_tag(args, auto_tags))
