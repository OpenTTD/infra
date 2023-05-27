import pulumi


def _replace_settings(jobspec, **settings):
    for key, value in settings.items():
        jobspec = jobspec.replace(f"[[ {key} ]]", str(value))
    return jobspec


def get_jobspec(jobspec, settings):
    jobspec = pulumi.Output.from_input(jobspec)
    return pulumi.Output.all(jobspec=jobspec, **dict((key, setting.value) for key, setting in settings.items())).apply(
        lambda args: _replace_settings(**args), run_with_unknowns=True
    )
