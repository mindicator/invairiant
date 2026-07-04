# Publishing `invairiant` to PyPI

The package is already **production-grade** (the wheel/sdist bundle the framework
the CLI needs; `pip install` works outside a checkout — proven by the CI
packaging smoke). The only remaining step is the **upload**, which needs a PyPI
account and is done by the maintainer.

**Publish the same version that was released.** PyPI versions are **immutable** —
you cannot re-upload or overwrite `X.Y.Z`. So publish only after the normal
release flow has produced a tag + green CI + GitHub release (see
[CONTRIBUTING.md](../CONTRIBUTING.md#releasing)), and always **build from the
exact tag** so the PyPI artifact matches the release. A botched upload means
bumping to the next patch and cutting a new release.

First, confirm the name is yours or free: <https://pypi.org/project/invairiant/>.

---

## Path A — manual (twine + API token)

Fastest for the first publish.

1. **Accounts** — create a [PyPI](https://pypi.org/account/register/) account (and
   a [TestPyPI](https://test.pypi.org/account/register/) one for a dry run);
   enable 2FA.
2. **API token** — PyPI → *Account settings → API tokens → Add token*. For the
   very first upload scope it to *entire account* (the project doesn't exist
   yet); after it exists, delete that token and create a **project-scoped** one.
   Username for uploads is always `__token__`; the password is the token string.
3. **Build from the tag** (clean tree, both artifacts):
   ```bash
   git checkout v0.2.3            # the released tag
   rm -rf dist
   python -m pip install --upgrade build twine
   python -m build               # → dist/invairiant-0.2.3{.tar.gz,-py3-none-any.whl}
   ```
4. **Pre-flight** — validate metadata, then rehearse on TestPyPI:
   ```bash
   twine check dist/*
   twine upload -r testpypi dist/*
   # verify the TestPyPI artifact installs & runs in a CLEAN venv:
   python -m venv /tmp/tv && /tmp/tv/bin/pip install \
     --index-url https://test.pypi.org/simple/ \
     --extra-index-url https://pypi.org/simple/ invairiant
   ( cd /tmp && /tmp/tv/bin/invairiant --help )
   ```
5. **Publish to real PyPI**:
   ```bash
   twine upload dist/*           # username __token__, password = your token
   ```
6. **Verify from real PyPI** in a fresh venv, outside any checkout:
   ```bash
   python -m venv /tmp/pv && /tmp/pv/bin/pip install invairiant
   cp examples/minimal-webapp/invairiant.config.yml /tmp/cfg.yml
   ( cd /tmp && /tmp/pv/bin/invairiant validate-config cfg.yml )   # expect: OK
   ```
7. **Re-scope the token** to the `invairiant` project; delete the account-wide one.

---

## Path B — automated, recommended (GitHub Actions Trusted Publishing, no token)

No secrets stored: PyPI trusts the repo's workflow over OIDC, and publishing
happens automatically when a GitHub release is cut (the release-gate already
guarantees CI was green on the tag).

1. **One-time PyPI setup** — PyPI → *your project → Publishing* (or, before the
   project exists, *Account → Publishing → Add a pending publisher*). Add a
   **GitHub** trusted publisher: Owner `mindicator` · Repository `invAIriant` ·
   Workflow name `publish.yml` · Environment `(Any)`. (For defense-in-depth you
   can instead create a protected `pypi` GitHub environment, add
   `environment: pypi` to the job, and scope the publisher to it.)
2. **The workflow already exists**:
   [`.github/workflows/publish.yml`](../.github/workflows/publish.yml) — OIDC
   (`id-token: write`), builds sdist + wheel, `twine check`, then
   `pypa/gh-action-pypi-publish`. No token, no `environment` (matches the
   `(Any)` publisher).
3. **First publish** — the workflow must exist on the ref you run. A GitHub
   release *already published* before the workflow existed will not retrofire
   `release: published`, so publish the first version by hand: Actions → *Publish
   to PyPI* → **Run workflow** on `main` (its `pyproject` version is the one that
   ships). Future releases auto-publish: `gh release create` fires
   `release: published`, which checks out the tag and uploads that version.

---

## After the first publish

- Update the README quickstart to prefer `pip install invairiant` over
  `pip install -e .`.
- Bump the badge/pin references to the published version as usual.
- The remaining distribution item in [ROADMAP.md](../ROADMAP.md) — the Marketplace
  listing for the Action — is independent of PyPI.
