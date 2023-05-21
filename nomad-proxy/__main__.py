import aiohttp
import os
import sys

from aiohttp import web

routes = web.RouteTableDef()

NOMAD_HOST = None


@routes.route("*", "/{tail:.*}")
async def proxy(request):
    headers = dict(request.headers)
    del headers["Host"]
    headers["CF-Access-Client-Id"] = os.getenv("CF_ACCESS_CLIENT_ID")
    headers["CF-Access-Client-Secret"] = os.getenv("CF_ACCESS_CLIENT_SECRET")

    data = await request.text()

    async with aiohttp.ClientSession() as session:
        command = getattr(session, request.method.lower())

        async with command(f"https://{NOMAD_HOST}/{request.match_info['tail']}?{request.query_string}", data=data, headers=headers) as resp:
            return web.Response(text=await resp.text(), status=resp.status)


def main():
    global NOMAD_HOST

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <nomad-host>")
        sys.exit(1)

    if not os.getenv("CF_ACCESS_CLIENT_ID") or not os.getenv("CF_ACCESS_CLIENT_SECRET"):
        print("CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET environment variables need to be set.")
        sys.exit(1)

    NOMAD_HOST = sys.argv[1]

    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=4646)


if __name__ == "__main__":
    main()
