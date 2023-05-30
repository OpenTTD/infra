job "wiki-[[ stack ]]-deploy" {
  datacenters = ["dc1"]

  type = "batch"

  parameterized {
    meta_required = ["version"]
    payload = "forbidden"
  }

  group "deploy" {
    # Prevent more than one deployment running at the same time.
    count = 1

    # If deployment fails, it fails; don't retry.
    reschedule {
      attempts = 0
      unlimited = false
    }
    restart {
      attempts = 0
    }

    task "run" {
      driver = "exec"

      config {
        command = "local/deploy.py"
        args = [
          "wiki",
          "[[ stack ]]",
          "${NOMAD_META_version}",
        ]
      }

      template {
        destination = "local/deploy.py"
        perms = "755"
        left_delimiter = "@@"
        right_delimiter = "@@"

        data =<<EOT
#!/bin/env python3

import base64
import json
import shlex
import subprocess
import sys

if len(sys.argv) != 4:
    print(f"Usage: {sys.argv[0]} <job> <stack> <version>")
    sys.exit(1)

_, job, stack, version = sys.argv

# Retrieve the settings.
settings = json.loads(subprocess.run(
    shlex.split(f"nomad var get -out json app/{job}-{stack}/settings"),
    stdout=subprocess.PIPE,
    check=True,
).stdout)["Items"]

# Set the new version; double-escape the first @, as a @ has special meaning for "nomad var put".
if version.startswith("@"):
    safe_version = f"\\\\@{version[1:]}"
else:
    safe_version = version
subprocess.run(
    shlex.split(f"nomad var put -force app/{job}-{stack}/version version={safe_version}"),
    stdout=subprocess.PIPE,
    check=True,
)

# Read the jobspec.
jobspec = subprocess.run(
    shlex.split(f"nomad var get -out go-template -template '{{{{ .Items.jobspec }}}}' app/{job}-{stack}/jobspec"),
    stdout=subprocess.PIPE,
    check=True,
).stdout
jobspec = base64.b64decode(jobspec).decode()

# Replace all the variables.
for key, value in settings.items():
    jobspec = jobspec.replace(f"[[ {key} ]]", value)
jobspec = jobspec.replace("[[ version ]]", version)

# Write and execute it.
with open(f"local/{job}.nomad", "w") as fp:
    fp.write(jobspec)
subprocess.run(
    shlex.split(f"nomad job run local/{job}.nomad"),
    check=True,
)

print("New version deployed.")
EOT
      }

      resources {
        cpu = 100
        memory = 64
      }
    }
  }
}
