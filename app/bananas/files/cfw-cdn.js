export default {
  async fetch(request, env, context) {
    if (request.method !== 'GET') {
      return new Response('Method not allowed', { status: 405 });
    }

    const url = new URL(request.url);
    const fullObjectName = url.pathname;

    /* Rewrite the first to the second:
     *  /base-graphics/12345678/12345678901234567890123456789012/filename.tar.gz
     *  base-graphics/12345678/12345678901234567890123456789012.tar.gz
     * This allows the OpenTTD client to know the name to use for the file,
     * while the bucket only knows the md5sum based name.
     */
    const objectName = fullObjectName.replace(/^\/([a-z-]+)\/([a-f0-9]{8})\/([a-f0-9]{32})\/[a-zA-Z0-9-_\.]+.tar.gz$/, '$1\/$2\/$3.tar.gz');

    /* If there is no file, or the regex didn't match, return a 404. */
    if (objectName === '' || fullObjectName == objectName) {
      return new Response('Not found', { status: 404 });
    }

    /* Create cache-key; make sure the same object has only a single URL. */
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
      const object = await env.BUCKET_CDN.get(objectName);

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

      /* Cloudflare can only cache up to 512MB. We shouldn't have anything larger, but .. just be safe. */
      if (object.size < 512 * 1024 * 1024) {
        context.waitUntil(cache.put(cacheKey, response.clone()));
      }

      response.headers.set('cf-cache-status', 'MISS');
    }

    return response;
  }
}
