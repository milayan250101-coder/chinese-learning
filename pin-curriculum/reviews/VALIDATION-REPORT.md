# PIN Schema v2.2 — Validation report

Date: 2026-11-17 \
Project: Chinese Learning / PIN pinyin curriculum

## Checks completed

- All 5 JSON Schema definitions pass Draft 2020-12 meta-schema checks using Python `jsonschema` 4.26.0.
- `data/manifest.json`: 0 schema validation errors.
- All 19 course placeholder JSON files: 0 schema validation errors.
- Manifest-to-Course parity for title, content status, acceptance status, and all four review statuses: 0 mismatches.
- `data/atlas-vocabulary.json` remains an empty array; no Atlas entries have been fabricated.
- All 34 JSON files in the package parse successfully.
- A fresh Python `jsonschema` 4.26.0 run with a local registry for the package schema `$ref` values validated the Manifest and all 19 course placeholders with 0 errors; all 5 schemas passed Draft 2020-12 meta-schema checks.
- Atlas review counts: 92 vocabulary occurrences, 192 syllable occurrences, 122 distinct tone-stripped spellings, 30 candidate medial structures (22 consonant-initial and 8 zero-initial y/w forms); ten previously labelled “extended finals” are clarified as medial-bearing compound-final forms, not ten independent basic finals, and 13 whole-syllable-recognition types matched across 31 occurrences.
- User-confirmed Atlas English meanings remain marked as confirmed and are not listed as translation issues: ATLAS-S02-03 and ATLAS-S03-04.
- PIN-17 spelling-rule source matrix: iu→iou (5), ui→uei (3), written un (4), j/q/x u-family→ü-family (5), zero-initial y/w (21), and apical i (19) Atlas occurrences mapped; lesson-text verification remains pending.
- Six-language pronunciation rules: 7 rules / 42 language fields checked; all 42 are present and 7/7 conceptual alignment checks are marked aligned. This is not native-speaker sign-off of full course prose.
- Atlas issue register duplicates were consolidated to three distinct source observations; the two user-confirmed translation items remain clear of issue flags.
- First-round review baseline remains 19/19, including PIN-02. Formal acceptance remains 0/19.

## Checks not completed

- `npm install` did not complete in this environment (timed out). AJV and `ajv-formats` are not installed here.
- `node tests/run-tests.mjs` was attempted. The runner reported 26 blocked cases because `ajv` could not be imported (`ERR_MODULE_NOT_FOUND`); T10 only checked that a validator invocation did not mutate files, and its validator subprocess also could not load AJV. Therefore no functional AJV regression case is counted as passed, and T01–T27 remain **blocked / not executed successfully**.
- A complete metadata listing of the saved Library returned 73 files; PIN/Pinyin-named items were the v2.2 packages, audit records, localization standard, and Atlas PPTX. Targeted content searches likewise surfaced prior audit records but no separate complete PIN-01—PIN-19 lesson source text. The recent CL-06 and CL-22 lesson dumps are CL curriculum files, not PIN lessons, so they were not imported. The course placeholders therefore remain `not_imported`.
- The package has not been installed or modified in the user's Codespaces repository.
- Full lesson text is not imported; course-by-course systematic, Atlas, cross-course and six-language sign-off remain pending.

## Interpretation

The Python JSON Schema check is an independent structural verification, not a replacement for the project's AJV runtime tests. No claim is made that npm tests, Codespaces integration, lesson-content review, or formal course acceptance have passed.
