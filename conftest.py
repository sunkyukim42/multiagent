# External baseline checkouts are inspected as inert files only.
# They must never be imported or collected as part of this repository's tests.
collect_ignore = [
    "results/external_baselines",
]

collect_ignore_glob = [
    "results/external_baselines/*",
    "results/external_baselines/**/*",
]
