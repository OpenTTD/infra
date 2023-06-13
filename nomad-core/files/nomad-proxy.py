#!/bin/env python3

"""
Nomad proxy to make sure the Content-Type is set correctly for streaming endpoints.
This is needed, as otherwise cloudflared buffers those calls, which is kinda
defeating the purpose of streaming endpoints.

This proxy listens on 8646, and forwards all requests to 127.0.0.1:4646.
"""

import aiohttp

from aiohttp import web

routes = web.RouteTableDef()

EVENT_STREAM_URLS = [
    "v1/event/stream",
    "v1/client/fs/logs/",
]


@routes.route("*", "/{tail:.*}")
async def proxy(request):
    headers = dict(request.headers)
    del headers["Host"]

    data = await request.text()

    async with aiohttp.ClientSession() as session:
        command = getattr(session, request.method.lower())

        async with command(
            f"http://127.0.0.1:4646/{request.match_info['tail']}?{request.query_string}", data=data, headers=headers
        ) as proxy_response:
            response = web.StreamResponse()
            response.headers.update(proxy_response.headers)
            response.set_status(proxy_response.status)

            # We decompressed the response, so we need to remove the Content-Encoding / Content-Length header.
            if "Content-Encoding" in response.headers:
                del response.headers["Content-Encoding"]
            if "Content-Length" in response.headers:
                del response.headers["Content-Length"]

            # Nomad returns application/json, even for streaming endpoints.
            # Cloudflared uses content-type to detect streaming endpoints,
            # and otherwise they buffer data. So we cheat here, and change
            # the content-type to something cloudflared recognizes.
            for url in EVENT_STREAM_URLS:
                if request.match_info["tail"].startswith(url):
                    response.headers["Content-Type"] = "text/event-stream"
            # If there is an index header, it's also a streaming endpoint.
            if "X-Nomad-Index" in proxy_response.headers:
                response.headers["Content-Type"] = "text/event-stream"

            try:
                await response.prepare(request)

                # Handle streaming data.
                while not proxy_response.content.is_eof():
                    while not proxy_response.content._buffer and not proxy_response.content._eof:
                        await proxy_response.content._wait("read")
                    await response.write(proxy_response.content.read_nowait(-1))

                # Read the remaining of the existing buffer.
                await response.write(proxy_response.content.read_nowait(-1))
            except ConnectionResetError:
                pass
            return response


def main():
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=8686)


if __name__ == "__main__":
    main()
