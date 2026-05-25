---
name: migrate-to-py312
description: Migrate a Netskope Stork-Debian or Debian component from Python 3.8 or 3.10 to Python 3.12. Auto-detects which of the four migration paths applies (Stork-vs-Debian × py38-vs-py310), edits the affected files in place (Makefile, tox.ini, Dockerfile-2004, Dockerfile-2004-fips), and prints the exact Docker commands the user must run themselves to regenerate `requirements.txt` and `app-env-py312.yaml`. Source of truth is the Confluence page "How to migrate to Python3.12 Stork and Debian Components" (page 7850558381). Use this skill whenever the user mentions migrating to Python 3.12, upgrading from py38/py310, "py312 migration", `app-env-py312.yaml`, "stork debian python upgrade", or asks to bump `PYTHON_VERSION` to py312 in a Netskope component.
disable-model-invocation: false
allowed-tools: Read Edit Write Bash Glob Grep AskUserQuestion
---

You're helping the user migrate a Netskope component from Python 3.8 or 3.10 to Python 3.12. The migration follows the official guide at https://netskope.atlassian.net/wiki/spaces/PE/pages/7850558381 — there are **four distinct paths** depending on the component type and source version. Detect which one applies, then edit the right files. The two regeneration commands (uv pip compile, conda-env-gen) require Docker images that may not be available in this environment, so you print those commands for the user to run; you handle every other file edit.

## Step 1 — Detect the migration path

Run this detection logic at the start of every invocation. The component's repo has signals you can use:

1. **Stork vs. Debian.** Stork components have one or more `Dockerfile-2004*` files and a Makefile that includes `stork-build.mk` or sets `STORK_COMPONENT_NAME`. Debian-only components don't have those Dockerfiles and don't reference Stork in the Makefile.
2. **Source Python version.** Look for `app-env-py38.yaml` or `app-env-py310.yaml`, and `PYTHON_VERSION ?= py38` / `py310` in the Makefile, and `envlist = py38` / `py310` in `tox.ini`.

If the signals conflict or are missing, ask the user via `AskUserQuestion` which path applies — don't guess. Once you've decided, **state the detected path back to the user in one sentence** before making any edits, so they can correct you.

The four paths and their reference files:

| Path | Reference file |
|---|---|
| Stork-Debian: py310 → py312 | `references/stork-py310-to-py312.md` |
| Stork-Debian: py38 → py312 | `references/stork-py38-to-py312.md` |
| Debian-only: py310 → py312 | `references/debian-py310-to-py312.md` |
| Debian-only: py38 → py312 | `references/debian-py38-to-py312.md` |

Read **only the reference for the detected path**. Each file contains the exact diffs and commands for that path.

## Step 2 — Apply the file edits

Following the matched reference file:

- Edit `Makefile` (always).
- Edit `tox.ini` (always).
- Edit `Dockerfile-2004` and `Dockerfile-2004-fips` if the path is Stork-Debian.
- Check for `pyproject.toml`. If the component only has `setup.py` and no `pyproject.toml`, **create one** with the 3-line content from the reference file. Without it, the Drone wheel build fails on py312 with `Backend 'setuptools.build_meta:__legacy__' is not available`. If `pyproject.toml` already exists, leave it alone.
- Plan to delete the old `app-env-py3{8,10}.yaml` after the user has generated the new `app-env-py312.yaml` (don't delete it yet — the user needs the old one as a reference until the new one is in place; tell them to delete it as part of the post-Docker step).

For each edit, **match the diff in the reference file as closely as the surrounding code allows**. The diffs in the reference were captured from real PRs; if the user's file differs (e.g., different component name, extra lines, slightly different formatting), preserve their structure and apply only the semantic change (e.g., `py310` → `py312`, `pythonpkg-py3.mk` → `conda-build.mk`). Don't reformat unrelated lines.

## Step 3 — Print the Docker commands

The user has to run two Docker commands themselves: one to regenerate `requirements.txt` (via `uv pip compile` in a `develop-uv-python3.12-ubuntu2004-current` image), and one to generate `app-env-py312.yaml` (via the `conda-env-gen-ubuntu2404-current` image). The exact command shapes are in each reference file.

When you print these for the user, **substitute the real values** so they can copy-paste verbatim:

- `$(pwd)` / `/path/to/repo` → the absolute path of the repo root the user is working in
- The relative path passed via `-r` to `conda-env-gen` → the actual path to the component's `requirements.txt` from the repo root (e.g., `repo/components/<their-component>/requirements.txt`)

You will **not** auto-fetch the latest tool image tags — these are hosted at `https://tool-ep-pokeball.netskope.io/` which requires browser auth. Instead, in your output:
- Use the example tags from the reference file as placeholders (e.g., `26.84.3019` for uv, `26.85.3004` for conda-env-gen).
- Tell the user to visit the pokeball URL and replace the tag with the latest if they want — but the placeholders are usually recent enough to work.

## Step 4 — Hand back a checklist

After your edits, print a short checklist of what the user needs to do next, in order:

1. Run the `uv pip compile` Docker command (you printed it).
2. Run the `conda-env-gen` Docker command (you printed it).
3. Delete the old `app-env-py3{8,10}.yaml`.
4. Build and test locally (`tox` or the project's usual build).
5. Confirm CI checks pass on the PR.

Also list the success criteria from the guide so the user can self-verify:

- `Makefile` has `PYTHON_VERSION ?= py312`
- `Makefile` exports `PIP_INDEX_URL=...org-external-pypi/simple` and `SETUPTOOLS_USE_DISTUTILS=local` (otherwise Drone wheel build fails finding `setuptools>=70.0.0`)
- `app-env-py312.yaml` exists (generated by tool, not hand-edited)
- Old `app-env-py3{8,10}.yaml` deleted
- `requirements.txt` regenerated
- `tox.ini` updated to `py312`
- `pyproject.toml` exists with `[build-system]` declaring `setuptools.build_meta` (created if was missing)
- For Stork: Dockerfiles use `cloud-python3-py312-2004:<tag>` base image and `python3.12 -m pip` for installs

## Don'ts

- **Don't manually edit `app-env-py312.yaml`.** It must be generated by `conda-env-gen`. If the user asks you to write its contents, refuse and explain why — the YAML has package hashes and channel ordering that the tool resolves correctly and humans don't.
- **Don't use the `latest` Docker tag.** The Netskope artifactory doesn't publish a `latest` tag for these images. Always use a date-versioned tag.
- **Don't mix Python 3.10 and 3.12 base images** in the same Dockerfile or the same build.
- **Don't forget the FIPS variant.** For Stork components, `Dockerfile-2004` and `Dockerfile-2004-fips` must both be updated. Treat skipping the FIPS file as a hard failure.
- **Don't run the regeneration Docker commands yourself.** Even if Docker is available, the user owns this step — they need to verify the resulting files are reasonable before committing. Print the commands; let them run them.

## Examples of when to trigger

- "Migrate this component from py310 to py312"
- "Upgrade nsdyncleanup to Python 3.12"
- "I need to bump PYTHON_VERSION to py312"
- "Help me follow the py3.12 migration guide"
- The user opens a Stork component repo and asks "what do I need to change for the python upgrade?"
