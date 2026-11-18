#!/usr/bin/env node
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import {fileURLToPath} from 'node:url';import {spawnSync} from 'node:child_process';import crypto from 'node:crypto';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'pin-v22-tests-'));let passed=0,failed=0;const results=[];
function project(name){const d=path.join(tmp,name);fs.cpSync(ROOT,d,{recursive:true,filter:s=>!s.includes('node_modules')&&!s.includes('/tests/run-tests.mjs')});if(fs.existsSync(path.join(ROOT,'node_modules')))fs.symlinkSync(path.join(ROOT,'node_modules'),path.join(d,'node_modules'),'dir');return d;}
function read(p,r){return JSON.parse(fs.readFileSync(path.join(p,r),'utf8'));}function write(p,r,o){fs.writeFileSync(path.join(p,r),JSON.stringify(o,null,2)+'\n');}
function run(p,script,args=[]){return spawnSync(process.execPath,[path.join(p,'scripts',script),p,...args],{encoding:'utf8'});}
function codes(r){try{return JSON.parse(r.stdout||'{}').errors?.map(x=>x.code)??[]}catch{return []}}
function test(name,fn){try{fn();passed++;results.push({id:name,status:'passed'});}catch(e){failed++;results.push({id:name,status:'failed',message:e.message});}}
function validTranslation(){const locales=['zh-CN','en','de','fr','es','it'];return {defaultLanguage:'zh-CN',requiredLanguages:locales,content:Object.fromEntries(locales.map(l=>[l,{text:`translation-${l}`}]))};}
function atlasEntry(id='PTA-P02-001'){return {atlasId:id,hanzi:'妈',originalPinyin:'mā',source:{document:'Pinyin_Town_Atlas.pptx',page:2,scene:'单韵母场景'},translations:{zh:'妈',en:'mother',de:'Mutter',fr:'mère',es:'madre',it:'madre'},courseReferences:['PIN-CORE-VOWEL-01'],review:{status:'approved',issues:[]}};}
function exercise(id='EX-PIN-01-001',course='PIN-01'){return {exerciseId:id,courseId:course,schemaVersion:'2.2.0',exerciseType:'multiple_choice',prompt:{'zh-CN':'选择正确拼音'},answerType:'single_option',options:[{optionId:'a',content:{'zh-CN':'mā'}},{optionId:'b',content:{'zh-CN':'má'}}],answer:{optionId:'a'},atlasVocabularyReferences:['PTA-P02-001'],atlasOccurrenceReferences:['ATLAS-S02-01']};}
function addAtlas(p,e=atlasEntry()){const a=read(p,'data/atlas-vocabulary.json');a.push(e);write(p,'data/atlas-vocabulary.json',a);const c=read(p,'data/courses/pin-01.json');c.atlasVocabularyReferences.push(e.atlasId);c.atlasOccurrenceReferences.push('ATLAS-S02-01');write(p,'data/courses/pin-01.json',c);}
function addExercise(p,e=exercise()){fs.writeFileSync(path.join(p,'data/exercises/a.json'),JSON.stringify(e,null,2)+'\n');const c=read(p,`data/courses/${e.courseId.toLowerCase()}.json`);c.exerciseReferences.push(e.exerciseId);write(p,`data/courses/${e.courseId.toLowerCase()}.json`,c);}
function validate(p){return run(p,'validate-pin.mjs');}
function expectCode(p,code){const r=validate(p),cs=codes(r);if(r.status===0||!cs.includes(code))throw Error(`Expected ${code}; exit=${r.status}; codes=${cs.join(',')}; stderr=${r.stderr}`);}
const cases=[];
cases.push(['T01',p=>{const r=validate(p);if(r.status!==0)throw Error(r.stdout+' '+r.stderr);const a=run(p,'validate-atlas.mjs');if(a.status!==0)throw Error(a.stdout+' '+a.stderr);for(let i=1;i<=19;i++)fs.unlinkSync(path.join(p,`data/courses/pin-${String(i).padStart(2,'0')}.json`));const g=run(p,'generate-course-placeholders.mjs');if(g.status!==0)throw Error(g.stderr||g.stdout);const p02=read(p,'data/courses/pin-02.json');if(p02.review.firstRoundReview.status!=='completed'||!p02.review.firstRoundReview.notes.includes('d/t/n/l'))throw Error('PIN-02 first-round completion history was not preserved by generator');}]);
cases.push(['T02',p=>{fs.unlinkSync(path.join(p,'data/courses/pin-04.json'));expectCode(p,'PIN_FILE_MISSING');}]);
cases.push(['T03',p=>{const m=read(p,'data/manifest.json');m.courses[0].courseNumber=9;write(p,'data/manifest.json',m);expectCode(p,'PIN_COURSE_NUMBER_MISMATCH');}]);
cases.push(['T04',p=>{addAtlas(p);const a=read(p,'data/atlas-vocabulary.json');a.push({...a[0]});write(p,'data/atlas-vocabulary.json',a);expectCode(p,'PIN_ATLAS_DUPLICATE_ID');}]);
cases.push(['T05',p=>{addAtlas(p);const a=read(p,'data/atlas-vocabulary.json');delete a[0].translations.de;write(p,'data/atlas-vocabulary.json',a);const r=run(p,'validate-atlas.mjs');if(r.status===0||!JSON.parse(r.stdout).errors.some(x=>x.code==='ATLAS_SCHEMA_VALIDATION_FAILED'||x.code==='ATLAS_TRANSLATION_MISSING'))throw Error('Missing de locale was not caught');}]);
cases.push(['T06',p=>{addAtlas(p);const a=read(p,'data/atlas-vocabulary.json');a[0].courseReferences=['PIN-02'];write(p,'data/atlas-vocabulary.json',a);const r=run(p,'validate-atlas.mjs');if(r.status===0||!JSON.parse(r.stdout).errors.some(x=>x.code==='ATLAS_SCHEMA_VALIDATION_FAILED'))throw Error('Invalid PIN course reference was not caught');}]);
cases.push(['T07',p=>{const m=read(p,'data/manifest.json');m.stats.importedCourses=1;write(p,'data/manifest.json',m);expectCode(p,'PIN_MANIFEST_STATS_MISMATCH');}]);
cases.push(['T08',p=>{const m=read(p,'data/manifest.json');m.courses[0].contentStatus='draft';write(p,'data/manifest.json',m);expectCode(p,'PIN_MANIFEST_STATS_MISMATCH');}]);
cases.push(['T09',p=>{const c=read(p,'data/courses/pin-01.json');c.contentStatus='approved';c.acceptanceStatus='accepted';write(p,'data/courses/pin-01.json',c);const m=read(p,'data/manifest.json');m.courses[0].contentStatus='approved';m.courses[0].acceptanceStatus='accepted';m.stats.importedCourses=1;m.stats.approvedCourses=1;write(p,'data/manifest.json',m);expectCode(p,'PIN_APPROVED_REVIEW_INCOMPLETE');}]);
cases.push(['T10',p=>{addAtlas(p);addExercise(p);const hash=()=>crypto.createHash('sha256').update(fs.readFileSync(path.join(p,'data/manifest.json'))).digest('hex')+crypto.createHash('sha256').update(fs.readFileSync(path.join(p,'data/atlas-vocabulary.json'))).digest('hex');const before=hash();validate(p);run(p,'validate-atlas.mjs');if(hash()!==before)throw Error('Validator mutated data');}]);
cases.push(['T11',p=>{addAtlas(p);const e=exercise();e.answer.optionId='missing';addExercise(p,e);expectCode(p,'PIN_EXERCISE_OPTION_REFERENCE_INVALID');}]);
cases.push(['T12',p=>{const e={exerciseId:'EX-PIN-01-002',courseId:'PIN-01',schemaVersion:'2.2.0',exerciseType:'matching',prompt:{'zh-CN':'连线'},answerType:'matching_pairs',matchingItems:{left:[{itemId:'l1',content:{'zh-CN':'a'}},{itemId:'l2',content:{'zh-CN':'b'}}],right:[{itemId:'r1',content:{'zh-CN':'1'}}]},answer:{pairs:[]},atlasVocabularyReferences:[],atlasOccurrenceReferences:[]};addExercise(p,e);expectCode(p,'PIN_EXERCISE_MATCHING_INCOMPLETE');}]);
cases.push(['T13',p=>{const c=read(p,'data/courses/pin-01.json');c.atlasVocabularyReferences=['PTA-P99-999'];write(p,'data/courses/pin-01.json',c);expectCode(p,'PIN_ATLAS_VOCABULARY_REFERENCE_MISSING');}]);
cases.push(['T14',p=>{const e=exercise('EX-PIN-02-001','PIN-02');fs.writeFileSync(path.join(p,'data/exercises/a.json'),JSON.stringify(e));const c=read(p,'data/courses/pin-01.json');c.exerciseReferences.push(e.exerciseId);write(p,'data/courses/pin-01.json',c);expectCode(p,'PIN_EXERCISE_OWNER_REFERENCE_MISMATCH');}]);
cases.push(['T15',p=>{const a=read(p,'data/atlas-vocabulary.json');a.push(atlasEntry('PIN-99'));write(p,'data/atlas-vocabulary.json',a);const r=run(p,'validate-atlas.mjs');if(r.status===0||!JSON.parse(r.stdout).errors.some(x=>x.code==='ATLAS_SCHEMA_VALIDATION_FAILED'))throw Error('Invalid official Atlas ID format not caught');}]);
cases.push(['T16',p=>{const c=read(p,'data/courses/pin-01.json');c.review.firstRoundReview.status='pending';c.review.firstRoundReview.notes='';write(p,'data/courses/pin-01.json',c);expectCode(p,'PIN_MANIFEST_REVIEW_STATUS_MISMATCH');}]);
cases.push(['T17',p=>{for(let i=1;i<=19;i++)fs.unlinkSync(path.join(p,`data/courses/pin-${String(i).padStart(2,'0')}.json`));const first=run(p,'generate-course-placeholders.mjs');if(first.status!==0)throw Error(first.stderr||first.stdout);for(let i=2;i<=19;i++)fs.unlinkSync(path.join(p,`data/courses/pin-${String(i).padStart(2,'0')}.json`));const rerun=run(p,'generate-course-placeholders.mjs');if(rerun.status===0)throw Error('Generator should refuse when any target exists');const remaining=fs.readdirSync(path.join(p,'data/courses')).filter(x=>x.endsWith('.json'));if(remaining.length!==1||remaining[0]!=='pin-01.json')throw Error('Generator created partial course files despite one existing target');}]);
cases.push(['T18',p=>{const m=read(p,'data/manifest.json');[m.courses[0],m.courses[1]]=[m.courses[1],m.courses[0]];write(p,'data/manifest.json',m);expectCode(p,'PIN_MANIFEST_ORDER_INVALID');}]);
cases.push(['T19',p=>{const c=read(p,'data/courses/pin-02.json');c.courseId='PIN-01';write(p,'data/courses/pin-02.json',c);expectCode(p,'PIN_COURSE_DUPLICATE_ID');}]);
cases.push(['T20',p=>{addAtlas(p);addExercise(p);const e=exercise();fs.writeFileSync(path.join(p,'data/exercises/b.json'),JSON.stringify(e));expectCode(p,'PIN_EXERCISE_DUPLICATE_ID');}]);
cases.push(['T21',p=>{fs.writeFileSync(path.join(p,'data/courses/pin-01.json'),'{bad json');expectCode(p,'PIN_JSON_INVALID');}]);
cases.push(['T22',p=>{addExercise(p,exercise('EX-PIN-02-001','PIN-01'));expectCode(p,'PIN_EXERCISE_ID_COURSE_MISMATCH');}]);
cases.push(['T23',p=>{const e=exercise();e.answerType='text';addExercise(p,e);expectCode(p,'PIN_SCHEMA_VALIDATION_FAILED');}]);
cases.push(['T24',p=>{const c=read(p,'data/courses/pin-01.json');c.acceptanceStatus='accepted';c.contentStatus='draft';write(p,'data/courses/pin-01.json',c);const m=read(p,'data/manifest.json');m.courses[0].acceptanceStatus='accepted';m.courses[0].contentStatus='draft';m.stats.importedCourses=1;write(p,'data/manifest.json',m);expectCode(p,'PIN_ACCEPTANCE_CONTENT_STATUS_INVALID');}]);
cases.push(['T25',p=>{const m=read(p,'data/manifest.json');m.courses[0].contentStatus='approved';m.courses[0].acceptanceStatus='accepted';m.stats.importedCourses=1;m.stats.approvedCourses=1;write(p,'data/manifest.json',m);expectCode(p,'PIN_MANIFEST_APPROVAL_INCOMPLETE');}]);
cases.push(['T26',p=>{const c=read(p,'data/courses/pin-01.json');delete c.acceptanceStatus;write(p,'data/courses/pin-01.json',c);expectCode(p,'PIN_SCHEMA_VALIDATION_FAILED');}]);
cases.push(['T27',p=>{const c=read(p,'data/courses/pin-02.json');c.review.firstRoundReview.status='pending';c.review.firstRoundReview.reviewedAt='2026-11-17T00:00:00Z';write(p,'data/courses/pin-02.json',c);expectCode(p,'PIN_REVIEW_TIMESTAMP_INVALID');}]);

