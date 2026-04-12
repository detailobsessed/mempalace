# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- version list -->

## v0.0.6 (2026-04-12)

### Bug Fixes

- Close chromadb PersistentClient in test fixtures to prevent ResourceWarning
  ([#29](https://github.com/detailobsessed/mempalace/pull/29),
  [`04c6ffb`](https://github.com/detailobsessed/mempalace/commit/04c6ffbb897c09f3db9040f109749a213fadb3c5))

### Chores

- Add dev-reload script for reinstalling CLI locally
  ([`33bc098`](https://github.com/detailobsessed/mempalace/commit/33bc09826aff3f8161055cec03a1fc3f5503f216))

- Sync uv.lock with v0.0.5
  ([`cbb56fd`](https://github.com/detailobsessed/mempalace/commit/cbb56fd6976a9f945a8f44eacf0f6c18887217dd))

- **plugin**: Add local dev docs, reset marketplace version to 0.0.1
  ([`5a7a082`](https://github.com/detailobsessed/mempalace/commit/5a7a082ffff4a42a8683d11d50754a1c9a29466d))


## v0.0.5 (2026-04-12)

### Bug Fixes

- Filter hooks at command level instead of entry level
  ([`0c65a18`](https://github.com/detailobsessed/mempalace/commit/0c65a18d7cc9899cb32e61903386c8bee8124187))

### Chores

- Clean up setup script, restore tests, add hook verification
  ([`d572e12`](https://github.com/detailobsessed/mempalace/commit/d572e1289728dc79a0032e3d17831e76c1c27759))


## v0.0.4 (2026-04-11)

### Bug Fixes

- **hooks**: Remove fork-only divergences, align with upstream behavior
  ([`04c3ad1`](https://github.com/detailobsessed/mempalace/commit/04c3ad13eb4fefd16ba50a1ea9a1cce5e4c17bb0))

- **hooks**: Remove opinionated health checks from hooks and MCP status
  ([`161fd9d`](https://github.com/detailobsessed/mempalace/commit/161fd9db668d9613cda87d737ad073ecc24ab812))

- **hooks**: Revert sync mining, restore stop-hook blocking, add statusline notifications
  ([`2911842`](https://github.com/detailobsessed/mempalace/commit/29118428872d28dd90f6e07db169037db029748f))

### Documentation

- Update REVIEW.md and README.md for hooks divergence reduction
  ([`6e345d4`](https://github.com/detailobsessed/mempalace/commit/6e345d49727fa4611880bc46f8d4df91ee3d6e73))


## v0.0.3 (2026-04-11)

Fork version reset. See [README](README.md) for details on what changed from upstream.
