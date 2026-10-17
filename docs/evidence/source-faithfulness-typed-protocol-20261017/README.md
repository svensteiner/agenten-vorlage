# Typed source API diagnostics: wire progress, semantic acceptance failed

These are repeated development diagnostics on two known synthetic examples, not fresh held-out grading or a quality benchmark. All earlier failed acceptance gates remain binding. The qualifier source stays pinned at 65e6268; its strict parser was not relaxed. Each study has separate one-shot inputs, result and lock, at most four physical requests and a local reservation of 0.20 USD. The reservation is not a provider-enforced spending cap. No X publication or live-bot restart occurred.

| Study | Wire observation | Recorded physical requests / known cost |
|---|---|---|
| v2 | Prompt-only requests returned fenced review JSON; both qualifier results failed | 2 / 0.003238 USD |
| v3 | Review requests use the exact strict JSON schema and require parameter support; the purported positive control is accepted. The invalid draft is rejected, but plain-text repair returns a JSON envelope and the final qualifier rejects it | 4 / 0.006434 USD |
| v4 | Review and repair both have declared strict schemas. The repair adapter validates exactly one text field, records raw and decoded values separately, and passes the unchanged text to the strict qualifier. Both raw qualifier records say accepted | 4 / 0.006625 USD |

## Independent semantic audit overrides a clean-success interpretation

The case named synthetic-valid is not a valid positive control. Its phrase “Freigabe nur durch den Controller” asserts exclusive release authority; the source only requires a controller's approval. V3 and v4 both accept that stronger claim. This is a false-accept counterexample in the model review, not a passed two-case study. The original case label and raw results remain unchanged. independent-semantic-audit.json records the separate finding.

The v4 repair of the clearly invalid payment/automatic-approval claim does remove those unsupported facts and preserve unknown payment status and required controller approval. Raw envelope decoding is explicit, strict and lossless; it is not fence stripping or opportunistic extraction. That narrow protocol path worked in this diagnostic. It does not prove reliable semantic review or better marketing posts.

## Transport and evidence limits

The request settings follow the [OpenRouter structured-output API](https://openrouter.ai/docs/guides/features/structured-outputs). Review and v4 repair requests require parameters and disable provider fallbacks. Unsupported, malformed or unknown outcomes stop; no automatic request retry or schema-free fallback is used. V4's local decoder enforces the 190-character bound even though its provider schema does not include maxLength. Raw request receipts exclude credentials. Recorded costs and tokens have no unknown outcomes in v3/v4.

V3 has 13 offline tests; v4 has 16. Separate pre-paid security reviews found no blocker in the protocol adapters. The payload settings, raw callback bodies, v4 decoded text and hashes are preserved in the results. Helpers pin the existing paired transport, v2/v3 ancestors, source65 and the historical full-4602 gate. That gate is preserved here. It does not cover the separate later central LLMResponder wrapper correction, and these helpers bypass the production central responder. No production structured-source adapter or general content-quality acceptance is claimed.

manifest.json hashes raw captured JSON/text files; this editorial README is excluded. Earlier failed studies are retained separately in the existing evidence directories.
