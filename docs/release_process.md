# Release Process <!-- omit in toc -->

How to create releases of `darwin-py`.

## Contents <!-- omit in toc -->

- [Introduction](#introduction)
- [Make a release](#make-a-release)
- [Release a hotfix](#release-a-hotfix)
- [Contact](#contact)

## Introduction

`darwin-py` is released on [pypi.org](https://pypi.org/project/darwin-py/).

It uses [Poetry's](https://python-poetry.org/) "Mason" engine, which builds both [SDIST](https://docs.python.org/3/distutils/sourcedist.html) and [Wheel](https://pythonwheels.com/) artifacts. The package is then uploaded to PyPI using GitHub Actions with OIDC-based authentication.

The build system is [`PEP-518`](https://peps.python.org/pep-0518/) compliant, which is required to install with `pip` versions 25 and over.

These instructions are only applicable to those with permissions to release on the repository, within the V7 organisation, not community contributors.

You can request we make a new release with contributions you have made by emailing [info@v7labs.com](mailto:info@v7labs.com).

## Make a release

The release tag is the version. Nothing is committed to bump it: the publish workflow (`.github/workflows/EVENT_release.yml`) writes the tag's version into `pyproject.toml` and `darwin/version/__init__.py` before it builds the package. The version committed on `master` is not updated by releases.

1. Make sure the latest "Merge to master" workflow run on `master` is green.
2. On GitHub, open [Releases → Draft a new release](https://github.com/v7labs/darwin-py/releases/new).
3. Under "Choose a tag", type the new tag `vX.Y.Z` (the leading `v` is required) and create it on `master`. Bump the minor version if the release contains a feature, otherwise the patch version.
4. Click "Generate release notes", then "Publish release".

Or, with the `gh` CLI:

```sh
gh release create vX.Y.Z --repo v7labs/darwin-py --target master --generate-notes
```

Publishing the release starts two workflows, one after the other:

1. `release-checks` (`.github/workflows/EVENT_release_checks.yml`) rejects tags that are not `vX.Y.Z` or whose commit is not on `master`, runs the tests and the e2e suite (70 to 90 minutes), then starts the publish workflow on `master`.
2. `release` (`.github/workflows/EVENT_release.yml`, run name "Publish vX.Y.Z") runs from `master`, checks the tag again, builds the package and publishes it to PyPI.

Only `master` can publish: the PyPI trusted publisher trusts `EVENT_release.yml` in the `pypi` environment, and only `master` can deploy to that environment. A branch with an edited copy of the workflow cannot publish.

If a job fails on a flake, re-run the failed jobs. If the tests or e2e fail and the code needs a fix, nothing has reached PyPI yet: delete the release and its tag (`gh release delete vX.Y.Z --cleanup-tag`), merge the fix and publish the release again. If the publish run failed, check [PyPI](https://pypi.org/project/darwin-py/#history) first. Once any file of a version is on PyPI, that version cannot be uploaded again, so release the next patch version instead. If nothing reached PyPI, re-run the failed publish jobs, or start the publish again with `gh workflow run EVENT_release.yml --repo v7labs/darwin-py --ref master -f tag=vX.Y.Z -f sha=<tagged commit>`.

When the publish run is green, check that PyPI serves the version and that the wheel carries it:

```sh
curl -s https://pypi.org/pypi/darwin-py/X.Y.Z/json | python3 -c 'import json,sys; print(json.load(sys.stdin)["info"]["version"])'
pip download darwin-py==X.Y.Z --no-deps -d /tmp/darwin-py-check
```

**Make sure you update the tickets to 'Done'**

## Release a hotfix

Merge the fix into `master`, then follow [Make a release](#make-a-release). Releases from other branches are refused.

## Contact

Any issues, reach out in the appropriate channels on slack, or contact john@v7labs.com - Slack is faster.