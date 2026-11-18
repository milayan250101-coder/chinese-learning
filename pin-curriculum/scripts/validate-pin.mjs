#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(process.argv[2] ?? path.join(HERE, '..'));

const LANGS = ['zh-CN', 'en', 'de', 'fr', 'es', 'it'];
const IDS = Array.from(
  { length: 19 },
  (_, i) => `PIN-${String(i + 1).padStart(2, '0')}`
);

const errors = [];
const warnings = [];
let filesChecked = 0;

const report = (code, file, p, message) =>
  errors.push({ code, file, path: p, message });

const warn = (code, file, p, message) =>
  warnings.push({ code, file, path: p, message });

function readJson(rel) {
  const file = path.join(ROOT, rel);
  filesChecked++;

  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (e) {
    report(
      fs.existsSync(file) ? 'PIN_JSON_INVALID' : 'PIN_FILE_MISSING',
      rel,
      '$',
      e.message
    );
    return null;
  }
}

function ajvFor() {
  const a = new Ajv2020({ allErrors: true, strict: false });
  addFormats(a);
  return a;
}

function addSchema(a, name) {
  const schema = readJson(`schema/${name}.schema.json`);
  if (schema) a.addSchema(schema, `${name}.schema.json`);
  return schema;
}

function schemaCheck(a, schema, data, file) {
  if (!schema || data === null) return false;

  const validator = a.getSchema(schema);

  if (!validator) {
    report(
      'PIN_SCHEMA_MISSING',
      `schema/${schema}`,
      '$',
      'Schema was not registered'
    );
    return false;
  }

  const valid = validator(data);

  if (!valid) {
    for (const e of validator.errors ?? []) {
      report(
        'PIN_SCHEMA_VALIDATION_FAILED',
        file,
        e.instancePath || '$',
        `${e.keyword}: ${e.message}`
      );
    }
  }

  return valid;
}

function getStatus(c, name) {
  const flat = c[`${name}Status`];
  return typeof flat === 'string'
    ? flat
    : (c.review?.[name]?.status ?? null);
}

