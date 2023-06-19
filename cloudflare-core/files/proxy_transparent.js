export default {
    async fetch(request) {
        const url = new URL(request.url);

        let headers = new Headers(request.headers);
        let body = request.body;

        /* Some tools, like GidGetHub, send a Content-Length header and an empty
         * body on a GET request. This is not allowed, and so we remove both
         * the header and the body here. */
        if (request.method == "GET" && request.headers.has("content-length")) {
            headers.delete("content-length");
            body = undefined;
        }

        /* Resend the request to the actual git host. */
        url.hostname = "[[ hostname ]]";
        const response = await fetch(url.toString(), {
            method: request.method,
            headers,
            body,
            redirect: "follow", // We follow redirects, to avoid us having to rewrite 307s etc.
        });

        return response;
    },
};
