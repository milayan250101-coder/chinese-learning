"""
课堂教学内容候选检索。

职责：
1. 以完整词语为单位，从课堂原文中寻找 HSK 词汇候选。
2. 提供 HSK 语法库作为 AI 判断的候选参考。
3. 不修改学生进度，不判断学生是否掌握。
4. 不直接认定老师已经讲授，最终由老师审核。
"""

from sqlalchemy.orm import Session

from backend.hsk_models import HSKGrammarPoint, HSKVocabulary


DEFAULT_SYLLABUS_VERSION = "2025"


def _find_occurrences(text: str, form: str) -> list[tuple[int, int]]:
    """查找一个词语在原文中的所有出现位置。"""

    if not form:
        return []

    positions = []
    start = 0

    while True:
        index = text.find(form, start)

        if index == -1:
            break

        positions.append((index, index + len(form)))
        start = index + 1

    return positions


def find_vocabulary_candidates(
    db: Session,
    note_text: str,
    syllabus_version: str = DEFAULT_SYLLABUS_VERSION,
) -> list[dict]:
    """
    根据课堂原文检索 HSK 词汇候选。

    以词语为检索单位，而不是以单个汉字为单位。

    规则：
    1. 同时匹配简体和繁体词语。
    2. 优先识别完整词语。
    3. 单字词如果只出现在另一个完整词语内部，则不单独列为候选。
    4. 单字词在原文其他位置独立出现时，仍然保留。
    5. 不合并不同拼音、词性或等级的词汇记录。
    6. 词汇候选编号使用 HSKVocabulary.number。
    """

    if not isinstance(note_text, str) or not note_text.strip():
        return []

    rows = (
        db.query(HSKVocabulary)
        .filter(HSKVocabulary.syllabus_version == syllabus_version)
        .order_by(HSKVocabulary.number)
        .all()
    )

    matched_items = []
    multi_character_spans = []

    # 第一轮：查找所有完整词语及其出现位置。
    for item in rows:
        forms = sorted({
            form
            for form in (item.simplified, item.traditional)
            if isinstance(form, str) and form.strip()
        })

        form_positions = {
            form: _find_occurrences(note_text, form)
            for form in forms
        }

        matched_forms = [
            form for form, positions in form_positions.items()
            if positions
        ]

        if not matched_forms:
            continue

        matched_items.append({
            "item": item,
            "matched_forms": matched_forms,
            "form_positions": form_positions,
        })

        # 记录完整多字词的覆盖范围。
        for form in matched_forms:
            if len(form) > 1:
                multi_character_spans.extend(
                    form_positions[form]
                )

    # 第二轮：过滤只出现在完整词语内部的单字候选。
    candidates = []

    for result in matched_items:
        item = result["item"]
        matched_forms = result["matched_forms"]
        form_positions = result["form_positions"]

        valid_forms = []

        for form in matched_forms:
            positions = form_positions[form]

            if len(form) > 1:
                valid_forms.append(form)
                continue

            # 单字至少要有一次没有被完整多字词覆盖的出现。
            has_independent_occurrence = any(
                not any(
                    span_start <= position_start
                    and position_end <= span_end
                    for span_start, span_end in multi_character_spans
                )
                for position_start, position_end in positions
            )

            if has_independent_occurrence:
                valid_forms.append(form)

        if not valid_forms:
            continue

        candidates.append({
            "id": item.number,
            "level": item.level,
            "simplified": item.simplified,
            "traditional": item.traditional,
            "pinyin": item.pinyin,
            "english": item.english,
            "part_of_speech": item.part_of_speech,
            "matched_forms": sorted(
                valid_forms,
                key=lambda value: (-len(value), value),
            ),
        })

    # 多字词优先排列；同一词形的不同读音、词性和等级全部保留。
    candidates.sort(
        key=lambda item: (
            -max(len(value) for value in item["matched_forms"]),
            item["id"],
        )
    )

    return candidates


def find_grammar_candidates(
    db: Session,
    syllabus_version: str = DEFAULT_SYLLABUS_VERSION,
) -> list[dict]:
    """
    读取指定版本的 HSK 语法知识点，供 AI 结合课堂上下文判断。

    不只查找字面相同的语法名称，因为实际课堂例句
    可能使用了某个语法结构，却没有写出语法名称。
    """

    rows = (
        db.query(HSKGrammarPoint)
        .filter(HSKGrammarPoint.syllabus_version == syllabus_version)
        .order_by(
            HSKGrammarPoint.level,
            HSKGrammarPoint.source_index,
            HSKGrammarPoint.id,
        )
        .all()
    )

    return [
        {
            "id": item.id,
            "level": item.level,
            "category": item.category,
            "category_name": item.category_name,
            "subcategory": item.subcategory,
            "content": item.content,
        }
        for item in rows
    ]


def build_knowledge_candidates(
    db: Session,
    note_text: str,
    syllabus_version: str = DEFAULT_SYLLABUS_VERSION,
) -> dict:
    """
    一次生成词汇和语法候选，直接提供给 AI 分析服务。
    """

    if not isinstance(note_text, str) or not note_text.strip():
        raise ValueError("课堂资料内容不能为空。")

    return {
        "vocabulary": find_vocabulary_candidates(
            db=db,
            note_text=note_text,
            syllabus_version=syllabus_version,
        ),
        "grammar": find_grammar_candidates(
            db=db,
            syllabus_version=syllabus_version,
        ),
    }
