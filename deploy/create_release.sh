#!/usr/bin/env bash
WORKING_DIR=$(dirname "$0")

echo "CLI Tool for creating a new release in one step."
echo
echo "Releases from master branch only.  To perform releases from other branches, tag the branch and push the tag"
echo
echo "Usage: ./deploy/create_release.sh"
echo

# Check that the current branch is master
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "master" ]; then
    echo "ERROR: You must be on the master branch to create a release."
    exit 1
fi

# Check that the working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: You have uncommitted changes.  Please commit or stash them before creating a release."
    exit 1
fi

# Check that the remote is set
REMOTE=$(git remote get-url origin)
if [ -z "$REMOTE" ]; then
    echo "ERROR: The remote is not set.  Please set the remote before creating a release."
    exit 1
fi

# Increment the version number one patch version
"$WORKING_DIR/increase_version.sh --patch --force"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to increase the version number."
    exit 1
fi
VERSION=$(cat "$WORKING_DIR/../VERSION")
if [ -z "$VERSION" ]; then
    echo "ERROR: Failed to read the version number."
    exit 1
fi

echo "Created changes for release v$VERSION"
echo
echo "Please review the changes and commit them."
echo
echo "Continue? (y/n)"
read -r CONTINUE
if [ "$CONTINUE" != "y" ]; then
    echo "Aborting."
    exit 1
fi
echo

# Commit the changes
commit_and_tag=$(git add "$WORKING_DIR/../darwin/version/__init__.py" && \
    git add "$WORKING_DIR/../pyproject.toml" && \
    git commit -m "HOUSEKEEPING: Bump version to v$VERSION" && \
    git tag master "v$VERSION" && \
git push origin "v$VERSION")
masterpush=$(git push origin master)

if [ "$commit_and_tag" -ne 0 ]; then
    echo "ERROR: Failed to commit the changes and tag the release.  You may have an issue with your git configuration."
    exit 1
fi

if [ "$masterpush" -ne 0 ]; then
    echo "ERROR: Failed to push the changes.  You need to be an admin to bump version directly on master."
    echo "Stash your changes to a branch and create a pull request."
    exit 1
fi


echo "Successfully created release v$VERSION"
echo "The release action should trigger, and the release will be available on PyPI in ~20m."
echo "Check the github actions tab for the status of the release."

exit 0
