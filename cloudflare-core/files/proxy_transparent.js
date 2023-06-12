export default {
    async fetch(request) {
        const url = new URL(request.url);

        /* Resend the request to the actual git host. */
        url.hostname = "[[ hostname ]]";
        const response = await fetch(url.toString(), {
            method: request.method,
            headers: request.headers,
            body: request.body,
            redirect: "follow", // We follow redirects, to avoid us having to rewrite 307s etc.
        });

        return response;
    },
};
