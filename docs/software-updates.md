# Software Updates

All software needs maintenance.
OpenTTD's software is no difference: not only the game, but also the services related.

There are two reasons to keep things updated on the regular:
- Big dependency updates can mean a lot of small differences which break the software.
  Doing it on the regular reduces that risks, making it easier to spot why a dependency update broke something.
- If a dependency is hit by a CVE, you can update quickly without worrying too much about unrelated dependency updates.

## Production

As one should update like every 3 months (and so pretty repetitive), it is made as easy as possible:
when a new commit on `main` lands in any of the repositories of the backend services, it will automatically build that version and deploy it to production.
You better make sure that the PR works before you merge!

## Preview

To that effect, all OpenTTD's backend services run twice: once for production, and once for "preview" (or staging, or testing, call it what you want; OpenTTD calls it "preview").
This is a very minimal deployment of the service, meant to smoketest whether a PR works before merging.

On all repositories of the backend service you can attach the `preview` label to any PR, and it will automatically build that PR and deploy it to preview.
Preview URLs are things like:

- https://wiki-preview.openttd.org
- https://bananas-preview.openttd.org

Etc etc.

This works great for website, but what about the content-service (bananas-server) you ask?
For this, you need to set some environment variables when launching OpenTTD:

```bash
OTTD_CONTENT_MIRROR_URI="https://binaries-preview.openttd.org/bananas" OTTD_CONTENT_SERVER_CS="content-preview.openttd.org:4978" ./openttd
```

Generally speaking, adding 1000 to the port OpenTTD talks to is the port used for preview.

The only exception here is `dibridge`.
Although it does have a preview running, you need access to a secret server and IRC channel to actually test it.
So you will just have to wing it.

## Repositories

Below is the table of all repositories with active dependabot PRs.
Dependabot is the automation that is running to update the dependencies.

Be mindful: in a time where supply-chain attacks are normal, it is wise to hold back on the latest version for a few weeks.
Dependabot can (and should) be configured to only update after a release is released for N days.

NOTE: if no dependabot PR has been touched in a few weeks, dependabot will pause its actions.
You can manually run a new dependabot via `Insights` -> `Dependency graph` -> `Dependabot`.
Clicking on any file allows you to start a new run.

| Name | PRs | 
| --- | --- | 
| actions| [![PRs actions](https://img.shields.io/github/issues-pr/OpenTTD/actions/dependencies?label=)](https://github.com/OpenTTD/actions/pulls)|
| bananas-api| [![PRs bananas-api](https://img.shields.io/github/issues-pr/OpenTTD/bananas-api/dependencies?label=)](https://github.com/OpenTTD/bananas-api/pulls)|
| bananas-frontend-cli| [![PRs bananas-frontend-cli](https://img.shields.io/github/issues-pr/OpenTTD/bananas-frontend-cli/dependencies?label=)](https://github.com/OpenTTD/bananas-frontend-cli/pulls)|
| bananas-frontend-web| [![PRs bananas-frontend-web](https://img.shields.io/github/issues-pr/OpenTTD/bananas-frontend-web/dependencies?label=)](https://github.com/OpenTTD/bananas-frontend-web/pulls)|
| bananas-server| [![PRs bananas-server](https://img.shields.io/github/issues-pr/OpenTTD/bananas-server/dependencies?label=)](https://github.com/OpenTTD/bananas-server/pulls)|
| dibridge| [![PRs dibridge](https://img.shields.io/github/issues-pr/OpenTTD/dibridge/dependencies?label=)](https://github.com/OpenTTD/dibridge/pulls)|
| DorpsGek| [![PRs DorpsGek](https://img.shields.io/github/issues-pr/OpenTTD/DorpsGek/dependencies?label=)](https://github.com/OpenTTD/DorpsGek/pulls)|
| eints| [![PRs eints](https://img.shields.io/github/issues-pr/OpenTTD/eints/dependencies?label=)](https://github.com/OpenTTD/eints/pulls)|
| game-coordinator| [![PRs game-coordinator](https://img.shields.io/github/issues-pr/OpenTTD/game-coordinator/dependencies?label=)](https://github.com/OpenTTD/game-coordinator/pulls)|
| master-server| [![PRs master-server](https://img.shields.io/github/issues-pr/OpenTTD/master-server/dependencies?label=)](https://github.com/OpenTTD/master-server/pulls)|
| master-server-web| [![PRs master-server-web](https://img.shields.io/github/issues-pr/OpenTTD/master-server-web/dependencies?label=)](https://github.com/OpenTTD/master-server-web/pulls)|
| py-helpers| [![PRs py-helpers](https://img.shields.io/github/issues-pr/OpenTTD/py-helpers/dependencies?label=)](https://github.com/OpenTTD/py-helpers/pulls)|
| py-protocol| [![PRs py-protocol](https://img.shields.io/github/issues-pr/OpenTTD/py-protocol/dependencies?label=)](https://github.com/OpenTTD/py-protocol/pulls)|
| survey-web| [![PRs survey-web](https://img.shields.io/github/issues-pr/OpenTTD/survey-web/dependencies?label=)](https://github.com/OpenTTD/survey-web/pulls)|
| website| [![PRs website](https://img.shields.io/github/issues-pr/OpenTTD/website/dependencies?label=)](https://github.com/OpenTTD/website/pulls)|
| workflows| [![PRs workflows](https://img.shields.io/github/issues-pr/OpenTTD/workflows/dependencies?label=)](https://github.com/OpenTTD/workflows/pulls)|
