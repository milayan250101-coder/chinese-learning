import json
import os

import requests


DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-flash"

MAX_NOTE_LENGTH = 20000
REQUEST_TIMEOUT = 90

CLASSIFICATIONS = {
    "new_lesson",
    "previously_exposed",
    "uncertain",
}

TEACHING_SIGNALS = {
    "explicit_explanation",
    "example",
    "exercise",
    "theme_focus",
    "repeated_teaching",
    "contextual_use",
}


class KnowledgeAnalysisError(Exception):
    """学生知识分析错误。"""


def _parse_json_response(content: str) -> dict:
    """稳健解析 AI 返回的 JSON，允许 JSON 外围存在说明文字。"""
    if not isinstance(content, str) or not content.strip():
        raise KnowledgeAnalysisError("AI 返回了空内容。")

    content = content.strip().lstrip("\ufeff").strip()

    # 去除 Markdown 代码围栏。
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    try:
        result = json.loads(content)
    except json.JSONDecodeError as original_error:
        # 尝试从外围说明文字中提取完整 JSON 对象。
        decoder = json.JSONDecoder()
        result = None

        for index, char in enumerate(content):
            if char != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(content[index:])
            except json.JSONDecodeError:
                continue

            if isinstance(candidate, dict):
                result = candidate
                break

        if result is None:
            raise KnowledgeAnalysisError(
                "AI 返回的内容不是完整有效的 JSON。"
                f"解析位置：第 {original_error.lineno} 行，"
                f"第 {original_error.colno} 列；"
                f"字符位置：{original_error.pos}；"
                f"内容长度：{len(content)}。"
            ) from original_error

    if not isinstance(result, dict):
        raise KnowledgeAnalysisError("AI 返回的数据结构不正确。")

    return result


def _prior_candidate_ids(prior_knowledge, key):
    """提取此前资料中已有证据的知识点编号。"""
    if not isinstance(prior_knowledge, dict):
        return set()

    items = prior_knowledge.get(key, [])
    if not isinstance(items, list):
        return set()

    ids = set()

    for item in items:
        if not isinstance(item, dict):
            continue

        candidate_id = item.get("candidate_id")
        evidence = item.get("evidence")

        if candidate_id is not None and isinstance(evidence, str):
            if evidence.strip():
                ids.add(candidate_id)

    return ids


def _validate_results(
    result,
    note_text,
    vocabulary_candidates,
    grammar_candidates,
    prior_knowledge=None,
):
    """核验数据库候选、原文证据和教学分类。"""

    if not isinstance(result.get("vocabulary"), list):
        raise KnowledgeAnalysisError("词汇分析结果格式不正确。")

    if not isinstance(result.get("grammar"), list):
        raise KnowledgeAnalysisError("语法分析结果格式不正确。")

    if not isinstance(result.get("observations", []), list):
        raise KnowledgeAnalysisError("分析说明格式不正确。")

    vocab_ids = {item["id"] for item in vocabulary_candidates}
    grammar_ids = {item["id"] for item in grammar_candidates}

    prior_vocab_ids = _prior_candidate_ids(
        prior_knowledge, "vocabulary"
    )
    prior_grammar_ids = _prior_candidate_ids(
        prior_knowledge, "grammar"
    )

    validated = {
        "vocabulary": [],
        "grammar": [],
        "observations": [],
    }

    for key, allowed_ids, prior_ids in (
        ("vocabulary", vocab_ids, prior_vocab_ids),
        ("grammar", grammar_ids, prior_grammar_ids),
    ):
        seen = set()

        for item in result[key]:
            if not isinstance(item, dict):
                continue

            candidate_id = item.get("candidate_id")
            evidence = item.get("evidence")
            confidence = item.get("confidence")

            if candidate_id not in allowed_ids:
                continue

            if not isinstance(evidence, str) or not evidence.strip():
                continue

            evidence = evidence.strip()

            # 证据必须真实出现在本次课堂原文中
            if evidence not in note_text:
                continue

            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                continue

            if not 0 <= confidence <= 1:
                continue

            classification = item.get(
                "classification", "uncertain"
            )

            if classification not in CLASSIFICATIONS:
                classification = "uncertain"

            # 没有以前课堂资料的证据，
            # 不允许标记为“以前接触”
            if (
                classification == "previously_exposed"
                and candidate_id not in prior_ids
            ):
                classification = "uncertain"

            reason = item.get("classification_reason", "")
            if not isinstance(reason, str):
                reason = ""
            reason = reason.strip()[:500]

            signals = item.get("teaching_signals", [])
            if not isinstance(signals, list):
                signals = []

            signals = list(dict.fromkeys(
                signal
                for signal in signals
                if isinstance(signal, str)
                and signal in TEACHING_SIGNALS
            ))

            # 本课新授必须有明确的教学意图证据。
            # 多个例句只有在至少两条不同原文证据均可核实时才可作为依据。
            if classification == "new_lesson":
                strong_signals = {
                    "explicit_explanation",
                    "exercise",
                    "theme_focus",
                    "repeated_teaching",
                }

                supporting = item.get("supporting_evidence", [])
                if not isinstance(supporting, list):
                    supporting = []

                verified_examples = list(dict.fromkeys(
                    fragment.strip()
                    for fragment in supporting
                    if isinstance(fragment, str)
                    and fragment.strip()
                    and fragment.strip() in note_text
                ))

                has_strong_signal = bool(
                    set(signals) & strong_signals
                )
                has_multiple_examples = (
                    "example" in signals
                    and len(verified_examples) >= 2
                )

                if not (
                    has_strong_signal or has_multiple_examples
                ):
                    classification = "uncertain"

            unique_key = (candidate_id, evidence)
            if unique_key in seen:
                continue

            seen.add(unique_key)

            validated[key].append({
                "candidate_id": candidate_id,
                "evidence": evidence,
                "confidence": confidence,
                "classification": classification,
                "classification_reason": reason,
                "teaching_signals": signals,
            })

    for observation in result.get("observations", []):
        if isinstance(observation, str) and observation.strip():
            validated["observations"].append(
                observation.strip()[:500]
            )

    return validated



