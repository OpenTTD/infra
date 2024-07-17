const BACKENDS = ["nomad-aws-service", "nomad-oci-service"];

export default {
    async fetch(request) {
        const url = new URL(request.url);

        /* This endpoint normally only sees POSTs. */
        if (request.method !== "POST" && (request.method !== "GET" || url.pathname !== "/healthz")) {
            return new Response("Bad Request", {
                status: 400,
                statusText: "Bad Request",
                headers: {
                    "Content-Type": "text/plain",
                },
            });
        }
        /* On a GET request to /, check all backends. */
        if (request.method === "GET" && url.pathname === "/healthz") {
            let failed = [];

            for (const backend of BACKENDS) {
                url.hostname = `${backend}.openttd.org`;
                const response = await fetch(url.toString(), {
                    method: "GET",
                    headers: request.headers,
                });
                /* Avoid an error on the server, and read the full body. */
                await response.text();

                if (!response.ok) {
                    failed.push(backend);
                }
            }

            if (failed.length !== 0) {
                return new Response("Some backends failed: " + failed.join(", "), {
                    status: 500,
                    statusText: "Internal Server Error",
                    headers: {
                        "Content-Type": "text/plain",
                    },
                });
            }

            return new Response("OK", {
                status: 200,
                statusText: "OK",
                headers: {
                    "Content-Type": "text/plain",
                },
            });
        }

        let headers = new Headers(request.headers);
        let body = await request.text();

        let failed = [];
        let notfound = [];
        for (const backend of BACKENDS) {
            url.hostname = `${backend}.openttd.org`;
            const response = await fetch(url.toString(), {
                method: request.method,
                headers,
                body,
            });
            /* Avoid an error on the server, and read the full body. */
            await response.text();

            if (!response.ok) {
                if (response.status === 404) {
                    notfound.push(backend);
                } else {
                    failed.push(backend);
                }
            }
        }

        /* Tell the user if any backend returned an error (other than 404). */
        if (failed.length !== 0) {
            return new Response("Some backends failed: " + failed.join(", "), {
                status: 500,
                statusText: "Internal Server Error",
                headers: {
                    "Content-Type": "text/plain",
                },
            });
        }

        /* If no backend acknowledged the request, return that to the user. */
        if (notfound.length === BACKENDS.length) {
            return new Response("Not Found", {
                status: 404,
                statusText: "Not Found",
                headers: {
                    "Content-Type": "text/plain",
                },
            });
        }

        /* One of the backends acknowledge the request, so return an OK. */
        return new Response("OK", {
            status: 200,
            statusText: "OK",
            headers: {
                "Content-Type": "text/plain",
            },
        });
    },
};
