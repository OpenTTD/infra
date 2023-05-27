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

        async with command(
            f"https://{NOMAD_HOST}/{request.match_info['tail']}?{request.query_string}", data=data, headers=headers
        ) as proxy_response:
            response = web.StreamResponse()
            response.headers.update(proxy_response.headers)
            response.set_status(proxy_response.status)

            # We decompressed the response, so we need to remove the Content-Encoding / Content-Length header.
            if "Content-Encoding" in response.headers:
                del response.headers["Content-Encoding"]
            if "Content-Length" in response.headers:
                del response.headers["Content-Length"]

            await response.prepare(request)

            # Handle streaming data.
            while not proxy_response.content.is_eof():
                while not proxy_response.content._buffer and not proxy_response.content._eof:
                    await proxy_response.content._wait("read")
                await response.write(proxy_response.content.read_nowait(-1))

            # Read the remaining of the existing buffer.
            await response.write(proxy_response.content.read_nowait(-1))
            return response


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
