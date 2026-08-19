# Upgrade: v1.5.1 to v1.6.0-rc.1

v1.5.1 is the locked baseline. v1.6.0-rc.1 is a development release and should be tested in a separate checkout before replacing v1.5.1.

## Recommended workflow

1. Keep the v1.5.1 repository unchanged as the rollback point.
2. Extract the full v1.6.0-rc.1 package into a separate directory.
3. Copy only your local `.env` and any character YAML files into the v1.6 checkout.
4. Run `./scripts/bootstrap.sh` and `./scripts/release_check.sh`.
5. Run the unchanged 38-question compatibility suite with `./scripts/run_regression.sh`.
6. Run `./scripts/run_epistemic_regression.sh`.
7. Compare results before promoting v1.6.

Do not merge source files piecemeal into the locked v1.5.1 checkout during development validation.
