
const public_keys = {
[[ public_keys ]]
};

async function handleUploadFile(request, env) {
  const url = new URL(request.url);
  const objectName = url.pathname.replace(/^\//, '');

  const signature = request.headers.get("x-signature");
  const repository = request.headers.get("x-repository");
  const content_type = request.headers.get("content-type");

  /* Sanity check, to make sure the request contains all required headers. */
  if (!signature) {
    return new Response('Not Found', { status: 404 });
  }
  if (!repository) {
    return new Response('Not Found', { status: 404 });
  }
  if (!content_type) {
    return new Response('Not Found', { status: 404 });
  }
  if (!(repository in public_keys)) {
    return new Response('Not Found', { status: 404 });
  }

  /* Import the public key. */
  const public_key = await crypto.subtle.importKey(
    "spki",
    new Uint8Array(atob(public_keys[repository]).split("").map(c => c.charCodeAt(0))),
    {
      name: "RSASSA-PKCS1-v1_5",
      hash: "SHA-256"
    },
    false,
    ["verify"]
  );

  /* Verify the signature is valid. */
  const result = await crypto.subtle.verify(
    "RSASSA-PKCS1-v1_5",
    public_key,
    new Uint8Array(atob(signature).split("").map(c => c.charCodeAt(0))),
    new TextEncoder().encode(objectName)
  )
  if (!result) {
    return new Response('Not Found', { status: 404 });
  }

  /* Do not allow overwriting files. */
  const result_head = await env.BUCKET_SYMBOLS.head(objectName);
  if (result_head) {
    return new Response('File Already Exists', { status: 409 });
  }

  /* Upload the new file. */
  const result_put = await env.BUCKET_SYMBOLS.put(objectName, request.body,
    {
      httpMetadata: {
        contentType: content_type,
      }
    }
  );
  if (!result_put) {
    return new Response('Internal Server Error', { status: 500 });
  }
  return new Response('OK', { status: 200 });
}

export default {
  async fetch(request, env, context) {
    if (request.method === 'PUT') {
      return handleUploadFile(request, env);
    }

    if (request.method !== 'GET' && request.method !== 'HEAD') {
      return new Response('Method not allowed', { status: 405 });
    }

    let url = new URL(request.url);

    let objectName = url.pathname.replace(/^\//, '');
    /* If a folder is requested, tell the user listing is not allowed. */
    if (objectName.endsWith('/') || objectName == '') {
      return new Response('Forbidden', { status: 403 });
    }

    /* We only serve .sym, .pdb, and .exe files. If anything else is requested, just cancel it. */
    if (!objectName.endsWith('.sym') && !objectName.endsWith('.pdb') && !objectName.endsWith('.exe')) {
      return new Response('Not found', { status: 404 });
    }

    if (!objectName.startsWith('openttd')) {
      /* All symbol-requests that are not related to OpenTTD we forward to Mozilla. */
      if (objectName.endsWith('.sym')) {
        url.hostname = 'symbols.mozilla.org';
        return fetch(url.toString(), request);
      }

      return new Response('Not found', { status: 404 });
    }

    /* All symbol-files are stored compressed on the R2 bucket. */
    objectName += ".gz";

    if (request.method === 'HEAD') {
      const object = await env.BUCKET_SYMBOLS.head(objectName);
      if (object === null) {
        return new Response('Not found', { status: 404 });
      }

      const headers = new Headers();
      object.writeHttpMetadata(headers);
      headers.set('etag', object.httpEtag);
      headers.set('content-type', 'text/plain');

      return new Response(null, {
        headers,
      });
    }

    url.pathname = objectName;
    url.search = '';

    const cacheUrl = new URL(url);
    const cacheKey = new Request(cacheUrl.toString(), request);
    const cache = caches.default;

    /* Check if the file is in the cache. */
    let response = await cache.match(cacheKey);

    /* If not, fetch it from the R2 bucket. */
    if (!response) {
      const object = await env.BUCKET_SYMBOLS.get(objectName);

      if (object === null) {
        /* Don't cache 404s. */
        return new Response('Not found', { status: 404 });
      }

      const headers = new Headers();
      object.writeHttpMetadata(headers);
      /* Cache symbol files for a year. */
      headers.set('cache-control', 'public, max-age=31536000, immutable');
      headers.set('etag', object.httpEtag);

      /* We force a gzip encoding; that way we don't have to extract the gzip-stored file from the R2 bucket. */
      headers.set('content-type', 'text/plain');
      headers.set('content-encoding', 'gzip');
      response = new Response(object.body, {
        headers,
        encodeBody: 'manual',
      });

      /* Cloudflare can only cache up to 512MB. We shouldn't have anything larger, but .. just be safe. */
      if (object.size < 512 * 1024 * 1024) {
        context.waitUntil(cache.put(cacheKey, response.clone()));
      }

      response.headers.set('cf-cache-status', 'MISS');
    } else {
      /* Bit of trickery as the cached item is also a gzip compressed file. */
      response = new Response(response.body, {
        headers: response.headers,
        encodeBody: 'manual',
      });
      response.headers.set('content-encoding', 'gzip');
    }

    return response;
  }
}
