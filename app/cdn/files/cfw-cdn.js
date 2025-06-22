
const public_keys = {
[[ public_keys ]]
};

async function handleUploadFile(request, env) {
  const url = new URL(request.url);
  const objectName = url.pathname.replace(/^\//, '');
  const folder = objectName.split('/')[0];

  const signature = request.headers.get("x-signature");
  const content_type = request.headers.get("content-type");

  /* Sanity check, to make sure the request contains all required headers. */
  if (!signature) {
    return new Response('Not Found', { status: 404 });
  }
  if (!content_type) {
    return new Response('Not Found', { status: 404 });
  }
  if (!(folder in public_keys)) {
    return new Response('Not Found', { status: 404 });
  }

  /* Import the public key. */
  const public_key = await crypto.subtle.importKey(
    "spki",
    new Uint8Array(atob(public_keys[folder]).split("").map(c => c.charCodeAt(0))),
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
  const result_head = await env.BUCKET_CDN.head(objectName);
  if (result_head) {
    /* If the object exists, check if the md5 checksum matches with the request body. */

    const digestStream = new crypto.DigestStream("MD5");
    request.body.pipeTo(digestStream);
    const requestDigest = await digestStream.digest;
    const requestMd5 = [...new Uint8Array(requestDigest)]
      .map(b => b.toString(16).padStart(2, '0'))
      .join('')

    const objectMd5 = [...new Uint8Array(result_head.checksums.md5)]
      .map(b => b.toString(16).padStart(2, '0'))
      .join('')

    /* This was a reupload of the same file. Act like it succeeded. */
    if (objectMd5 === requestMd5) {
      return new Response('OK - Identical File Already Exists', { status: 200 });
    }

    return new Response('File Already Exists', { status: 409 });
  }

  /* Upload the new file. */
  const result_put = await env.BUCKET_CDN.put(objectName, request.body,
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

    if (request.method !== 'GET') {
      return new Response('Method not allowed', { status: 405 });
    }

    const url = new URL(request.url);

    let objectName = url.pathname.replace(/^\//, '');
    /* If a folder is requested, request the index.html instead. */
    if (objectName.endsWith('/') || objectName == '') {
      objectName += 'index.html';
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
      const object = await env.BUCKET_CDN.get(objectName);

      if (object === null) {
        /* Don't cache 404s. */
        return new Response('Not found', { status: 404 });
      }

      const headers = new Headers();
      object.writeHttpMetadata(headers);
      /* Cache most files for a year; .html and .yaml are used to index the bucket, so we cache those shorter. */
      if (objectName.endsWith('.html') || objectName.endsWith('.yaml')) {
        headers.set('cache-control', 'public, max-age=60, must-revalidate');
      } else {
        headers.set('cache-control', 'public, max-age=31536000, immutable');
      }
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
