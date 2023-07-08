export default {
  async fetch(request, env, context) {
    if (request.method !== 'GET') {
      return new Response('Method not allowed', { status: 405 });
    }

    const url = new URL(request.url);
    url.search = '';

    /* Redirect requests to the root page to www.openttd.org. */
    if (url.pathname === '/') {
      return Response.redirect('https://www.openttd.org/', 301);
    }

    /* URLs are like /prNNN/filename. Split them apart. */
    const urlParts = url.pathname.split('/');
    const prNumber = urlParts[1];
    let objectName = urlParts.slice(2).join('/');

    /* If the objectName is empty, make it into "openttd", as that is our index page. */
    if (objectName === '') {
      objectName = 'openttd';
    }

    /* The actual URL is https://prNNN.openttd-preview.pages.dev/filename. */
    const actualUrl = `https://${prNumber}.[[ name ]].pages.dev/${objectName}`;

    /* Fetch the actual URL. */
    return await fetch(actualUrl, {
      cf: {
        cacheTtl: 60,
        cacheEverything: true,
        cacheKey: actualUrl,
      },
    });
  }
}