class _BatchOutputTooLong(Exception):
    """AI 单批输出达到 token 上限。"""


def _call_analysis_batch(
    note_text,
    vocabulary_candidates,
    grammar_candidates,
    history_data,
    api_key,
):
    """调用 AI 分析一批候选知识点。"""

    system_prompt = """
你是中文教师的课堂知识分析助手。

请根据课堂原文和数据库候选知识点，识别本课实际涉及的词汇和语法。

规则：
1. 只能选择本批数据库候选中的知识点，不得创建编号。
2. 每项必须提供当前课堂原文中的准确证据。
3. 语法必须结合实际句子结构判断，不能只凭关键词匹配。
4. 只输出有真实证据的知识点，不要填满候选列表。
5. new_lesson 必须有明确教学意图：明确讲解、集中练习、主题重点或再次系统讲解。
6. example 或 contextual_use 单独出现，不足以判定为 new_lesson。
7. 如果至少两个不同例句被系统地用于说明同一个知识点，也可以判为 new_lesson；此时必须提供 supporting_evidence 数组，包含至少两个不同且逐字出现在本次课堂原文中的例句片段。
8. 不得编造 supporting_evidence；无法核实的例句不得计数。
9. previously_exposed 必须有此前课堂资料中的有效证据。
10. uncertain 表示偶然出现、教学意图不明确或无法可靠判断。
11. 出现不代表学生已经掌握，不得推断学生掌握或不会。
12. 不需要教师逐条审核。
13. classification_reason 简短说明分类依据。
14. teaching_signals 只能使用：
explicit_explanation、example、exercise、theme_focus、
repeated_teaching、contextual_use。

只返回有效 JSON，不要使用 Markdown。

格式：
{
  "vocabulary": [
    {
      "candidate_id": 123,
      "evidence": "课堂原文准确片段",
      "confidence": 0.95,
      "classification": "new_lesson",
      "classification_reason": "本课明确讲解并练习",
      "teaching_signals": ["explicit_explanation", "exercise"],
      "supporting_evidence": []
    }
  ],
  "grammar": [],
  "observations": []
}
"""

    candidate_data = {
        "vocabulary": vocabulary_candidates,
        "grammar": grammar_candidates,
    }

    user_prompt = (
        "本批数据库候选知识点：\n"
        + json.dumps(candidate_data, ensure_ascii=False)
        + "\n\n此前课堂知识证据：\n"
        + json.dumps(history_data, ensure_ascii=False)
        + "\n\n本次课堂资料原文：\n"
        + note_text
    )

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "thinking": {"type": "disabled"},
                "temperature": 0.1,
                "max_tokens": 5000,
                "stream": False,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise KnowledgeAnalysisError("调用 AI 分析服务失败。") from exc

    try:
        response_data = response.json()
        choices = response_data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("choices 为空")

        choice = choices[0]
        if choice.get("finish_reason") == "length":
            raise _BatchOutputTooLong()

        message = choice.get("message")
        if not isinstance(message, dict):
            raise ValueError("message 格式不正确")

        content = message.get("content")
        if not isinstance(content, str):
            raise ValueError("content 不是文本")

    except _BatchOutputTooLong:
        raise
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise KnowledgeAnalysisError("AI 服务返回的数据结构不正确。") from exc

    try:
        result = _parse_json_response(content)
    except KnowledgeAnalysisError as exc:
        # 只有 finish_reason == length 才允许自动拆分。
        # 普通 JSON 格式错误不重复请求，避免不必要的 API 调用。
        raise KnowledgeAnalysisError(
            "AI 返回的 JSON 格式不正确；"
            f"finish_reason={choice.get('finish_reason')!r}。"
            "本批未检测到 token 截断，因此不自动拆分重试。"
            f"解析详情：{exc}"
        ) from exc

    if not isinstance(result.get("vocabulary"), list):
        raise KnowledgeAnalysisError("AI 词汇结果格式不正确。")
    if not isinstance(result.get("grammar"), list):
        raise KnowledgeAnalysisError("AI 语法结果格式不正确。")
    if not isinstance(result.get("observations", []), list):
        raise KnowledgeAnalysisError("AI 分析说明格式不正确。")

    return result


