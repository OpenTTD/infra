export default {
  async fetch(request) {
    const url = new URL(request.url);

    if (url.pathname == "/favicon.ico") {
      return fetch("https://www.[[ domain ]]/static/favicon.ico", {
        cf: {
          cacheEverything: true,
        }
      });
    }

    let response = await fetch(`https://[[ hostname ]].[[ domain ]]/weblogs${url.pathname}`, {
      cf: {
        cacheEverything: true,
      }
    });

    if (response.status == 200) {
      let body = (await response.text()).replace(/href="\/weblogs\//g, 'href="/');
      response = new Response(body, { ...response });
    }

    return response;
  }
}
