#!/bin/env python3

"""
Handles several endpoints related to deploying new software on the Nomad cluster.
"""

import aiohttp
import asyncio
import base64
import json
import logging
import shlex
import signal
import sys

from aiohttp import web
from aiohttp.web_log import AccessLogger

REMOTE_IP_HEADER = "cf-connecting-ip"
SERVICE_KEYS = {}
SERVICES = {}

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


@routes.post("/autoscaling/{service}/{key}")
async def autoscaling_handler(request):
    if "[[ target ]]" != "aws":
        return web.HTTPNotFound()

    service = request.match_info["service"]
    key = request.match_info["key"]
    payload = await request.json()

    if "x-amz-sns-topic-arn" in request.headers:
        type = payload["Type"]
        log.info(f"Receiving SNS notification: {type}")

        if service not in SERVICE_KEYS or SERVICE_KEYS[service]["key"] != key:
            log.error("Invalid service or service key")
            return web.HTTPOk()

        if type == "SubscriptionConfirmation":
            url = payload["SubscribeURL"]
            async with aiohttp.ClientSession() as session:
                await session.get(url)
            return web.HTTPOk()

        if type == "Notification":
            message = json.loads(payload["Message"])

            # We are only interested in autoscaling messages.
            if "LifecycleTransition" not in message:
                return web.HTTPOk()

            log.info(f"SNS notification is an autoscaling notification: {message['LifecycleTransition']}")

            if message["LifecycleTransition"] == "autoscaling:EC2_INSTANCE_TERMINATING":
                instance = message["EC2InstanceId"]

                async def execute(command):
                    command_args = shlex.split(command)

                    proc = await asyncio.create_subprocess_exec(
                        command_args[0],
                        *command_args[1:],
                        stdout=asyncio.subprocess.PIPE,
                    )

                    if await proc.wait() != 0:
                        log.error(f"Executing {command} failed.\n")
                        raise web.HTTPOk()

                    return (await proc.stdout.read()).decode().strip()

                # Get the Private IP DNS name of the instance.
                instance_name = await execute(
                    f"aws ec2 describe-instances --instance-ids {instance} --query 'Reservations[0].Instances[0].PrivateDnsName' --output text"
                )
                if not instance_name:
                    log.error(f"No instance name found for {instance}")
                    return web.HTTPOk()

                # Find the node ID of the instance.
                node_id = await execute(f"nomad node status -filter '\"{instance_name}\" in Name' -quiet")
                if not node_id:
                    log.error(f"No node ID found for {instance_name}")
                    return web.HTTPOk()

                log.info(f"Removing {instance} ({instance_name}) with node ID {node_id} from the cluster")

                # Make sure no new jobs are scheduled on the instance.
                await execute(f"nomad node eligibility -disable {node_id}")

                # Drain the instance (including system jobs).
                await execute(f"nomad node drain -yes -enable {node_id}")

                # Mark the node as ready for termination.
                await execute(
                    f"aws autoscaling complete-lifecycle-action --lifecycle-action-result CONTINUE --instance-id {instance} --lifecycle-hook-name {message['LifecycleHookName']} --auto-scaling-group-name {message['AutoScalingGroupName']}"
                )

        return web.HTTPOk()

    if service not in SERVICE_KEYS or SERVICE_KEYS[service]["key"] != key:
        return web.HTTPNotFound()
    if "instance" not in payload or "state" not in payload:
        return web.HTTPNotFound()
    if payload["state"] == "Continue" and "lifecycle-hook-name" not in payload:
        return web.HTTPNotFound()

    instance = payload["instance"]
    state = payload["state"]

    response = web.StreamResponse()
    response.headers["Content-Type"] = "text/event-stream"
    response.set_status(200)
    await response.prepare(request)

    async def reply(message):
        await response.write(message.encode())

    async def execute(command):
        command_args = shlex.split(command)

        proc = await asyncio.create_subprocess_exec(
            command_args[0],
            *command_args[1:],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            await reply(line.decode())

        if await proc.wait() != 0:
            await reply(f"ERROR: Executing {command} failed.\n")
            raise web.HTTPInternalServerError()

    log.info(f"Received {state} state for {instance} in {service}")

    if state == "Healthy":
        await execute(f"aws autoscaling set-instance-health --instance-id {instance} --health-status Healthy")

    if state == "Unhealthy":
        await execute(f"aws autoscaling set-instance-health --instance-id {instance} --health-status Unhealthy")

    if state == "Continue":
        lifecycle_hook_name = payload["lifecycle-hook-name"]
        await execute(
            f"aws autoscaling complete-lifecycle-action --lifecycle-action-result CONTINUE --instance-id {instance} --lifecycle-hook-name {lifecycle_hook_name} --auto-scaling-group-name {service}"
        )

    return response


@routes.post("/reload/{service}/{key}")
async def reload_handler(request):
    service = request.match_info["service"]
    key = request.match_info["key"]
    payload = await request.json()

    if service not in SERVICE_KEYS or SERVICE_KEYS[service]["key"] != key:
        return web.HTTPNotFound()
    if service not in SERVICES:
        return web.HTTPNotFound()
    if "secret" not in payload:
        return web.HTTPNotFound()

    secret = payload["secret"]

    response = web.StreamResponse()
    response.headers["Content-Type"] = "text/event-stream"
    response.set_status(200)
    await response.prepare(request)

    async with aiohttp.ClientSession() as session:
        for service in SERVICES[service]:
            if not service:
                continue

            url = f"http://[{service['address']}]:{service['port']}/reload"
            await response.write(f"Calling {url} ...\n".encode())
            reload_response = await session.post(url, json={"secret": secret})
            if reload_response.status >= 400:
                await response.write(f"  FAIL\n\n".encode())
            else:
                await response.write(f"  OK\n\n".encode())

    await response.write("All instances reloaded.\n".encode())
    return response


@routes.post("/deploy/{service}/{key}")
async def deploy_handler(request):
    service = request.match_info["service"]
    key = request.match_info["key"]
    payload = await request.json()

    if service not in SERVICE_KEYS or SERVICE_KEYS[service]["key"] != key:
        return web.HTTPNotFound()
    if "version" not in payload:
        return web.HTTPNotFound()

    version = payload["version"]

    response = web.StreamResponse()
    response.headers["Content-Type"] = "text/event-stream"
    response.set_status(200)
    await response.prepare(request)

    async def reply(message):
        await response.write(message.encode())

    async def execute(command, capture):
        command_args = shlex.split(command)

        if capture:
            proc = await asyncio.create_subprocess_exec(
                command_args[0],
                *command_args[1:],
                stdout=asyncio.subprocess.PIPE,
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                command_args[0],
                *command_args[1:],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                await reply(line.decode())

        if await proc.wait() != 0:
            await reply(f"ERROR: Executing {command} failed.\n")
            raise web.HTTPInternalServerError()

        if capture:
            return await proc.stdout.read()

    # Set the new version; double-escape the first @, as a @ has special meaning for "nomad var put".
    await reply(f"Setting new version to {version} ...\n")
    if version.startswith("@"):
        safe_version = f"\\\\@{version[1:]}"
    else:
        safe_version = version
    await execute(f"nomad var put -force app/{service}/version version={safe_version}", False)

    # Retrieve the settings.
    await reply(f"\nRetrieving settings for {service} ...\n")
    settings_raw = await execute(f"nomad var get -out json app/{service}/settings", True)
    settings = json.loads(settings_raw)["Items"]

    # Read the jobspec.
    await reply(f"\nRetrieving jobspec for {service} ...\n")
    jobspec = await execute(
        f"nomad var get -out go-template -template '{{{{ .Items.jobspec }}}}' app/{service}/jobspec", True
    )
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
    await execute(f"nomad job run local/{service}.nomad", False)

    await reply(f"\nDeployed {version} to {service}\n")
    return response


@routes.route("*", "/{tail:.*}")
async def fallback(request):
    return web.HTTPNotFound()


def handle_sighup(*args):
    log.info("Reloading files ...")
    global SERVICE_KEYS, SERVICES
    SERVICE_KEYS = json.loads(open("local/service-keys.json").read())
    SERVICES = json.loads(open("local/services.json").read())


def main():
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO
    )

    handle_sighup()
    signal.signal(signal.SIGHUP, handle_sighup)

    app = web.Application()
    app.middlewares.insert(0, remote_ip_header_middleware)

    app.add_routes(routes)

    web.run_app(app, port=int(sys.argv[1]), access_log_class=MyAccessLogger)


if __name__ == "__main__":
    main()
