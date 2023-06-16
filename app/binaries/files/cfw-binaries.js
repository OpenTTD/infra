export default {
  async fetch(request, env, context) {
    const url = new URL(request.url);

    /* Old OpenTTD used NSIS installer, which used this domain to fetch
     * OpenGFX / OpenMSX / OpenSFX. To make sure these installers still work,
     * we still serve these files on this domain.
     * Additionally, Emscripten uses it to fetch a valid OpenGFX version.
     */
    if (request.method === 'GET' && url.pathname.startsWith('/installer/')) {
      const objectName = url.pathname.replace(/^\/installer\//, '');

      url.pathname = objectName;
      url.protocol = "https";
      url.search = '';

      const cacheUrl = new URL(url);
      const cacheKey = new Request(cacheUrl.toString(), request);
      const cache = caches.default;

      /* Check if the file is in the cache. */
      let response = await cache.match(cacheKey);

      /* If not, fetch it from the R2 bucket. */
      if (!response) {
        const object = await env.BUCKET_INSTALLER.get(objectName);

        if (object === null) {
          /* Don't cache 404s. */
          return new Response('Not found', { status: 404 });
        }

        const headers = new Headers();
        object.writeHttpMetadata(headers);
        /* Cache for a year. */
        headers.set('cache-control', 'public, max-age=31536000, immutable');
        headers.set('etag', object.httpEtag);

        response = new Response(object.body, {
          headers,
        });

        context.waitUntil(cache.put(cacheKey, response.clone()));
        response.headers.set('cf-cache-status', 'MISS');
      }

      return response;
    }

    /* Pre 14.0 clients made a POST to http://binaries.openttd.org/bananas to
     * get a list of mirrors for BaNaNaS content. This has been moved to
     * https://bananas.openttd.org/bananas (domain and proto is different).
     * Still redirect old requests to the new place to ensure old clients
     * can use the the mirrors too. */
    if (request.method === 'POST' && url.pathname === '/bananas') {
      const init = {
        body: await request.text(),
        method: "POST",
        headers: {
          "user-agent": request.headers.get("user-agent"),
        }
      }

      const response = await fetch(`https://[[ hostname ]]-server.[[ domain ]]/bananas`, init);
      return response;
    }

    /* Return a 404 for everything else. */
    return new Response('Not found', { status: 404 });
  }
}
