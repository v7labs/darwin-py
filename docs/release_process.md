# Release Process <!-- omit in toc -->

How to create releases of `darwin-py`.

## Contents <!-- omit in toc -->

- [Introduction](#introduction)
- [Make a standard release](#make-a-standard-release)
  - [Steps](#steps)
- [Make a non-standard release](#make-a-non-standard-release)
- [Contact](#contact)

## Introduction

`darwin-py` is released on [pypi.org](https://pypi.org/project/darwin-py/). 

It uses [Poetry's](https://python-poetry.org/) "Mason" engine, which builds both [SDIST](https://docs.python.org/3/distutils/sourcedist.html) and [Wheel](https://pythonwheels.com/) artifacts. The package is then uploaded to PyPI using GitHub Actions with OIDC-based authentication.

The build system is [`PEP-518`](https://peps.python.org/pep-0518/) compliant, which is required to install with `pip` versions 25 and over.

These instructions are only applicable to those with permissions to release on the repository, within the V7 organisation, not community contributors.

You can request we make a new release with contributions you have made by emailing [info@v7labs.com](mailto:info@v7labs.com).

## Make a standard release

These are the steps for releasing a passing `master` branch.

If you are releasing a hotfix or other selective build, you need to follow the instructions for a [non-standard release](#make-a-non-standard-release).

### Steps

**Pre-release**

1. Ensure all tickets to be included are QA'd and to be included in a release. Speak to PM's and code owners if unsure.
2. Once passed on QA, merge all PRs to be included into `master`

**Release**

This is the process for making a simple semver _patch_ release. If you need to make a _minor_ or _major_ version release, follow the instructions for [Making a non-standard release](#make-a-non-standard-release)

1. Run the script `deploy/create_release.sh` - follow the prompts, and the script will:
   * Increment the version in all places it exists
   * Commit this, and push these changes, along with a tag for the version
   * Check the script didn't throw any errors, if it didn't, the script will prompt you to look at the Actions dialog, to see when the tests and quality checks all pass.
   **NB: If checks fail, the release will fail**
2. A draft release will be created in Github. You can release this with the UI or the `gh` CLI.
3. Once the release is published, the GitHub Actions workflow will automatically build and publish the package to PyPI using OIDC-based authentication.

**Done!**

**Make sure you update the tickets to 'Done'**

## Make a non-standard release

Making a non-standard release (like a hotfix) is _broadly_ the same as the process for [making a normal release](#make-a-standard-release), but with a few more steps:

1. Run the script `python deploy/increase_version.py` and use `--patch`, `--minor`, or `--major` to set the version change you want to make. If you need to make a more complex version change (changing more than one aspect of the version), you can pass `--new-version` followed by a valid semver version.
2. Commit and push the changes to master
3. Add a tag using `git tag v0.0.0`, substituting the right version number (**NB: the preceding 'v' is necessary for release**)
4. Push the tag `git push origin v0.0.0`, again substituting the right version number
5. A draft release will be created in Github. You can release this with the UI or the `gh` CLI.
6. Once the release is published, the GitHub Actions workflow will automatically build and publish the package to PyPI using OIDC-based authentication.

**Make sure you update the tickets to 'Done'**

## Contact

Any issues, reach out in the appropriate channels on slack, or contact john@v7labs.com - Slack is faster.