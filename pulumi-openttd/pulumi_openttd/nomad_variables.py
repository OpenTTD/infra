import json
import pulumi
import shlex
import subprocess

from dataclasses import dataclass

# Dict of last variable created per path; used for ordering.
_last_variable = {}


@dataclass
class NomadVariableArgs:
    path: str
    name: str
    value: str = ""
    overwrite_if_exists: bool = True


def local_run(command, stdin=None, check=True):
    return subprocess.run(
        shlex.split(command),
        input=stdin.encode() if stdin else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    ).stdout


class NomadVariableProvider(pulumi.dynamic.ResourceProvider):
    def _get_current_vars(self, path):
        vars = local_run(f"nomad var get -out json {path}", check=False)

        if vars:
            return json.loads(vars)
        else:
            return {
                "Namespace": "default",
                "Path": path,
                "ModifyIndex": 0,
                "Items": {},
            }

    def read(self, id, args):
        current_vars = self._get_current_vars(args["path"])

        if args["name"] not in current_vars["Items"]:
            args["value"] = ""
        else:
            args["value"] = current_vars["Items"][args["name"]]

        return pulumi.dynamic.ReadResult(id, args)

    def create(self, args):
        current_vars = self._get_current_vars(args["path"])

        if args["overwrite_if_exists"] or args["name"] not in current_vars["Items"]:
            current_vars["Items"][args["name"]] = args["value"]

        local_run("nomad var put -in json -", stdin=json.dumps(current_vars))

        return pulumi.dynamic.CreateResult(f"variable-{args['path']}-{args['name']}", args)

    def update(self, id, old_args, args):
        current_vars = self._get_current_vars(args["path"])

        if args["overwrite_if_exists"] or args["name"] not in current_vars["Items"]:
            current_vars["Items"][args["name"]] = args["value"]

        local_run("nomad var put -in json -", stdin=json.dumps(current_vars))

        return pulumi.dynamic.UpdateResult(args)

    def delete(self, id, args):
        current_vars = self._get_current_vars(args["path"])

        # Happens when Pulumi and the actual source is out-of-sync; ignore it silently, as clearly the entry is gone.
        if not current_vars["Items"]:
            return

        if args["name"] in current_vars["Items"]:
            del current_vars["Items"][args["name"]]

        if current_vars["Items"]:
            local_run("nomad var put -in json -", stdin=json.dumps(current_vars))
        else:
            local_run(f"nomad var purge -check-index {current_vars['ModifyIndex']} {args['path']}")

    def diff(self, id, old_args, args):
        changes = False
        replaces = []

        if old_args["value"] != args["value"] and args["overwrite_if_exists"]:
            changes = True

        # Don't attempt to update change of name/path cleanly, and just delete and recreate.
        if old_args["name"] != args["name"] or old_args["path"] != args["path"]:
            replaces.append("name")
            changes = True

        return pulumi.dynamic.DiffResult(changes=changes, replaces=replaces, delete_before_replace=True)


class NomadVariable(pulumi.dynamic.Resource, module="nomad", name="NomadVariable"):
    """
    Manage a Nomad variable.

    This resource handles the creation, update and deletion of a Nomad variable.

    Note: although with the Nomad CLI and API you need to change all variables
    for a given path, there is no need for that with this resource. This resource
    will only change the variable you specify, and leave the rest alone.

    Note: because of the above, it is important that only one variable at the
    time is manipulated. As such, internally variables are ordered per path, and
    the last variable created is used as a dependency for the next variable.
    This means that creating a lot of variables for a single path will be rather
    slow, as they are handled one by one.
    """

    def __init__(self, name: str, args: NomadVariableArgs, opts: pulumi.ResourceOptions = None):
        # Ensure only one variable is manipulated per path at the time.
        if args.path in _last_variable:
            if opts:
                opts.depends_on = (opts.depends_on or []) + [_last_variable[args.path]]
            else:
                opts = pulumi.ResourceOptions(depends_on=[_last_variable[args.path]])
        _last_variable[args.path] = self

        super().__init__(NomadVariableProvider(), name, vars(args), opts)
