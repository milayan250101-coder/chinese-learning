#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(process.argv[2] ?? path.join(HERE, '..'));

const errors = [];
let filesChecked = 0;

const LANGS = ['zh', 'en', 'de', 'fr', 'es', 'it'];

function report(code, file, location, message) {
  errors.push({ code, file, path: location, message });
}

function readJson(rel) {
  filesChecked++;
  const file = path.join(ROOT, rel);

  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (e) {
    report(
      fs.existsSync(file) ? 'ATLAS_JSON_INVALID' : 'ATLAS_FILE_MISSING',
      rel,
      '$',
      e.message
    );
    return null;
  }
}

function addSchema(ajv, rel, schemaName) {
  const schema = readJson(rel);
  if (schema) {
    ajv.addSchema(schema, schemaName);
  }
}

function main() {
  const ajv = new Ajv2020({
    allErrors: true,
    strict: false
  });

  addFormats(ajv);

  addSchema(
    ajv,
    'schema/atlas-entry.schema.json',
    'atlas-entry.schema.json'
  );

  addSchema(
    ajv,
    'schema/atlas-occurrence-map.schema.json',
    'atlas-occurrence-map.schema.json'
  );

  const official = readJson('data/atlas-vocabulary.json');
  const mapping = readJson('data/atlas-occurrence-map.json');

  const officialEntries = Array.isArray(official) ? official : [];

  if (!Array.isArray(official)) {
    report(
      'ATLAS_DATA_NOT_ARRAY',
      'data/atlas-vocabulary.json',
      '$',
      'Official Atlas vocabulary must be an array'
    );
  }

  const officialIds = new Set();
  const officialValidator = ajv.getSchema('atlas-entry.schema.json');

  for (const entry of officialEntries) {
    if (!officialValidator(entry)) {
      for (const e of officialValidator.errors ?? []) {
        report(
          'ATLAS_SCHEMA_VALIDATION_FAILED',
          'data/atlas-vocabulary.json',
          e.instancePath || '$',
          `${e.keyword}: ${e.message}`
        );
      }
    }

    if (officialIds.has(entry.atlasId)) {
      report(
        'ATLAS_DUPLICATE_ID',
        'data/atlas-vocabulary.json',
        '/atlasId',
        `Duplicate official Atlas ID: ${entry.atlasId}`
      );
    }

    officialIds.add(entry.atlasId);

    for (const lang of LANGS) {
      const value = entry.translations?.[lang];

      if (typeof value !== 'string' || !value.trim()) {
        report(
          'ATLAS_TRANSLATION_MISSING',
          'data/atlas-vocabulary.json',
          `/${entry.atlasId}/translations/${lang}`,
          `Missing or blank ${lang} translation`
        );
      }
    }

    // courseReferences are PIN-CORE module references.
    // They are intentionally not checked against PIN-01 to PIN-19.
  }

  if (
    !mapping ||
    typeof mapping !== 'object' ||
    Array.isArray(mapping)
  ) {
    report(
      'ATLAS_OCCURRENCE_MAP_INVALID',
      'data/atlas-occurrence-map.json',
      '$',
      'Occurrence mapping must be an object'
    );
  }

  const mappingValidator = ajv.getSchema(
    'atlas-occurrence-map.schema.json'
  );

  if (mapping && !mappingValidator(mapping)) {
    for (const e of mappingValidator.errors ?? []) {
      report(
        'ATLAS_OCCURRENCE_SCHEMA_INVALID',
        'data/atlas-occurrence-map.json',
        e.instancePath || '$',
        `${e.keyword}: ${e.message}`
      );
    }
  }

  const occurrences = Array.isArray(mapping?.entries)
    ? mapping.entries
    : [];

  if (!Array.isArray(mapping?.entries)) {
    report(
      'ATLAS_OCCURRENCE_ENTRIES_INVALID',
      'data/atlas-occurrence-map.json',
      '/entries',
      'Occurrence entries must be an array'
    );
  }

  const occurrenceIds = new Set();
  const referencedOfficialIds = new Set();

  for (const occurrence of occurrences) {
    const occurrenceId = occurrence.atlasOccurrenceId;
    const officialId = occurrence.officialAtlasId;

    if (occurrenceIds.has(occurrenceId)) {
      report(
        'ATLAS_OCCURRENCE_DUPLICATE_ID',
        'data/atlas-occurrence-map.json',
        '/entries',
        `Duplicate occurrence ID: ${occurrenceId}`
      );
    }

    occurrenceIds.add(occurrenceId);

    if (officialId !== null && officialId !== undefined) {
      if (!officialIds.has(officialId)) {
        report(
          'ATLAS_OCCURRENCE_BROKEN_LINK',
          'data/atlas-occurrence-map.json',
          `/${occurrenceId}/officialAtlasId`,
          `Unknown official Atlas ID: ${officialId}`
        );
      } else {
        referencedOfficialIds.add(officialId);
      }
    }
  }

  for (const id of officialIds) {
    if (!referencedOfficialIds.has(id)) {
      report(
        'ATLAS_OFFICIAL_ENTRY_UNREFERENCED',
        'data/atlas-occurrence-map.json',
        '/entries',
        `Official vocabulary entry has no visual occurrence: ${id}`
      );
    }
  }

  const soccer = occurrences.filter(
    x => x.officialAtlasId === 'PTA-P09-053'
  );

  const scissors = occurrences.filter(
    x => x.officialAtlasId === 'PTA-P11-066'
  );

  if (officialEntries.length !== 79) {
    report(
      'ATLAS_OFFICIAL_COUNT_MISMATCH',
      'data/atlas-vocabulary.json',
      '$',
      `Expected 79 official entries, found ${officialEntries.length}`
    );
  }

  if (occurrences.length !== 92) {
    report(
      'ATLAS_OCCURRENCE_COUNT_MISMATCH',
      'data/atlas-occurrence-map.json',
      '/entries',
      `Expected 92 visual occurrences, found ${occurrences.length}`
    );
  }

  if (soccer.length !== 2) {
    report(
      'ATLAS_SOCCER_OCCURRENCES_MISMATCH',
      'data/atlas-occurrence-map.json',
      '/entries',
      `Expected 2 soccer occurrences, found ${soccer.length}`
    );
  }

  if (scissors.length !== 2) {
    report(
      'ATLAS_SCISSORS_OCCURRENCES_MISMATCH',
      'data/atlas-occurrence-map.json',
      '/entries',
      `Expected 2 scissors occurrences, found ${scissors.length}`
    );
  }

  const result = {
    tool: 'validate-atlas',
    schemaVersion: '2.2.0',
    valid: errors.length === 0,
    summary: {
      filesChecked,
      officialVocabularyEntries: officialEntries.length,
      uniqueOfficialIds: officialIds.size,
      occurrenceEntries: occurrences.length,
      uniqueOccurrenceIds: occurrenceIds.size,
      distinctOfficialEntriesReferenced: referencedOfficialIds.size,
      errors: errors.length
    },
    repeatedVisualOccurrences: {
      soccer: soccer.map(x => x.atlasOccurrenceId),
      scissors: scissors.map(x => x.atlasOccurrenceId)
    },
    errors
  };

  console.log(JSON.stringify(result, null, 2));

  if (errors.length > 0) {
    process.exitCode = 1;
  }
}

main();
