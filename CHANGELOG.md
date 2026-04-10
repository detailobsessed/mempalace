# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- version list -->

## v3.1.0 (2026-04-10)

### Bug Fixes

- --yes flag now skips room confirmation in init
  ([`caa1169`](https://github.com/detailobsessed/mempalace/commit/caa1169f0426676d79ad7ceaa3a8c18ea0ca82d3))

- Add explicit encoding="utf-8" to all file I/O calls
  ([`826c5de`](https://github.com/detailobsessed/mempalace/commit/826c5de08f7fc3bea27aa3c008752ede53a27705))

- Add limit=10000 safety cap to all unbounded ChromaDB .get() calls
  ([`9491ffa`](https://github.com/detailobsessed/mempalace/commit/9491ffa92bdb812d2938f5b1ef253f6a876b036c))

- Add text=True to mcp remove subprocess call
  ([`296d1cb`](https://github.com/detailobsessed/mempalace/commit/296d1cba3300e279875329570121b35f187e5597))

- Address Copilot review — remove unused imports, isolate HOME in tests, restore dev extra
  ([`cd8b245`](https://github.com/detailobsessed/mempalace/commit/cd8b245fdc069e4efa89a67b9e3a1da01ed02118))

- Address review feedback — cache cleanup, drawer hash, KG validation, test hang
  ([`8777430`](https://github.com/detailobsessed/mempalace/commit/87774300737b83df3d70313841d285a49a2918cf))

- Address review feedback — encoding, leading newline, mcp remove warning, test mocking
  ([`af21044`](https://github.com/detailobsessed/mempalace/commit/af21044f85fe26619bb5f39a5487291073e761f4))

- Address review — explicit parametrize ids, restore specific status assertion
  ([`7fa8b5f`](https://github.com/detailobsessed/mempalace/commit/7fa8b5f2d9562340a2315537e517c6eed1dc8ceb))

- Batch ChromaDB reads to avoid SQLite variable limit
  ([`0e77981`](https://github.com/detailobsessed/mempalace/commit/0e77981dec602989a61acfcd5a4addd1f484aedc))

- Cap diary_read query and update stale comment
  ([`161a0d1`](https://github.com/detailobsessed/mempalace/commit/161a0d12a2a3ff3ee884ecc1a82af2ede84b9a0e))

- CI failures — update workflow for uv migration, fix lint and format
  ([`96de23c`](https://github.com/detailobsessed/mempalace/commit/96de23cd974254d730dd0a69edaf943c4c0977da))

- Coerce MCP integer arguments to native Python int
  ([`8fbb617`](https://github.com/detailobsessed/mempalace/commit/8fbb6178dd73ba886525aabb8efefc62ad69bb7a))

- Convert spellcheck try/finally to monkeypatch, fix xdist master temp dir leak
  ([`602f90e`](https://github.com/detailobsessed/mempalace/commit/602f90e7dc71895b1860c40c2a175dfb9214436d))

- Correct REVIEW.md performance claims and PEP 758 terminology
  ([`d1ba27b`](https://github.com/detailobsessed/mempalace/commit/d1ba27b1d7aa32c1c94033962c9b205afb87090f))

- Enable SQLite WAL mode and add consistent LIMIT to KG timeline
  ([`21f2248`](https://github.com/detailobsessed/mempalace/commit/21f2248a3c41dae53ba596121ef83413a7c6cb8f))

- Ensure blank line before MemPalace section when CLAUDE.md lacks trailing newline
  ([`75002ef`](https://github.com/detailobsessed/mempalace/commit/75002efbffa1c715f2eccc3771bb9b2224e195dd))

- Guard against non-dict JSON in config loading
  ([`736e6a3`](https://github.com/detailobsessed/mempalace/commit/736e6a33cc8ed7dac1beae005392502179522cbc))

- Guard against non-dict stop_hook config value
  ([`0720cc1`](https://github.com/detailobsessed/mempalace/commit/0720cc1ca419777b8f2ea5b92d68fa562e58f515))

- Harden WAL logging and improve MCP server robustness
  ([`15832d8`](https://github.com/detailobsessed/mempalace/commit/15832d87708b98411c3384f5900b790766127a1e))

- Honest AAAK stats — word-based token estimator, lossy labels
  ([`39c14be`](https://github.com/detailobsessed/mempalace/commit/39c14be1136319f4471880c19a7510b3e5aee0f4))

- Isolate _CONFIG_DIR in all hook tests to prevent env leakage
  ([`aceef65`](https://github.com/detailobsessed/mempalace/commit/aceef6510ec7db826ea290c71efcdac06954236e))

- Mark MD5 as non-security in miner drawer ID generation
  ([`3a28175`](https://github.com/detailobsessed/mempalace/commit/3a2817505a49d44f05d9edd73f207dda70441953))

- Narrow bare except Exception to specific types where safe
  ([`312d380`](https://github.com/detailobsessed/mempalace/commit/312d380aab0f9192a823a380d1e0a2dcf7461939))

- Output compact JSON from hooks (single line for Claude Code)
  ([`828359d`](https://github.com/detailobsessed/mempalace/commit/828359da114b287f02b57783a26c4135c81c2bf7))

- Preserve CLI exit codes, log tracebacks, sanitize search errors, validate fixture
  ([`5ac4947`](https://github.com/detailobsessed/mempalace/commit/5ac4947d023f309e02faa3d86a1a0225e03cdabb))

- Remove dead code and duplicate set items in entity_registry.py
  ([`3c78e2f`](https://github.com/detailobsessed/mempalace/commit/3c78e2fbb5acff4f1e8a7612be5905c466419802))

- Repair command, split args, Claude export, room keywords
  ([`5e8a039`](https://github.com/detailobsessed/mempalace/commit/5e8a039e7c96fff1748a806e5644dbee188aa919))

- Replace Unicode separator in convo_miner.py for Windows compatibility
  ([`d214f6a`](https://github.com/detailobsessed/mempalace/commit/d214f6a85481e8ab16f974042f458824dfeb457b))

- Reset __init__ version, fix PSR v10 branch config, drop missing template_dir
  ([`0e7d4de`](https://github.com/detailobsessed/mempalace/commit/0e7d4de1bea1733a6e6ae24aae0984812ec5b57a))

- Resolve all ty type-checker errors across codebase
  ([`e863798`](https://github.com/detailobsessed/mempalace/commit/e863798a93103bd957fccef2a4b8121b5e3c9c04))

- Respect .gitignore during project mining
  ([`9b9daa9`](https://github.com/detailobsessed/mempalace/commit/9b9daa9b4b99ca5c74a037d47ced6597f354169f))

- Return validation errors as structured responses, fix conftest cache fallback
  ([`0e30f5a`](https://github.com/detailobsessed/mempalace/commit/0e30f5a1127bfbbdfb8e3def7f44829301b3dd99))

- Room detection checks keywords against folder paths
  ([`71fb66d`](https://github.com/detailobsessed/mempalace/commit/71fb66d687b61e45b67388a0f5ef23742dd89667))

- Sanitize error responses and remove sys.exit from library code
  ([`c9135aa`](https://github.com/detailobsessed/mempalace/commit/c9135aad67cf62a8e3bab2776f6570efe5dc9a76))

- Sanitize inputs in tool_kg_invalidate and tool_diary_read
  ([`1c83986`](https://github.com/detailobsessed/mempalace/commit/1c839864dc17437bd2e06fc1550a95a55c4372fc))

- Sanitize SESSION_ID in save hook to prevent path traversal
  ([`50239d4`](https://github.com/detailobsessed/mempalace/commit/50239d4b49931833ed42e4d17c6c38b0bee1e38c))

- Shell injection in hooks, Claude Code mining, chromadb pin
  ([`186bb2e`](https://github.com/detailobsessed/mempalace/commit/186bb2e3d1fb19a1dff66d51f34f833b87eef136))

- Stop hook mines transcript silently instead of blocking
  ([`37fb43c`](https://github.com/detailobsessed/mempalace/commit/37fb43c6b80b2b37a3b0f3cd752579d6e3be14b6))

- Support nested .gitignore rules during mining
  ([`c8c220d`](https://github.com/detailobsessed/mempalace/commit/c8c220d789a1d909c6593796e9f5d44fdb0f0c0a))

- Suppress WAL log exception in tool_diary_write
  ([`bbb6c1c`](https://github.com/detailobsessed/mempalace/commit/bbb6c1c9fc29cdc33a03a4f38b728f755fe2b786))

- Sync hook mining so statusMessage spinner is visible
  ([`0ff417d`](https://github.com/detailobsessed/mempalace/commit/0ff417d5b462f26813f599c95ce4680109c85f6c))

- Unify package and MCP version reporting
  ([`55152ce`](https://github.com/detailobsessed/mempalace/commit/55152ce476ead50b998d83acbebf460d05edd2e7))

- Update dialect tests for PR #147 stats API and remove unused fixture param
  ([`e5b3434`](https://github.com/detailobsessed/mempalace/commit/e5b3434e9b147ecc44a4a8429a98a5559b7aff74))

- Update dialect tests for PR #147 stats API and remove unused fixture param
  ([`b5a5855`](https://github.com/detailobsessed/mempalace/commit/b5a58557e3d3a8760c0fb9e895e6fa51c00f631a))

- Update dialect tests for PR #147 stats API and remove unused fixture param
  ([`6fa985e`](https://github.com/detailobsessed/mempalace/commit/6fa985eac2f86aff88f21b66fe35edf81f06611c))

- Update dialect tests for PR #147 stats API and remove unused fixture param
  ([`d3145e9`](https://github.com/detailobsessed/mempalace/commit/d3145e9a7b14e20da203edfcf0ff45ab0851e4b5))

- Update input prompt for entity confirmation in entity_detector.py
  ([`cfe8782`](https://github.com/detailobsessed/mempalace/commit/cfe878204e657015882831c7ff978d4569624dc7))

- **docs**: Correct test count, CI claims, project URLs, and upstream org
  ([`321c302`](https://github.com/detailobsessed/mempalace/commit/321c302362e8d780443745e025b084a95ed4cb04))

- **docs**: Remove incorrect license comparison — both repos are MIT
  ([`37f5860`](https://github.com/detailobsessed/mempalace/commit/37f58606ad0a419b042dbf5c1cb8f799defb2416))

### Chores

- Remove deprecated legacy shell hooks (DOT-424)
  ([`b096a34`](https://github.com/detailobsessed/mempalace/commit/b096a346859f6056015a00e280f9fff7db61c650))

- Restore hooks/ lost in copier src-layout migration
  ([`194ddb4`](https://github.com/detailobsessed/mempalace/commit/194ddb49b491bfe289d1a45a69a1c219b5ed3269))

- Tighten chromadb version range and add py.typed marker
  ([`541e9bd`](https://github.com/detailobsessed/mempalace/commit/541e9bd1ee880318b50237eaead1a4818052948b))

### Continuous Integration

- Activate semantic-release, reset to v0.0.1
  ([`376be3b`](https://github.com/detailobsessed/mempalace/commit/376be3be2f5b76b6d88001775ed6335627e035f7))

- Make link checker warn instead of fail
  ([`112f0dd`](https://github.com/detailobsessed/mempalace/commit/112f0dd6fe590010d57e1111542e74f1f5d8b7b7))

- Remove docs, issue-triage, and release workflows for fork
  ([`e271e68`](https://github.com/detailobsessed/mempalace/commit/e271e68b59a3b6cbbf8b5ea3de2abe4ddebee368))

- Set use_semantic_release to true in copier answers
  ([`ee42ccf`](https://github.com/detailobsessed/mempalace/commit/ee42ccf339b2c8c9346a372e6f0bff2388699627))

### Documentation

- Add beginner-friendly hooks tutorial for issue #20
  ([`b3c48d0`](https://github.com/detailobsessed/mempalace/commit/b3c48d0775bff50210dd356e50085cc415dba198))

- Add Gemini CLI setup guide and integration section
  ([`2df6c1b`](https://github.com/detailobsessed/mempalace/commit/2df6c1b121bc94c707954c1552a79b20ae481ee7))

- Add Gemini to MCP header in README
  ([`ca2549d`](https://github.com/detailobsessed/mempalace/commit/ca2549da5aeca4ffe9576ca59e22fa0f745dc53b))

- Add installation guide and behavioral differences section
  ([`1a34286`](https://github.com/detailobsessed/mempalace/commit/1a3428650ad2f22eb2aaa98915758d56bd292a75))

- Add REVIEW.md to guide AI code reviewers
  ([`23d6e6d`](https://github.com/detailobsessed/mempalace/commit/23d6e6dd68995564afea52585d404282944a2076))

- Add versioning and version reset to differences section
  ([`22321d4`](https://github.com/detailobsessed/mempalace/commit/22321d4282f800811a728cd2ebf03270968a0369))

- Align MCP setup examples with shipped server
  ([`1557eaa`](https://github.com/detailobsessed/mempalace/commit/1557eaa2f59b0d6cf0e68c25ea37608dea86c895))

- Overhaul README for fork — focus on what changed vs upstream
  ([`2370e8e`](https://github.com/detailobsessed/mempalace/commit/2370e8e11375fe07986a7635a4a7079af309bed6))

- Streamline readme — drop stale numbers, add template credit
  ([`c89c3c5`](https://github.com/detailobsessed/mempalace/commit/c89c3c5ac9bb127a8ddc264837fb710bcd427ba0))

- Tone down README — experimental fork, not upstream replacement
  ([`4b25357`](https://github.com/detailobsessed/mempalace/commit/4b253578612588ceb4e345925e7cd88c7a7cd870))

- Update REVIEW.md conventions for sync mining, add hook logs to CLAUDE.md
  ([`6ccdfca`](https://github.com/detailobsessed/mempalace/commit/6ccdfca06e99aeb4de36cb59d532994dee1bcc72))

- Updates readme
  ([`54d6d0d`](https://github.com/detailobsessed/mempalace/commit/54d6d0d7739b22c237729427284526eb45ffc835))

### Features

- Add Claude Code plugin structure with uv-based Python resolution
  ([`c69fd67`](https://github.com/detailobsessed/mempalace/commit/c69fd673078f20180e250ab1d4ccf57c164cbb25))

- Add install and repair script for claude code
  ([`ac4547d`](https://github.com/detailobsessed/mempalace/commit/ac4547db47599c329a3211def4c051fa790d1738))

- Add OpenAI Codex CLI JSONL normalizer
  ([`d4e1945`](https://github.com/detailobsessed/mempalace/commit/d4e1945f77f6c43c0f3d9d157a08bfe74795b345))

- Add scripts/setup_claude.py for one-shot Claude Code integration
  ([`b1be49d`](https://github.com/detailobsessed/mempalace/commit/b1be49d82beb2fa499860db0ceb9615c05434e4b))

- Add statusMessage to hook config for visible spinner during save/compact
  ([`cf130bd`](https://github.com/detailobsessed/mempalace/commit/cf130bdee0d7db32504d7807cbf851f6f43c685a))

- Align with latest upstream changes -- v3.1.0
  ([`34f9594`](https://github.com/detailobsessed/mempalace/commit/34f9594217550e21a4ba166cd34965f302f106a0))

- Apply copier-uv-bleeding template, migrate to src layout, expand test suite
  ([`4e43a16`](https://github.com/detailobsessed/mempalace/commit/4e43a16277a7f6d90847aac8a9a3ae3580d44301))

- **setup**: Auto-install from fork as editable uv tool
  ([`f1c7256`](https://github.com/detailobsessed/mempalace/commit/f1c7256d04a7091f0a3f57476a71f8d7b8e5a1cf))

### Refactoring

- Audit test suite — parametrize duplicates, deduplicate fixtures, add xdist
  ([`1f554bd`](https://github.com/detailobsessed/mempalace/commit/1f554bd33fe202d178b84596ef70a44a244fa902))

- Consolidate split known-names config loading
  ([`0808ad9`](https://github.com/detailobsessed/mempalace/commit/0808ad96c29d5acb9fd3b465025ea201711bd28d))

### Testing

- Add WAL mode and entity timeline limit assertions
  ([`b45bff9`](https://github.com/detailobsessed/mempalace/commit/b45bff9db189ee1f7e412e4a61257e089b04819d))

- Expand coverage from 20 to 92 tests, migrate to uv
  ([`72c548b`](https://github.com/detailobsessed/mempalace/commit/72c548b72916385c87fc61835ea2c084cf93aa61))

- Improve coverage from 82% to 86% to pass fail-under=85 threshold
  ([`180f9cc`](https://github.com/detailobsessed/mempalace/commit/180f9cc82413ac69a32768435242e53ab9ffccae))
