# Validation strategy

A trustworthy release needs two test layers.

## Deterministic tests

These run without a model and verify source hashing, index behavior, character path safety, evidence-ID validation, and parser behavior.

## Live-model regression suite

Run `python scripts/live_regression.py` while llama-server is available. The suite includes direct rules questions, derived calculations, prompts designed to lure the model into using older/supplemental knowledge, and deliberately unsupported options.

Do not treat a single successful demo as proof of reliability. Add every observed failure to the regression corpus before changing prompts or retrieval behavior.
