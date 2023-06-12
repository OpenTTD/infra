export default {
    async fetch(request) {
        const url = new URL(request.url);

        /* Resend the request to the actual registry. */
        url.hostname = "[[ hostname ]]";
        const response = await fetch(url.toString(), {
            method: request.method,
            headers: request.headers,
            body: request.body,
            redirect: "follow", // We follow redirects, to avoid us having to rewrite 307s etc.
        });

        /* In case of a 401 (unauthorized), there is a header that needs rewriting. */
        if (response.status == 401) {
            let new_response = new Response(response.body, {
                status: 401,
                statusText: "Unauthorized",
                headers: response.headers,
            });

            /*
             * Example of WWW-Authenticate header:
             *   WWW-Authenticate: Bearer realm="https://ghcr.io/token",service="ghcr.io",scope="repository:user/image:pull"
             *
             * We need to replace the realm part here with our own.
             */

            const realm = new URL(request.url);
            realm.pathname = "/token";

            const auth_header = response.headers.get("WWW-Authenticate");
            new_response.headers.set("WWW-Authenticate", auth_header.replace(/realm="[^"]+"/, `realm="${realm.href}"`));

            return new_response;
        }

        return response;
    },
};
