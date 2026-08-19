# Upgrade from v1.1 to v1.5

v1.5 is designed as a replacement checkout rather than an in-place database migration.

1. Back up any real character YAML files from `data/characters/`.
2. Extract the v1.5 package into a new repository directory.
3. Copy character YAML files into the new `data/characters/` directory.
4. Copy or recreate `.env` from `.env.example`.
5. Run `./scripts/bootstrap.sh`.
6. Run `./scripts/release_check.sh`.
7. Confirm `python -m archie.cli doctor` shows the expected endpoint/model.
8. Run `./scripts/run_regression.sh` and review the generated Markdown report.

Do not copy the old SQLite index. v1.5 should rebuild it from the pinned SRD.
