function responseWithCacheStatus(response, cache_status) {
  let headers = new Headers(response.headers);
  headers.set('cf-cache-status', cache_status);
  return new Response(response.body, {
    headers,
    status: response.status,
    statusText: response.statusText,
  });
}

function responseCheckEtag(request, response) {
  /* If the request has an If-None-Match header, check if the response is
   * still fresh. */
  const ifNoneMatch = request.headers.get('if-none-match');
  const etag = response.headers.get('etag');

  if (ifNoneMatch && etag) {
    if (ifNoneMatch === etag) {
      return new Response(null, {
        status: 304,
        statusText: 'Not Modified',
        headers: {
          'cf-cache-status': response.headers.get('cf-cache-status'),
        }
      });
    }
  }

  /* We don't support range requests for cached files. */
  if (etag) {
    response.headers.delete("accept-ranges");
  }
  return response;
}

export default {
  async fetch(request, env, context) {
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      const response = await fetch(request);
      return responseWithCacheStatus(response, 'BYPASS');
    }

    /* If "wiki_sid" cookie is set, the user is logged in. Don't cache. */
    const cookie = request.headers.get('cookie');
    if (cookie && cookie.match(/wiki_sid=([^;]+)/)) {
      const response = await fetch(request);
      return responseWithCacheStatus(response, 'BYPASS');
    }

    const url = new URL(request.url);

    /* Ignore the if-none-match / if-modified-since header for cache evaluation. We run our own. */
    const strippedRequest = new Request(url.toString(), request);
    strippedRequest.headers.delete('if-none-match');
    strippedRequest.headers.delete('if-modified-since');

    /* Check if the file is in the cache. */
    const cacheKey = new Request(url.toString() + ".cache", strippedRequest);
    const cache = caches.default;
    let response = await cache.match(cacheKey);

    const objectName = url.pathname.replace(/^\//, '') + ".cache";

    if (response && response.headers.get('etag')) {
      /* Check with the backend if this resource is still fresh. */
      let backendRequest = strippedRequest.clone();
      backendRequest.headers.set('If-None-Match', response.headers.get('etag'));
      const backendResponse = await fetch(backendRequest, {
        cf: {
          cacheTtl: 0,
        }
      });

      if (backendResponse.status === 304) {
        /* Still fresh, return the cached response. */
        response = responseWithCacheStatus(response, 'REVALIDATED');
        /* Restore the original cache-control header. */
        response.headers.set('cache-control', response.headers.get('x-cache-control'));
        response.headers.delete('x-cache-control');
        return responseCheckEtag(request, response);
      }

      /* Not fresh; update the cache with the new reply. */
      response = responseWithCacheStatus(backendResponse, 'EXPIRED');

      /* Take a look in the bucket, to see if that object also expired. */
      const object = await env.BUCKET_CACHE.get(objectName);
      if (object === null || object.customMetadata.etag !== backendResponse.headers.get('etag')) {
        /* The object in the bucket is outdated; update it. */
        context.waitUntil(env.BUCKET_CACHE.put(objectName, backendResponse.clone().body, {
          httpMetadata: backendResponse.headers,
          customMetadata: {
            'etag': backendResponse.headers.get('etag'),
          },
        }));
      }
    } else {
      /* Not in the cache; check the R2 bucket. */
      const object = await env.BUCKET_CACHE.get(objectName);

      if (object !== null) {
        /* Check with the backend if this resource is still fresh. */
        let backendRequest = strippedRequest.clone();
        backendRequest.headers.set('If-None-Match', object.customMetadata.etag);
        const backendResponse = await fetch(backendRequest, {
          cf: {
            cacheTtl: 0,
          }
        });

        if (backendResponse.status === 304) {
          /* Still fresh, return the R2 object. */
          const headers = new Headers();
          object.writeHttpMetadata(headers);
          headers.set('etag', object.customMetadata.etag);

          response = new Response(object.body, {
            headers,
          });

          /* We "use" the UPDATING status here, as Cloudflare can visualise that correctly
           * in statistics. It strictly seen means something else, but it is good enough. */
          response = responseWithCacheStatus(response, 'UPDATING');
          return responseCheckEtag(request, response);
        }

        response = backendResponse;
      } else {
        /* Not in cache / R2 (or didn't contain a etag); fetch from backend. */
        response = await fetch(strippedRequest);
      }

      if (response.headers.get('etag')) {
        /* Mark as a cache miss if we are going to cache it. No matter what the internal cache said. */
        response = responseWithCacheStatus(response, 'MISS');

        /* Store the entry also in the R2 bucket. */
        context.waitUntil(env.BUCKET_CACHE.put(objectName, response.clone().body, {
          httpMetadata: response.headers,
          customMetadata: {
            'etag': response.headers.get('etag'),
          },
        }));
      }
    }

    /* Only cache if we have the etag header. */
    if (response.headers.get('etag')) {
      /* Cache files for a year on Cloudflare. The idea here is: as we revalidate
       * every request anyway, we can cache the responses on Cloudflare for a long
       * time. If ETag indicates there hasn't been a change, we can return the
       * cached response instead. */
      response.headers.set('x-cache-control', response.headers.get('cache-control'));
      response.headers.set('cache-control', 'public, max-age=31536000');
      /* We remove the Last-Modified header, as it can be outdated. */
      response.headers.delete("last-modified");
      context.waitUntil(cache.put(cacheKey, response.clone()));

      /* Restore the original cache-control header. */
      response.headers.set('cache-control', response.headers.get('x-cache-control'));
      response.headers.delete('x-cache-control');
    }

    return responseCheckEtag(request, response);
  }
}
