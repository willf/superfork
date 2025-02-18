# superfork

[![Release](https://img.shields.io/github/v/release/willf/superfork)](https://img.shields.io/github/v/release/willf/superfork)
[![Build status](https://img.shields.io/github/actions/workflow/status/willf/superfork/main.yml?branch=main)](https://github.com/willf/superfork/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/willf/superfork/branch/main/graph/badge.svg)](https://codecov.io/gh/willf/superfork)
[![Commit activity](https://img.shields.io/github/commit-activity/m/willf/superfork)](https://img.shields.io/github/commit-activity/m/willf/superfork)
[![License](https://img.shields.io/github/license/willf/superfork)](https://img.shields.io/github/license/willf/superfork)

Fork or sync a repo or user/organization's repos on GitHub to GitHub

## Features

- From the command line, you want to fork a repo to a account you control on GitHub

Let's say your GitHub username is `mona` and you want to fork the repo `willf/superfork` to your account

```bash
uv run superfork mona willf/superfork
```

- From the command line, you want to sync or fork _all_ of the repos of a user or organization to an account you control on GitHub

Let's say your GitHub username is `mona` and you want to sync all of the repos of the user `willf` to your account

```bash
uv run superfork mona willf
```

You can specify multiple users or organizations to sync

```bash
uv run superfork mona willf willf2 willf/superfork
```

Note: To avoid overwhelming GitHub (and thus hitting API limits), this program will only attempt to fork a repo every 30 seconds. If you are syncing a large number of repos, it may take a while to complete.

THe command has the following options:

- `--include-issues`: Include issues and comments (not working yet)
- `--sync`: Sync when repository already exists (default)
- `--no-sync`: Don't sync when repository already exists
- `--include-private`: Include private repositories (of course, you need to be able to _access_ the private repos)
- `--include-forks`: Include repositories which were originally forked (default: don't include)
- `--include-dot-github`: Include .github repository if found (default: don't include)
- `--dry-run`: Don't actually do anything, but check status of repositories
- `--without-sleeping`: Don't sleep between requests (default: sleep 30 seconds between fork requests)

Only use `--without-sleeping` if you just have a few forks to do, otherwise you may hit GitHub (undocumented) API limits.

## Installation

1. Install [uv](https://github.com/astral-sh/uv)
2. Clone this repo
3. Change to the repo directory

Currently, you need to run the command from the repo directory

```bash
$ cd superfork
$ uv run superfork --help
Usage: superfork [OPTIONS] TO [SOURCE]...

  [TO]: destination user or organization

  [SOURCE]: source user or organization, or repository (one or more)

  A valid GITHUB_TOKEN must be set in the environment, or in a .env file in
  the current directory, or in a .env file in the user's home directory.

  To get a GITHUB_TOKEN, see https://docs.github.com/en/authentication

Options:
  --include-issues      Include issues, pull requests, and comments
  --sync / --no-sync    Sync when repository already exists  [default: sync]
  --include-private     Include private repositories
  --include-forks       Include repositories which were originally forked
  --include-dot-github  Include .github repository if found
  --dry-run             Don't actually do anything, but check status of repositories
  --without-sleeping    Don't sleep between requests
  --help                Show this message and exit.

#
```
