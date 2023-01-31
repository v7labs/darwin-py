# Release Process <!-- omit in toc -->

How to create releases of `darwin-py`.

## Contents <!-- omit in toc -->

- [Introduction](#introduction)
- [Make a standard release](#make-a-standard-release)
  - [Steps](#steps)
- [Make a hotfix release](#make-a-hotfix-release)
  - [Steps](#steps-1)
- [Contact](#contact)


## Introduction

`darwin-py` is released on [pypi.org](https://pypi.org/project/darwin-py/).  It uses [Poetry's]([https://poetry-python](https://python-poetry.org/)) "Mason" engine, which builds both [SDIST](https://docs.python.org/3/distutils/sourcedist.html) and [Wheel](https://pythonwheels.com/) artefacts, and uploads them to PyPi using `setuptools`.  The build system is [`PEP-518`](https://peps.python.org/pep-0518/) compliant, which is required to install with `pip` versions 25 and over.

These instructions are only applicable to those with permissions to release on the repository, within the V7 organisation, not community contributors.  You can request we make a new release with contributions you have made by emailing [info@v7labs.com](mailto:info@v7labs.com).

## Make a standard release

These are the steps for releasing a passing `master` branch.  If you are releasing a hotfix or other selective build, you need to follow the instructions for a [hotfix release](#make-a-hotfix-release).

### Steps

1. Ensure all tickets to be included are QA'd and to be included in a release.  Speak to PM's and code owners if unsure.
2. Once passed on QA, merge all PRs to be included into `master`
3. Ensure that `master` tests are still passing after merge.
4. Checkout a new branch for the version bump.
5. Open `pyproject.toml`, and update the version in there.  Maintain semver, and agree with owner if you are intending to make a release that is not a minor increment.
```
[tool.poetry]
name = "darwin-py"
version = "0.8.7" # update this when you change the version - See: https://peps.python.org/pep-0440/
```
6. Add, commit, and open a PR for the version bump.  
7. Once accepted, merge, and tag `master` with the version you have set, prefixed with "v".  E.g. if you set the version to `1.2.3`, then tag as `v1.2.3`
```shell
$ git checkout master
$ git tag v1.2.3 master  # for example
$ git push origin v1.2.3  # again, for example
```
8. Push the tag.
9.  In the ["Draft a new release"](https://github.com/v7labs/darwin-py/releases/new) section of github, select the tag you created.  Write an appropriate summary of the release (see Engineering team guidance on language), and create the release.  Click "Publish release"
10. Ensure release is successful in CI/CD
11. Ensure that release appears in Pypi.

## Make a hotfix release

Making a hotfix release is _broadly_ the same as the process for [making a normal release](#make-a-standard-release), but first you need to `cherry-pick` the items you need into a hotfix branch.

### Steps

1. Create a hotfix branch to contain your new release, based on the **last release, not master**.
```shell
$ git checkout v1.2.2  # for example - should be the last released tag
$ git checkout -b hotfix_branch_v1_2_3  # naming discretionary, branch won't exist long 
```
2. Two possible routes forward:
   1. If your branch is based on other, unmerged branches, then you can merge them into your hotfix branch:
    ```shell
    $ git merge thing_i_need_in_hotfix
    $ git merge other_thing_i_need_in_hotfix
    ```

    You may have to settle merge conflicts.

   2. If your branch is based on already-merged-into-master items, then you need to use `cherry-pick` to include them in your branch.  We use a squash-merge on PR, so you can cherry pick the squash merge of each PR, this will be the commit number that was actually merged in.  If for some reason you're dealing with merges not squash-merged, you need to cherry pick each commit from the branch in, in order that they happened.
   ```sh
   $ git cherry-pick [commit-number]
   $ git cherry-pick [other-commit-number]
   ...and so on
   ```
3. After these, you will have a branch with the items you need to include in a hot-fix.  Open `pyproject.toml`, and update the version in there.  Maintain semver, and agree with owner if you are intending to make a release that is not a minor increment.
```
[tool.poetry]
name = "darwin-py"
version = "0.8.7" # update this when you change the version - See: https://peps.python.org/pep-0440/
```
4. Add, commit, and push the branch. 
5. Once accepted, tag the branch with the version you have set, prefixed with "v".  E.g. if you set the version to `1.2.3`, then tag as `v1.2.3`
```shell
$ git checkout [your hotfix branch name]
$ git tag v1.2.3 [your hotfix branch name]  # for example
$ git push origin v1.2.3  # again, for example
```
6. Push the tag.
7.  In the ["Draft a new release"](https://github.com/v7labs/darwin-py/releases/new) section of github, select the tag you created, and the hotfix branch.  Write an appropriate summary of the release (see Engineering team guidance on language), and create the release.  Click "Publish release"
8.  Ensure release is successful in CI/CD
9.  Ensure release is successful in Pypi

## Contact

Any issues, reach out in the appropriate channels on slack, or contact owen@v7labs.com - Slack is faster.