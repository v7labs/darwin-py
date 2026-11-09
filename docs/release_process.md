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

The release tag is the version. Nothing is committed to bump it: the `release` workflow (`.github/workflows/EVENT_release.yml`) writes the tag's version into `pyproject.toml` and `darwin/version/__init__.py` before it builds the package. The version committed on `master` is not updated by releases.

1. Make sure the latest "Merge to master" workflow run on `master` is green.
2. On GitHub, open [Releases → Draft a new release](https://github.com/v7labs/darwin-py/releases/new).
3. Under "Choose a tag", type the new tag `vX.Y.Z` (the leading `v` is required) and create it on `master`. Bump the minor version if the release contains a feature, otherwise the patch version.
4. Click "Generate release notes", then "Publish release".

Or, with the `gh` CLI:

```sh
gh release create vX.Y.Z --repo v7labs/darwin-py --target master --generate-notes
```

Publishing the release starts the `release` workflow. It rejects tags that are not `vX.Y.Z`, runs the tests and the e2e suite (70 to 90 minutes), then builds and publishes the package to PyPI. If a job fails on a flake, re-run the failed jobs. If the tests or e2e fail and the code needs a fix, nothing has reached PyPI yet: delete the release and its tag (`gh release delete vX.Y.Z --cleanup-tag`), merge the fix and publish the release again. If the `release` job failed while publishing, check [PyPI](https://pypi.org/project/darwin-py/#history) first. Once any file of a version is on PyPI, that version cannot be uploaded again, so release the next patch version instead.

When the run is green, check that PyPI serves the version and that the wheel carries it:

```sh
curl -s https://pypi.org/pypi/darwin-py/X.Y.Z/json | python3 -c 'import json,sys; print(json.load(sys.stdin)["info"]["version"])'
pip download darwin-py==X.Y.Z --no-deps -d /tmp/darwin-py-check
```

**Make sure you update the tickets to 'Done'**

## Release a hotfix

Push a branch with the fix, then follow [Make a release](#make-a-release) with that branch as the target instead of `master` (`--target <branch>` with `gh`). Merge the fix into `master` afterwards.

The branch must contain the tag-driven `.github/workflows/EVENT_release.yml`, because the release runs the workflow from the tagged commit. If it starts from a release made before that workflow existed (v3.7.0 or older), copy the current `EVENT_release.yml` from `master` onto the branch first. Otherwise the old workflow builds the version committed in `pyproject.toml` instead of the tag's version.

## Contact

Any issues, reach out in the appropriate channels on slack, or contact john@v7labs.com - Slack is faster.