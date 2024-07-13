import pulumi


def get_stack():
    """
    Get the prod/preview part of the stack-name.

    Some stacks are called just prod or preview, but others are called like
    prod-aws or prod-oci. In these cases we only want to know prod too.
    """
    stack = pulumi.get_stack()
    return stack.split("-")[0]
