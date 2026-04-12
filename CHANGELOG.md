# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- version list -->

## v0.0.10 (2026-04-12)

### Bug Fixes

- MCP null args hang, repair infinite recursion, OOM on large files
  ([#36](https://github.com/detailobsessed/mempalace/pull/36),
  [`f787c57`](https://github.com/detailobsessed/mempalace/commit/f787c572ee677499b229c55918f27037d033a6a6))

- Mitigate system prompt contamination in search queries
  ([#34](https://github.com/detailobsessed/mempalace/pull/34),
  [`9b61b80`](https://github.com/detailobsessed/mempalace/commit/9b61b80d732594e43c1c9948c5ed23c251a84a56))


## v0.0.9 (2026-04-12)

### Bug Fixes

- Prevent HNSW index bloat — add() to upsert() in convo_miner, add repair/dedup modules
  ([#33](https://github.com/detailobsessed/mempalace/pull/33),
  [`30d6236`](https://github.com/detailobsessed/mempalace/commit/30d6236da63ba5bb2a93055bc0fcdcadfab4b875))


## v0.0.8 (2026-04-12)

### Bug Fixes

- Purge stale drawers before re-mine to avoid hnswlib segfault
  ([#32](https://github.com/detailobsessed/mempalace/pull/32),
  [`4704ff3`](https://github.com/detailobsessed/mempalace/commit/4704ff3a3ae900df63881948aea104b91f4ecc8b))

### Chores

- Update project template to 0.33.11 ([#35](https://github.com/detailobsessed/mempalace/pull/35),
  [`3334fac`](https://github.com/detailobsessed/mempalace/commit/3334fac091a56c8b27d735049d85e16e786e9d17))


## v0.0.7 (2026-04-12)

### Bug Fixes

- Security hardening — sha256 IDs, transaction safety, file guards, permissions
  ([#31](https://github.com/detailobsessed/mempalace/pull/31),
  [`b41a76d`](https://github.com/detailobsessed/mempalace/commit/b41a76ddf6d929de6020b204bc38928783346ffb))

### Chores

- Update documentation and memories ([#30](https://github.com/detailobsessed/mempalace/pull/30),
  [`b95f085`](https://github.com/detailobsessed/mempalace/commit/b95f085b68005a4a4ce8a3dc05c4e7299c0a5346))


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