cases.push(['T28',p=>{
  const c=read(p,'data/courses/pin-01.json');
  c.contentStatus='approved';
  c.acceptanceStatus='accepted';
  c.localizedContent=validTranslation();
  write(p,'data/courses/pin-01.json',c);
  expectCode(p,'PIN_SCHEMA_VALIDATION_FAILED');
}]);

cases.push(['T29',p=>{
  const c=read(p,'data/courses/pin-01.json');
  c.contentStatus='draft';
  c.acceptanceStatus='accepted';
  c.localizedContent=validTranslation();
  write(p,'data/courses/pin-01.json',c);
  const m=read(p,'data/manifest.json');
  m.courses[0].contentStatus='draft';
  m.courses[0].acceptanceStatus='accepted';
  m.stats.importedCourses=1;
  write(p,'data/manifest.json',m);
  expectCode(p,'PIN_SCHEMA_VALIDATION_FAILED');
}]);


cases.push(['T30',p=>{
  const c=read(p,'data/courses/pin-01.json');
  c.atlasOccurrenceReferences=['ATLAS-S99-99'];
  write(p,'data/courses/pin-01.json',c);
  expectCode(p,'PIN_ATLAS_OCCURRENCE_REFERENCE_MISSING');
}]);

cases.push(['T31',p=>{
  const m=read(p,'data/atlas-occurrence-map.json');
  m.entries[0].officialAtlasId='PTA-P99-999';
  write(p,'data/atlas-occurrence-map.json',m);
  expectCode(p,'PIN_ATLAS_OCCURRENCE_BROKEN_LINK');
}]);

cases.push(['T32',p=>{
  const m=read(p,'data/atlas-occurrence-map.json');
  m.entries[1].atlasOccurrenceId=m.entries[0].atlasOccurrenceId;
  write(p,'data/atlas-occurrence-map.json',m);
  expectCode(p,'PIN_ATLAS_OCCURRENCE_DUPLICATE_ID');
}]);

for(const [name,fn] of cases){const p=project(name);test(name,()=>fn(p));}
console.log(JSON.stringify({suite:'PIN v2.2 regression tests',total:cases.length,passed,failed,results},null,2));fs.rmSync(tmp,{recursive:true,force:true});if(failed)process.exitCode=1;
