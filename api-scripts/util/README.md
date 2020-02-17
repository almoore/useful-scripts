Util Scripts
============

# Purpose #

These scripts are most used to maintain or do configuration to various systems
over their various APIs.

# Usage #

## add-salt-repo-pipeline ##

This scipt is mainly there to string together all the steps needed to add an
new salt repo pipeline. The steps for this include:

1. Create or just clone the repo if it already exists
2. Ensure that the dev branch exits
3. Ensure that the needed files are in the repo ex `name` `version` and
   `Jenkinsfile`
4. Conform the repo to have the the branch permisions and pull request settings
   the same as the others repos in the salt project.
5. Add a multi-branch pipeline job to the devopsjenkins server that will build
   for only the branches `dev`, `qa`, `beta` and `prod`
6. Add hooks to the repo that notify jenkins of changes rather than having it
   poll for changes.

## bitbucket-create-repo.py ##

Create or make sure that a repo exists. There is also an option to delete a
repo. The delete option is there to ensure that a repo is able to be recreate.

## bitbucket-update-permissions.py ##

Conform the repo to have the the branch permisions and pull request settings
the same as the others repos in the salt project.

## prod_default_reviewers.json ##

Used to set and maintain the default reviewers for the repos on the prod branch.

## ensure_called.sh ##

This is an example script that could be used for callback and cleanup

## ensure_installed.sh ##

Similar to ensure_called.sh but meant for installation.

## git-remote-dirs ##

Get the remote directories that are in a given repo on bitbucket.

**NOTE:** This only works for the repos / projects that the saltmaster users has access
to at this time.

## git-remote-files ##

Get the remote files that are in a given repo on bitbucket.

**NOTE:** This only works for the repos / projects that the saltmaster users has access
to at this time.

## mirror_update.py ##

This is used to mirror all the repos in a given project. Userful for backing up
repo data or migrating a repo from one location to another.
