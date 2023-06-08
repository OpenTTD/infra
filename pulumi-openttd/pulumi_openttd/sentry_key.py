import pulumi
import pulumiverse_sentry


def _replace_settings(jobspec, **settings):
    for key, value in settings.items():
        jobspec = jobspec.replace(f"[[ {key} ]]", str(value))
    return jobspec


def get_sentry_key(project, sentry_ingest_hostname, domain):
    sentry_key = pulumiverse_sentry.get_sentry_key(
        organization="openttd",
        project=project,
    )

    # sentry.io doesn't support IPv6, so we route it via our own domain.
    return pulumi.Output.all(
        sentry_ingest_hostname=sentry_ingest_hostname,
        sentry_key=sentry_key.dsn_public,
        domain=domain,
    ).apply(lambda args: args["sentry_key"].replace(args["sentry_ingest_hostname"], f"sentry-ingest.{args['domain']}"))