function same(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

function checkTranslation(t, file) {
  if (!t) return;

  const keys = Object.keys(t.content ?? {});

  if (!keys.includes(t.defaultLanguage)) {
    report(
      'PIN_TRANSLATION_DEFAULT_MISSING',
      file,
      '/localizedContent/defaultLanguage',
      'defaultLanguage must exist in content'
    );
  }

  if (!same([...(t.requiredLanguages ?? [])].sort(), [...keys].sort())) {
    report(
      'PIN_TRANSLATION_LANGUAGE_SET_MISMATCH',
      file,
      '/localizedContent',
      'requiredLanguages must exactly match content locale keys'
    );
  }

  for (const lang of LANGS) {
    if (!t.content?.[lang]?.text?.trim()) {
      report(
        'PIN_TRANSLATION_REQUIRED_LOCALE_MISSING',
        file,
        `/localizedContent/content/${lang}`,
        'Required baseline locale is missing or blank'
      );
    }
  }
}

function checkReview(c, file) {
  const review = c.review ?? {};

  for (const name of [
    'firstRoundReview',
    'crossCourseReview',
    'atlasReview',
    'languageReview'
  ]) {
    const item = review[name];
    if (!item) continue;

    if (item.status === 'pending' && item.reviewedAt !== null) {
      report(
        'PIN_REVIEW_TIMESTAMP_INVALID',
        file,
        `/review/${name}/reviewedAt`,
        'Pending review must have reviewedAt=null'
      );
    }

    if (
      item.status === 'completed' &&
      item.reviewedAt === null &&
      !item.notes?.trim()
    ) {
      report(
        'PIN_REVIEW_HISTORY_NOTE_MISSING',
        file,
        `/review/${name}`,
        'Completed review without timestamp requires a historical note'
      );
    }
  }

  const statuses = [
    'firstRoundReview',
    'crossCourseReview',
    'atlasReview',
    'languageReview'
  ].map(name => review[name]?.status);

  if (
    c.acceptanceStatus === 'accepted' &&
    c.contentStatus !== 'approved'
  ) {
    report(
      'PIN_ACCEPTANCE_CONTENT_STATUS_INVALID',
      file,
      '/acceptanceStatus',
      'Accepted course must have approved content'
    );
  }

  if (
    c.contentStatus === 'approved' &&
    (
      c.acceptanceStatus !== 'accepted' ||
      statuses.some(status => status !== 'completed')
    )
  ) {
    report(
      'PIN_APPROVED_REVIEW_INCOMPLETE',
      file,
      '/review',
      'Approved course requires accepted status and all four reviews completed'
    );
  }
}

function checkAtlasReferences(item, file, prefix, officialIds, occurrenceIds) {
  const vocabularyRefs = item.atlasVocabularyReferences ?? [];
  const occurrenceRefs = item.atlasOccurrenceReferences ?? [];

  for (const id of vocabularyRefs) {
    if (!officialIds.has(id)) {
      report(
        'PIN_ATLAS_VOCABULARY_REFERENCE_MISSING',
        file,
        `/${prefix}atlasVocabularyReferences`,
        `Unknown official Atlas vocabulary ID: ${id}`
      );
    }
  }

  for (const id of occurrenceRefs) {
    if (!occurrenceIds.has(id)) {
      report(
        'PIN_ATLAS_OCCURRENCE_REFERENCE_MISSING',
        file,
        `/${prefix}atlasOccurrenceReferences`,
        `Unknown Atlas visual occurrence ID: ${id}`
      );
    }
  }
}

function main() {
  const a = ajvFor();

  addSchema(a, 'pin-manifest');
  addSchema(a, 'translation');
  addSchema(a, 'pin-course');
  addSchema(a, 'atlas-entry');
  addSchema(a, 'atlas-occurrence-map');
  addSchema(a, 'exercise');

  // 1. Validate the PIN manifest.
  const manifest = readJson('data/manifest.json');

  if (
    manifest &&
    schemaCheck(a, 'pin-manifest.schema.json', manifest, 'data/manifest.json')
  ) {
    if (!same(manifest.courses.map(x => x.courseId), IDS)) {
      report(
        'PIN_MANIFEST_ORDER_INVALID',
        'data/manifest.json',
        '/courses',
        'Manifest must list PIN-01 through PIN-19 in order'
      );
    }

    for (let i = 0; i < manifest.courses.length; i++) {
      const course = manifest.courses[i];

      if (course.courseNumber !== i + 1) {
        report(
          'PIN_COURSE_NUMBER_MISMATCH',
          'data/manifest.json',
          `/courses/${i}/courseNumber`,
          `Expected courseNumber ${i + 1}`
        );
      }

      if (course.file !== `pin-${String(i + 1).padStart(2, '0')}.json`) {
        report(
          'PIN_COURSE_FILENAME_MISMATCH',
          'data/manifest.json',
          `/courses/${i}/file`,
          'Course filename must match its position'
        );
      }
    }

    if (!same([...(manifest.languages ?? [])].sort(), [...LANGS].sort())) {
      report(
        'PIN_MANIFEST_LANGUAGES_INVALID',
        'data/manifest.json',
        '/languages',
        'Manifest must include the six baseline languages'
      );
    }

    const counts = {
      totalCourses: manifest.courses.length,
      importedCourses: manifest.courses.filter(
        x => x.contentStatus !== 'not_imported'
      ).length,
      firstRoundCompleted: manifest.courses.filter(
        x => x.firstRoundReviewStatus === 'completed'
      ).length,
      firstRoundPending: manifest.courses.filter(
        x => x.firstRoundReviewStatus === 'pending'
      ).length,
      crossCourseReviewCompleted: manifest.courses.filter(
        x => x.crossCourseReviewStatus === 'completed'
      ).length,
      atlasReviewCompleted: manifest.courses.filter(
        x => x.atlasReviewStatus === 'completed'
      ).length,
      languageReviewCompleted: manifest.courses.filter(
        x => x.languageReviewStatus === 'completed'
      ).length,
      approvedCourses: manifest.courses.filter(
        x => x.contentStatus === 'approved'
      ).length
    };

    for (const [key, value] of Object.entries(counts)) {
      if (manifest.stats?.[key] !== value) {
        report(
          'PIN_MANIFEST_STATS_MISMATCH',
          'data/manifest.json',
          `/stats/${key}`,
          `Expected ${value}, got ${manifest.stats?.[key]}`
        );
      }
    }

    for (const course of manifest.courses) {
      if (
        course.acceptanceStatus === 'accepted' &&
        course.contentStatus !== 'approved'
      ) {
        report(
          'PIN_MANIFEST_ACCEPTANCE_INVALID',
          'data/manifest.json',
          `/courses/${course.courseNumber - 1}/acceptanceStatus`,
          'Accepted course must have approved content'
        );
      }

      const statuses = [
        course.firstRoundReviewStatus,
        course.crossCourseReviewStatus,
        course.atlasReviewStatus,
        course.languageReviewStatus
      ];

      if (
        course.contentStatus === 'approved' &&
        (
          course.acceptanceStatus !== 'accepted' ||
          statuses.some(x => x !== 'completed')
        )
      ) {
        report(
          'PIN_MANIFEST_APPROVAL_INCOMPLETE',
          'data/manifest.json',
          `/courses/${course.courseNumber - 1}`,
          'Approved manifest course requires accepted status and all four reviews completed'
        );
      }
    }
  }

  const manifestCourses = Array.isArray(manifest?.courses)
    ? manifest.courses
    : [];

  const manifestById = new Map(
    manifestCourses.map(x => [x.courseId, x])
  );

  // 2. Load the official Atlas vocabulary IDs.
  const atlasData = readJson('data/atlas-vocabulary.json');
  const atlas = Array.isArray(atlasData) ? atlasData : [];

  if (atlasData !== null && !Array.isArray(atlasData)) {
    report(
      'PIN_ATLAS_DATA_NOT_ARRAY',
      'data/atlas-vocabulary.json',
      '$',
      'Atlas vocabulary must be an array'
    );
  }

  const officialIds = new Set();

  for (const entry of atlas) {
    const rel = 'data/atlas-vocabulary.json';

    schemaCheck(a, 'atlas-entry.schema.json', entry, rel);

    if (officialIds.has(entry.atlasId)) {
      report(
        'PIN_ATLAS_DUPLICATE_ID',
        rel,
        '/atlasId',
        `Duplicate official Atlas ID: ${entry.atlasId}`
      );
    }

    officialIds.add(entry.atlasId);
  }

  // 3. Load and validate the visual occurrence mapping.
  const mapping = readJson('data/atlas-occurrence-map.json');
  const occurrenceIds = new Set();

  if (
    mapping &&
    schemaCheck(
      a,
      'atlas-occurrence-map.schema.json',
      mapping,
      'data/atlas-occurrence-map.json'
    )
  ) {
    for (const occurrence of mapping.entries ?? []) {
      const occurrenceId = occurrence.atlasOccurrenceId;
      const officialId = occurrence.officialAtlasId;

      if (occurrenceIds.has(occurrenceId)) {
        report(
          'PIN_ATLAS_OCCURRENCE_DUPLICATE_ID',
          'data/atlas-occurrence-map.json',
          '/entries',
          `Duplicate occurrence ID: ${occurrenceId}`
        );
      }

      occurrenceIds.add(occurrenceId);

      if (officialId !== null && !officialIds.has(officialId)) {
        report(
          'PIN_ATLAS_OCCURRENCE_BROKEN_LINK',
          'data/atlas-occurrence-map.json',
          `/${occurrenceId}/officialAtlasId`,
          `Unknown official Atlas ID: ${officialId}`
        );
      }
    }
  }

  // 4. Validate all 19 PIN course files.
  const courses = new Map();

  for (const id of IDS) {
    const number = Number(id.slice(4));
    const rel = `data/courses/pin-${String(number).padStart(2, '0')}.json`;
    const course = readJson(rel);

    if (!course) continue;

    schemaCheck(a, 'pin-course.schema.json', course, rel);

    if (course.courseId !== id) {
      report(
        'PIN_COURSE_ID_MISMATCH',
        rel,
        '/courseId',
        `Expected ${id}`
      );
    }

    if (course.courseId && courses.has(course.courseId)) {
      report(
        'PIN_COURSE_DUPLICATE_ID',
        rel,
        '/courseId',
        `Duplicate ${course.courseId}`
      );
    }

    courses.set(id, course);

    const manifestCourse = manifestById.get(id);

    if (manifestCourse) {
      if (course.title !== manifestCourse.title) {
        report(
          'PIN_MANIFEST_COURSE_MISMATCH',
          rel,
          '/title',
          'Course title differs from manifest'
        );
      }

      for (const field of ['contentStatus', 'acceptanceStatus']) {
        if (course[field] !== manifestCourse[field]) {
          report(
            'PIN_MANIFEST_COURSE_MISMATCH',
            rel,
            `/${field}`,
            `${field} differs from manifest`
          );
        }
      }

      for (const [review, field] of [
        ['firstRoundReview', 'firstRoundReviewStatus'],
        ['crossCourseReview', 'crossCourseReviewStatus'],
        ['atlasReview', 'atlasReviewStatus'],
        ['languageReview', 'languageReviewStatus']
      ]) {
        if (getStatus(course, review) !== manifestCourse[field]) {
          report(
            'PIN_MANIFEST_REVIEW_STATUS_MISMATCH',
            rel,
            `/review/${review}/status`,
            `${review} differs from manifest`
          );
        }
      }
    }

    if (course.localizedContent) {
      checkTranslation(course.localizedContent, rel);
    }

    checkReview(course, rel);

    checkAtlasReferences(
      course,
      rel,
      '',
      officialIds,
      occurrenceIds
    );
  }

  // 5. Validate exercise files and their Atlas references.
  const exerciseIds = new Set();
  const exerciseById = new Map();

  const exerciseDirectory = path.join(ROOT, 'data/exercises');

  const exerciseFiles = fs.existsSync(exerciseDirectory)
    ? fs.readdirSync(exerciseDirectory)
        .filter(name => name.endsWith('.json'))
        .sort()
    : [];

  for (const name of exerciseFiles) {
    const rel = `data/exercises/${name}`;
    const exercise = readJson(rel);

    if (!exercise) continue;

    schemaCheck(a, 'exercise.schema.json', exercise, rel);

    if (exerciseIds.has(exercise.exerciseId)) {
      report(
        'PIN_EXERCISE_DUPLICATE_ID',
        rel,
        '/exerciseId',
        'Duplicate exercise ID'
      );
    }

    exerciseIds.add(exercise.exerciseId);
    exerciseById.set(exercise.exerciseId, exercise);

    const courseId = exercise.courseId;

    if (!courses.has(courseId)) {
      report(
        'PIN_EXERCISE_OWNER_MISSING',
        rel,
        '/courseId',
        `Unknown course ${courseId}`
      );
    } else if (
      !(courses.get(courseId).exerciseReferences ?? [])
        .includes(exercise.exerciseId)
    ) {
      report(
        'PIN_EXERCISE_OWNER_REFERENCE_MISMATCH',
        rel,
        '/exerciseId',
        'Owning course does not reference this exercise'
      );
    }

    if (!exercise.exerciseId?.startsWith(`EX-${courseId}-`)) {
      report(
        'PIN_EXERCISE_ID_COURSE_MISMATCH',
        rel,
        '/exerciseId',
        'Exercise ID prefix must match courseId'
      );
    }

    checkAtlasReferences(
      exercise,
      rel,
      '',
      officialIds,
      occurrenceIds
    );

    if (exercise.exerciseType === 'multiple_choice') {
      const options = exercise.options ?? [];
      const optionIds = options.map(x => x.optionId);

      if (new Set(optionIds).size !== optionIds.length) {
        report(
          'PIN_EXERCISE_OPTION_REFERENCE_INVALID',
          rel,
          '/options',
          'Option IDs must be unique'
        );
      }

      if (!optionIds.includes(exercise.answer?.optionId)) {
        report(
          'PIN_EXERCISE_OPTION_REFERENCE_INVALID',
          rel,
          '/answer/optionId',
          'Answer must reference an existing option'
        );
      }
    }

    if (exercise.exerciseType === 'matching') {
      const left = exercise.matchingItems?.left ?? [];
      const right = exercise.matchingItems?.right ?? [];

      if (left.length !== right.length || left.length < 2) {
        report(
          'PIN_EXERCISE_MATCHING_INCOMPLETE',
          rel,
          '/matchingItems',
          'Matching sides must have equal lengths and at least two items'
        );
      }

      const leftIds = left.map(x => x.itemId);
      const rightIds = right.map(x => x.itemId);

      if (
        new Set(leftIds).size !== leftIds.length ||
        new Set(rightIds).size !== rightIds.length
      ) {
        report(
          'PIN_EXERCISE_MATCHING_INCOMPLETE',
          rel,
          '/matchingItems',
          'Matching item IDs must be unique on each side'
        );
      }

      const pairs = exercise.answer?.pairs ?? [];

      for (const pair of pairs) {
        if (
          !leftIds.includes(pair.leftId) ||
          !rightIds.includes(pair.rightId)
        ) {
          report(
            'PIN_EXERCISE_OPTION_REFERENCE_INVALID',
            rel,
            '/answer/pairs',
            'Matching answer must reference existing left/right item IDs'
          );
        }
      }
    }

    const expectedAnswer = {
      pronunciation: 'text',
      spelling: 'text',
      tone_identification: 'tone',
      multiple_choice: 'single_option',
      matching: 'matching_pairs'
    }[exercise.exerciseType];

    if (expectedAnswer && exercise.answerType !== expectedAnswer) {
      report(
        'PIN_EXERCISE_ANSWER_TYPE_MISMATCH',
        rel,
        '/answerType',
        `Expected ${expectedAnswer} for ${exercise.exerciseType}`
      );
    }
  }

  // 6. Validate course-to-exercise references.
  for (const [id, course] of courses) {
    const rel = `data/courses/${id.toLowerCase()}.json`;

    for (const exerciseId of course.exerciseReferences ?? []) {
      if (!exerciseIds.has(exerciseId)) {
        report(
          'PIN_EXERCISE_REFERENCE_MISSING',
          rel,
          '/exerciseReferences',
          `Unknown exercise ${exerciseId}`
        );
      } else if (exerciseById.get(exerciseId)?.courseId !== id) {
        report(
          'PIN_EXERCISE_OWNER_REFERENCE_MISMATCH',
          rel,
          '/exerciseReferences',
          `Exercise ${exerciseId} belongs to ${exerciseById.get(exerciseId)?.courseId}`
        );
      }
    }
  }

  const result = {
    tool: 'validate-pin',
    schemaVersion: '2.2.0',
    valid: errors.length === 0,
    summary: {
      filesChecked,
      coursesChecked: courses.size,
      officialAtlasVocabularyIds: officialIds.size,
      atlasOccurrenceIds: occurrenceIds.size,
      exercisesChecked: exerciseIds.size,
      errors: errors.length,
      warnings: warnings.length
    },
    errors,
    warnings
  };

  console.log(JSON.stringify(result, null, 2));

  if (errors.length > 0) {
    process.exitCode = 1;
  }
}

main();
