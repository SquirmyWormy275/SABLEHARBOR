# Unadopted canonical encoder experiment — October 2

**Historical untracked experiment, not the active codec.** This is the exact [`canonical_encoder_experiment.py`](original/canonical_encoder_experiment.py) found beside a detached October 2 audit-suite worktree at commit `a07039ad4a361b5d45eb250565e9ad8827b6c0a0`. The local file timestamp is October 2 at 12:00 PDT; it is not an authoring certificate. The source was imported October 23.

The module's own header says the canonical node format remains unchanged. It sketches buffered insertion and native fragment boundaries, but it was not adopted or executed as the [current canonical codec](../../canonical_state_codec.py). This preservation makes no claim that the experiment is safe to run, performance-qualified, or part of a signed CLEAN or MESSY history.

[SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) records the exact 3,394-byte SHA-256 `102b1f195d4a82f7bcd7f655eb50dc8ffc3328643f6961ce6574543633d60af9` and Git blob ID. Run `python -I verify.py` in a fresh clone to check the bytes and syntax without importing or executing the experiment. The related untracked 16,400-byte compiled native helper is a generated binary with an exact opaque member in the Seagate recovery archives. Its rebuild and archive-family disposition remain open; that binary is not promoted to a source file by this history entry.

The original worktree is unchanged. No local path is cleared for deletion until this source is accepted and freshly retrieved, and the compiled binary has its own verified disposition.
