# Protected instructor original inspection

The instructor source archive can display two explicitly selected original scenario
definitions side by side. Open an explanation, expand **Inspect original source
versions side by side**, choose each source and load it. Search spans the complete
archive, showing up to 50 matches plus the selected source per side. Searching does
not replace the selected source or fetch its contents.

The display preserves original UTF-8 text, whitespace and duplicate JSON keys.
The browser verifies the returned byte count and SHA-256 before displaying text;
the service also verifies the canonical-source, migrated explanation and archive
pins. Each source has a 4 MiB limit. Contents are rendered as text, never HTML.
The selection identifies archived definitions, not an asserted predecessor chain,
active scenario or independent corroborating source. Bound engagement Keys and
previous archives remain unchanged.

Changing a selection clears that side and cancels its request. A viewer, engagement,
revision, permission, scope or source-context change remounts the protected archive
workspace and clears displayed originals. Failed requests leave no previous content
under a new selection. There is no automatic original fetch, download, comparison
judgment, learner release or persistent browser copy.

## Service contract

`GET /api/engagements/{engagement_id}/instructor-key/{scenario_id}/original`
requires current instructor membership. The response contains the unbound library
context, exact archive/key/raw/canonical hashes, scenario ID, byte count, media type
and base64 original bytes. No server filesystem path is supplied by the caller or
returned in the original response. Files are bounded, private, regular and without
symbolic or hard links. Source/archive integrity and instructor membership are
checked again before return. Responses use `Cache-Control: no-store, private`.

An `ORIGINAL` entry in the private instructor access journal records success or
failure and exact pins for successful retrieval. It is an access receipt, not proof
that the user read or understood the definition. Retrieval does not append formal
audit work, change company records, invoke a model or grant learner visibility.

This implements original-byte inspection within IK-03. Causal validation,
professional calibration and owner usability acceptance remain separate work.
