#!/bin/env python3

"""

"""

import base64
import json
import logging
import shlex
import signal
import subprocess
import sys

from aiohttp import web
from aiohttp.web_log import AccessLogger

REMOTE_IP_HEADER = "cf-connecting-ip"
SERVICE_KEYS = None

routes = web.RouteTableDef()
log = logging.getLogger(__name__)

class MyAccessLogger(AccessLogger):
    def log(self, request, response, time):
        # Don't log the health-check; it is spammy.
        if request.path == "/healthz":
            return

        if REMOTE_IP_HEADER in request.headers:
            request = request.clone(remote=request.headers[REMOTE_IP_HEADER])
        super().log(request, response, time)


@web.middleware
async def remote_ip_header_middleware(request, handler):
    if REMOTE_IP_HEADER in request.headers:
        request = request.clone(remote=request.headers[REMOTE_IP_HEADER])
    return await handler(request)


@routes.get("/healthz")
async def healthz_handler(request):
    return web.HTTPOk()


@routes.post("/deploy/{service}/{key}")
async def deploy_handler(request):
    service = request.match_info["service"]
    key = request.match_info["key"]
    payload = await request.json()
    version = payload["version"]

    if service not in SERVICE_KEYS or SERVICE_KEYS[service]['key'] != key:
        return web.HTTPNotFound()

    response = web.StreamResponse()
    response.headers["Content-Type"] = "text/event-stream"
    response.set_status(200)
    await response.prepare(request)

    async def reply(message):
        await response.write(message.encode())

    # Set the new version; double-escape the first @, as a @ has special meaning for "nomad var put".
    await reply(f"Setting new version to {version} ...\n")
    if version.startswith("@"):
        safe_version = f"\\\\@{version[1:]}"
    else:
        safe_version = version
    with subprocess.Popen(
        shlex.split(f"nomad var put -force app/{service}/version version={safe_version}"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ) as proc:
        for line in proc.stdout:
            await reply(line.decode())
        if proc.wait() != 0:
            await reply("ERROR: Setting new version failed.\n")
            raise web.HTTPInternalServerError()

    # Retrieve the settings.
    await reply(f"\nRetrieving settings for {service} ...\n")
    settings = json.loads(subprocess.run(
        shlex.split(f"nomad var get -out json app/{service}/settings"),
        stdout=subprocess.PIPE,
        check=True,
    ).stdout)["Items"]

    # Read the jobspec.
    await reply(f"\nRetrieving jobspec for {service} ...\n")
    jobspec = subprocess.run(
        shlex.split(f"nomad var get -out go-template -template '{{{{ .Items.jobspec }}}}' app/{service}/jobspec"),
        stdout=subprocess.PIPE,
        check=True,
    ).stdout
    jobspec = base64.b64decode(jobspec).decode()

    # Replace all the variables.
    await reply(f"\nCreating updated jobspec ...\n")
    for key, value in settings.items():
        jobspec = jobspec.replace(f"[[ {key} ]]", value)
    jobspec = jobspec.replace("[[ version ]]", version)

    # Write and execute it.
    await reply(f"\nUpdating job {service} with new jobspec ...\n")
    with open(f"local/{service}.nomad", "w") as fp:
        fp.write(jobspec)
    with subprocess.Popen(
        shlex.split(f"nomad job run local/{service}.nomad"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ) as proc:
        for line in proc.stdout:
            await reply(line.decode())
        if proc.wait() != 0:
            await reply("ERROR: Deploying new version failed.\n")
            raise web.HTTPInternalServerError()

    await reply(f"\nDeployed {version} to {service}\n")
    return response


@routes.route("*", "/{tail:.*}")
async def fallback(request):
    return web.HTTPNotFound()


def reload_services(*args):
    log.info("Reloading service keys")
    global SERVICE_KEYS
    SERVICE_KEYS = json.loads(open("local/service-keys.json").read())


def main():
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO
    )

    reload_services()
    signal.signal(signal.SIGHUP, reload_services)

    app = web.Application()
    app.middlewares.insert(0, remote_ip_header_middleware)

    app.add_routes(routes)

    web.run_app(app, port=int(sys.argv[1]), access_log_class=MyAccessLogger)


if __name__ == "__main__":
    main()
