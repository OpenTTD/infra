export default {
  async fetch(request) {
      if (request.method !== "GET") {
          return new Response("Method Not Allowed", { status: 405 });
      }

      const url = new URL(request.url);
      let headers = new Headers(request.headers);

      /* Request the filename from GitHub. */
      url.hostname = "raw.githubusercontent.com";
      url.pathname = "/OpenTTD/nile-data/main/" + url.pathname;
      let response = await fetch(url.toString(), {
          method: request.method,
          headers,
          redirect: "follow", // We follow redirects, to avoid us having to rewrite 307s etc.
      });

      /* Add CORS headers. */
      response = new Response(response.body, response);
      response.headers.set('access-control-allow-origin', '*');
      return response;
  },
};
