import json
import pulumi
import pulumi_command
import pulumi_nomad
import shlex
import subprocess

from dataclasses import dataclass

# Dict of last variable created per job; used for ordering.
_last_variable = {}


@dataclass
class VariableArgs:
    job: str
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


class VariableProvider(pulumi.dynamic.ResourceProvider):
    def _get_current_vars(self, job):
        vars = local_run(f"nomad var get -out json nomad/jobs/{job}", check=False)

        if vars:
            return json.loads(vars)
        else:
            return {
                "Namespace": "default",
                "Path": f"nomad/jobs/{job}",
                "ModifyIndex": 0,
                "Items": {},
            }

    def create(self, args):
        current_vars = self._get_current_vars(args["job"])

        if args["overwrite_if_exists"] or args["name"] not in current_vars["Items"]:
            current_vars["Items"][args["name"]] = args["value"]

        local_run(f"nomad var put -in json -", stdin=json.dumps(current_vars))

        return pulumi.dynamic.CreateResult(f"variable-{args['job']}-{args['name']}", args)

    def update(self, id, old_args, args):
        current_vars = self._get_current_vars(args["job"])

        if args["overwrite_if_exists"] or args["name"] not in current_vars["Items"]:
            current_vars["Items"][args["name"]] = args["value"]

        local_run(f"nomad var put -in json -", stdin=json.dumps(current_vars))

        return pulumi.dynamic.UpdateResult(args)

    def delete(self, id, args):
        current_vars = self._get_current_vars(args["job"])

        # Happens when Pulumi and the actual source is out-of-sync; ignore it silently, as clearly the entry is gone.
        if not current_vars["Items"]:
            return

        if args["name"] in current_vars["Items"]:
            del current_vars["Items"][args["name"]]

        if current_vars["Items"]:
            local_run(f"nomad var put -in json -", stdin=json.dumps(current_vars))
        else:
            local_run(f"nomad var purge -check-index {current_vars['ModifyIndex']} nomad/jobs/{args['job']}")

    def diff(self, id, old_args, args):
        changes = False
        replaces = []

        if old_args["value"] != args["value"] and args["overwrite_if_exists"]:
            changes = True

        # Don't attempt to update change of name/job cleanly, and just delete and recreate.
        if old_args["name"] != args["name"] or old_args["job"] != args["job"]:
            replaces.append("name")
            changes = True

        return pulumi.dynamic.DiffResult(changes=changes, replaces=replaces, delete_before_replace=True)


class Variable(pulumi.dynamic.Resource, module="nomad", name="Variable"):
    def __init__(self, name: str, args: VariableArgs, opts: pulumi.ResourceOptions = None):
        # Ensure only one variable is manipulated per job at the time.
        if args.job in _last_variable:
            if opts:
                opts.depends_on = (opts.depends_on or []) + [_last_variable[args.job]]
            else:
                opts = pulumi.ResourceOptions(depends_on=[_last_variable[args.job]])
        _last_variable[args.job] = self

        super().__init__(VariableProvider(), name, vars(args), opts)