def _analyze_batch_with_split(
    note_text,
    vocabulary_candidates,
    grammar_candidates,
    history_data,
    api_key,
):
    """输出超限时递归拆分候选，不丢弃候选。"""

    try:
        return _call_analysis_batch(
            note_text,
            vocabulary_candidates,
            grammar_candidates,
            history_data,
            api_key,
        )
    except _BatchOutputTooLong:
        vocab_count = len(vocabulary_candidates)
        grammar_count = len(grammar_candidates)

        if vocab_count + grammar_count <= 1:
            raise KnowledgeAnalysisError(
                "单个知识点分析仍达到 AI 输出上限，分析未完成。"
            )

        if grammar_count > 1 and grammar_count >= vocab_count:
            middle = grammar_count // 2
            left = _analyze_batch_with_split(
                note_text, vocabulary_candidates,
                grammar_candidates[:middle], history_data, api_key
            )
            right = _analyze_batch_with_split(
                note_text, [],
                grammar_candidates[middle:], history_data, api_key
            )
        elif vocab_count > 1:
            middle = vocab_count // 2
            left = _analyze_batch_with_split(
                note_text, vocabulary_candidates[:middle],
                grammar_candidates, history_data, api_key
            )
            right = _analyze_batch_with_split(
                note_text, vocabulary_candidates[middle:],
                [], history_data, api_key
            )
        else:
            # 词汇和语法各只有一个时，分开分析。
            left = _analyze_batch_with_split(
                note_text, vocabulary_candidates,
                [], history_data, api_key
            )
            right = _analyze_batch_with_split(
                note_text, [],
                grammar_candidates, history_data, api_key
            )

        return {
            "vocabulary": left["vocabulary"] + right["vocabulary"],
            "grammar": left["grammar"] + right["grammar"],
            "observations": (
                left.get("observations", [])
                + right.get("observations", [])
            ),
        }


def analyze_knowledge_candidates(
    note_text: str,
    vocabulary_candidates: list[dict],
    grammar_candidates: list[dict],
    prior_knowledge: dict | None = None,
) -> dict:
    """
    分批分析课堂资料中的词汇和语法。
    保留所有候选，统一使用原有验证函数核验结果。
    """

    if not isinstance(note_text, str) or not note_text.strip():
        raise KnowledgeAnalysisError("课堂资料内容为空。")

    if len(note_text) > MAX_NOTE_LENGTH:
        raise KnowledgeAnalysisError(
            "课堂资料过长，需要先分段分析，不能直接截断内容。"
        )

    if not isinstance(vocabulary_candidates, list):
        raise KnowledgeAnalysisError("词汇候选数据格式不正确。")
    if not isinstance(grammar_candidates, list):
        raise KnowledgeAnalysisError("语法候选数据格式不正确。")

    if prior_knowledge is None:
        prior_knowledge = {}
    if not isinstance(prior_knowledge, dict):
        raise KnowledgeAnalysisError("历史知识数据格式不正确。")

    for candidates in (vocabulary_candidates, grammar_candidates):
        for item in candidates:
            if not isinstance(item, dict) or "id" not in item:
                raise KnowledgeAnalysisError("候选知识点缺少数据库编号。")

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise KnowledgeAnalysisError(
            "DEEPSEEK_API_KEY 未在后端环境中配置。"
        )

    history_data = {
        "vocabulary": prior_knowledge.get("vocabulary", []),
        "grammar": prior_knowledge.get("grammar", []),
    }

    vocab_size = 30
    grammar_size = 20

    batch_count = max(
        1,
        (len(vocabulary_candidates) + vocab_size - 1) // vocab_size,
        (len(grammar_candidates) + grammar_size - 1) // grammar_size,
    )

    merged = {
        "vocabulary": [],
        "grammar": [],
        "observations": [],
    }

    for index in range(batch_count):
        vocab_batch = vocabulary_candidates[
            index * vocab_size:(index + 1) * vocab_size
        ]
        grammar_batch = grammar_candidates[
            index * grammar_size:(index + 1) * grammar_size
        ]

        result = _analyze_batch_with_split(
            note_text,
            vocab_batch,
            grammar_batch,
            history_data,
            api_key,
        )

        merged["vocabulary"].extend(result["vocabulary"])
        merged["grammar"].extend(result["grammar"])

        for observation in result.get("observations", []):
            if isinstance(observation, str) and observation.strip():
                merged["observations"].append(observation.strip())

    merged["observations"] = list(dict.fromkeys(merged["observations"]))

    return _validate_results(
        merged,
        note_text,
        vocabulary_candidates,
        grammar_candidates,
        prior_knowledge,
    )
