import pulumi


def _replace_settings(jobspec, **settings):
    for key, value in settings.items():
        jobspec = jobspec.replace(f"[[ {key} ]]", str(value))
    return jobspec


def get_jobspec(filename, settings):
    jobspec = pulumi.Output.from_input(open(filename).read())
    return pulumi.Output.all(jobspec=jobspec, **settings).apply(
        lambda args: _replace_settings(**args), run_with_unknowns=True
    )
