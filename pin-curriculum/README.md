# PIN Curriculum Schema v2.2

Project: **Chinese Learning** \
Module: **PIN pinyin curriculum**

This package is a standalone implementation of PIN Schema v2.2.

## Structure
- `schema/`: five JSON Schemas (manifest, course, Atlas entry, exercise, translation).
- `data/manifest.json`: fixed PIN-01–PIN-19 curriculum index and status counters.
- `data/courses/`: 19 placeholders, explicitly marked `not_imported`.
- `data/atlas-vocabulary.json`: intentionally empty until the authoritative Pinyin Town Atlas entries are entered.
- `scripts/`: generator and independent validators.
- `tests/`: regression checks.
- `reviews/`: first-round register, Atlas source index, syllable-structure coverage matrix, PIN-14—PIN-17 dependency review, six-language terminology audit, seven-rule six-language pronunciation audit, and PIN-17 Atlas spelling-rule matrix.

## Rules
- Baseline locales: zh-CN, en, de, fr, es, it. Additional BCP-47 locales may be added.
- `not_imported` course placeholders must have `localizedContent: null`; no translations or Atlas entries are fabricated.
- Course review is nested; Manifest review status is flat. Validators compare both.
- Pending reviews require a null timestamp. A completed historical review may have a null timestamp only when its notes explain the history.
- Approved courses require accepted status and all four reviews completed.
- Atlas source wording is authoritative; validators do not rewrite source material.
- Review JSON files distinguish verified source facts, outline-level structural mappings, and items that still require the missing full course text. No placeholder is treated as an accepted lesson.
- Generator refuses to overwrite any existing course file and rolls back only files/directories created in its own failed run. It never edits the Manifest.

## Install and run
```bash
npm install
npm run validate:pin
npm run validate:atlas
npm test
```

The validators print machine-readable JSON and exit non-zero on errors. The generator is for a fresh project with all 19 course files absent.

Run the installer from the repository root with `bash pin-curriculum/INSTALL-IN-CODESPACES.sh`, or from inside this directory with `bash INSTALL-IN-CODESPACES.sh`. It operates only in this package directory.
