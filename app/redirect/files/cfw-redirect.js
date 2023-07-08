export default {
  async fetch(request) {
    const url = new URL(request.url);

    switch (url.host) {
      case '[[ alt_domain ]]':
        return Response.redirect('https://www.[[ domain ]]/', 301);

      case 'www.[[ alt_domain ]]':
        return Response.redirect('https://www.[[ domain ]]/', 301);

      case '[[ domain ]]':
        return Response.redirect('https://www.[[ domain ]]/', 301);

      case 'bugs.[[ domain ]]':
        /* Example URLs:
         *  https://bugs.openttd.org/
         *  https://bugs.openttd.org/task/1234
         *  https://bugs.openttd.org/task/1234.html
         */

        const task = url.pathname.match(/^\/task\/(\d+)(\.html)?$/);
        if (task) {
          return Response.redirect(`https://github.com/OpenTTD/OpenTTD/issues/${task[1]}`, 301);
        }

        return Response.redirect('https://github.com/OpenTTD/OpenTTD/issues', 301);

      case 'download.[[ domain ]]':
        return Response.redirect('https://www.[[ domain ]]/downloads/openttd-releases/latest.html', 301);

      case 'forum.[[ domain ]]':
        return Response.redirect('https://www.tt-forums.net/viewforum.php?f=55', 301);

      case 'github.[[ domain ]]':
        return Response.redirect('https://github.com/OpenTTD/OpenTTD/', 301);

      case 'grfsearch.[[ domain ]]':
        /* Example URLs:
         *  https://grfsearch.openttd.org/?do=searchgrfid&q=4E4D2014:7D576D4B6C854EC61C343292D4BBBDFF,47474705:6D9D5B2E44D9EFE3EEE35BB92E971EC8
         *  https://grfsearch.openttd.org/?do=searchtext&q=bestgrfever
        */

        const params = new URLSearchParams(url.search);

        if (params.get('do') === 'searchgrfid') {
          const grfidlist = params.get('q').split(',').map(grfid => grfid.split(':')[0]).join(',');
          return Response.redirect(`https://grfcrawler.tt-forums.net/index.php?do=search&type=grfidlist&q=${grfidlist}`, 301);
        }
        if (params.get('do') === 'searchtext') {
          return Response.redirect(`https://grfcrawler.tt-forums.net/index.php?do=search&q=${params.get('q')}`, 301);
        }

        return Response.redirect('https://grfcrawler.tt-forums.net/index.php', 301);
        break;

      case 'nightly.[[ domain ]]':
        return Response.redirect('https://www.[[ domain ]]/downloads/openttd-nightlies/latest.html', 301);

      case 'noai.[[ domain ]]':
        return Response.redirect('https://docs.[[ domain ]]/ai-api/', 301);

      case 'nogo.[[ domain ]]':
        return Response.redirect('https://docs.[[ domain ]]/gs-api/', 301);

      case 'security.[[ domain ]]':
        let redirect_uri = "/security";

        /* If the URL starts with [/en]/CVE-<year>-<number>, redirect to the new location. */
        const path = url.pathname.replace(/^\/en/, '');
        if (path.match(/^\/CVE-\d{4}-\d+$/)) {
          redirect_uri = `/security${path}`;
        }

        return Response.redirect(`https://www.[[ domain ]]/${redirect_uri}`, 301);
    }

    /* Unkwown host, redirect to the homepage. */
    return Response.redirect('https://www.[[ domain ]]/', 301);
  }
}
