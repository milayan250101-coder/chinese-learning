import json
import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="中文教学工作台",
    page_icon="📚",
    layout="wide"
)

st.title("📚 中文教学工作台")
st.caption("教师专用 · 课堂材料整理 · AI 教案分析 · 教师审核")

if "current_record" not in st.session_state:
    st.session_state.current_record = None
if "edited_plan" not in st.session_state:
    st.session_state.edited_plan = ""
if "working_metadata" not in st.session_state:
    st.session_state.working_metadata = {}

def load_record(record_id):
    response = requests.get(
        f"{API_URL}/api/history/{record_id}",
        timeout=30
    )
    response.raise_for_status()
    record = response.json()
    st.session_state.current_record = record
    st.session_state.edited_plan = record.get("generated_plan") or ""
    return record

def display_structured_items(items):
    if not items:
        st.info("本次分析没有返回这一部分内容。")
        return

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            st.markdown(f"{index}. {item}")
            continue

        if "chinese" in item:
            st.markdown(f"### {item.get('chinese', '')}")
            st.markdown(f"**拼音：** {item.get('pinyin', '未提供')}")
            st.markdown(f"**释义：** {item.get('english', '未提供')}")

        elif "point" in item:
            st.markdown(f"### {item.get('point', '')}")
            st.markdown(item.get("explanation", ""))
            if item.get("example"):
                st.markdown(f"**例句：** {item['example']}")
            if item.get("example_pinyin"):
                st.markdown(f"**拼音：** {item['example_pinyin']}")
            if item.get("example_english"):
                st.markdown(f"**翻译：** {item['example_english']}")

        elif "note" in item and "pinyin" in item:
            st.markdown(f"### {item.get('item', '')}")
            st.markdown(f"**拼音：** {item.get('pinyin', '')}")
            st.caption(item.get("note", ""))

        elif "instruction" in item:
            st.markdown(f"### {item.get('type', '课堂练习')}")
            st.markdown(item.get("instruction", ""))
            for exercise in item.get("items", []):
                st.markdown(f"- {exercise}")

        elif "level" in item and "content" in item:
            st.markdown(f"### {item.get('level', '')}")
            st.markdown(item.get("content", ""))

        else:
            heading = (
                item.get("word")
                or item.get("term")
                or item.get("pattern")
                or item.get("title")
                or f"项目 {index}"
            )
            with st.expander(str(heading)):
                st.json(item)

        st.divider()


with st.sidebar:
    st.header("📂 历史课堂记录")
    try:
        history_response = requests.get(
            f"{API_URL}/api/history",
            timeout=10
        )
        history_response.raise_for_status()
        history = history_response.json()

        if history:
            history_options = {
                f"#{item['id']} · {item['title']} · {item['created_at']}":
                item["id"]
                for item in history
            }
            selected_history = st.selectbox(
                "选择一条历史记录",
                options=list(history_options.keys())
            )
            if st.button("加载这条记录", use_container_width=True):
                try:
                    load_record(history_options[selected_history])
                    st.rerun()
                except requests.RequestException as exc:
                    st.error(f"读取历史记录失败：{exc}")
        else:
            st.caption("目前还没有历史记录。")
    except requests.RequestException:
        st.warning("暂时无法连接后端历史记录接口。")

    st.divider()
    st.caption("支持文件：TXT、PDF、DOCX")
    st.caption("Zoom 字幕 VTT 暂未开放，请先导出为 TXT。")

st.subheader("一、课堂与学生信息")

left, right = st.columns(2)

with left:
    student_name = st.text_input(
        "学生姓名 / 代号",
        placeholder="例如：Student A；通用材料可留空"
    )
    student_type = st.selectbox(
        "学生类型",
        ["初中级学习者", "高级 / 华裔学习者", "通用教学材料"]
    )
    native_language = st.selectbox(
        "学生母语",
        ["English", "French", "German", "Japanese",
         "Korean", "Spanish", "Other / 未指定"]
    )

with right:
    source_type = st.selectbox(
        "课堂材料来源",
        ["Zoom 课堂逐字稿", "当堂课堂笔记", "白板笔记", "其他教学材料"]
    )
    target_language = st.selectbox(
        "教案解释语言",
        ["English", "French", "German", "Japanese",
         "Korean", "Spanish", "Chinese"]
    )
    hsk_level = st.selectbox(
        "HSK 范围",
        ["HSK 1–3", "未指定 / 高级材料"]
    )

st.caption(
    "说明：学生信息和材料来源目前仅用于本次工作台操作，"
    "尚未写入数据库。HSK 4–6 暂不开放。"
)

st.divider()
st.subheader("二、上传课堂材料")

uploaded_file = st.file_uploader(
    "选择课堂材料文件",
    type=["txt", "pdf", "docx"],
    help="目前支持 TXT、PDF、DOCX；单个文件最大 10 MB。"
)

if uploaded_file:
    st.success(
        f"已选择：{uploaded_file.name} "
        f"（{uploaded_file.size / 1024:.1f} KB）"
    )

if st.button(
    "✨ 开始 AI 分析",
    type="primary",
    use_container_width=True,
    disabled=uploaded_file is None
):
    metadata = {
        "student_name": student_name.strip() or "通用教学材料",
        "student_type": student_type,
        "native_language": native_language,
        "source_type": source_type,
        "target_language": target_language
    }
    st.session_state.working_metadata = metadata

    api_hsk_level = (
        "HSK1-3"
        if hsk_level == "HSK 1–3"
        else "Not specified / Advanced"
    )

    try:
        with st.spinner("正在读取材料并生成教案和结构化教学内容，请稍候……"):
            response = requests.post(
                f"{API_URL}/api/process-document",
                files={
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type or "application/octet-stream"
                    )
                },
                data={
                    "target_lang": target_language,
                    "hsk_level": api_hsk_level
                },
                timeout=300
            )
            response.raise_for_status()
            result = response.json()

            record = load_record(result["record_id"])
            st.session_state.current_record = record
            st.session_state.edited_plan = record.get("generated_plan") or ""

        st.success(f"分析完成！记录编号：#{result['record_id']}")
        st.rerun()

    except requests.HTTPError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("detail", "")
        except Exception:
            pass
        st.error(f"分析请求失败：{detail or exc}")
    except requests.RequestException as exc:
        st.error(f"无法连接后端服务：{exc}")
    except (KeyError, ValueError) as exc:
        st.error(f"后端返回的数据格式不符合预期：{exc}")

record = st.session_state.current_record

if record:
    st.divider()
    st.subheader(f"三、课堂分析结果 · 记录 #{record['id']}")

    metadata = st.session_state.working_metadata
    if metadata:
        st.caption(
            f"学生：{metadata.get('student_name', '未指定')}　|　"
            f"类型：{metadata.get('student_type', '未指定')}　|　"
            f"来源：{metadata.get('source_type', '未指定')}　|　"
            f"母语：{metadata.get('native_language', '未指定')}"
        )
    else:
        st.caption(
            f"历史记录 · {record.get('title', '')}　|　"
            f"解释语言：{record.get('target_language', '')}　|　"
            f"级别：{record.get('hsk_level', '')}"
        )

    tab_plan, tab_data, tab_original, tab_review = st.tabs(
        ["AI 教案", "结构化教学内容", "课堂原文", "教师审核"]
    )

    with tab_plan:
        st.markdown(record.get("generated_plan") or "暂无教案内容。")

    with tab_data:
        structured = record.get("structured_data")
        if not structured:
            st.warning(
                "本条记录没有可读取的结构化分析结果。"
                "请以原始材料和教案为准，不要将缺失内容当作已分析。"
            )
        else:
            sections = [
                ("vocabulary", "📖 核心词汇"),
                ("grammar", "🧩 语法要点"),
                ("sentence_patterns", "💬 句型"),
                ("examples", "✍️ 例句"),
                ("pronunciation", "🔊 发音与拼音"),
                ("exercises", "📝 课堂练习"),
                ("hsk_mapping", "🎯 HSK 对应建议")
            ]

            selected_title = st.selectbox(
                "选择要查看的教学内容",
                options=[title for _, title in sections],
                key="structured_category"
            )
            selected_key = next(
                key for key, title in sections
                if title == selected_title
            )

            st.subheader(selected_title)
            display_structured_items(structured.get(selected_key, []))

            st.caption(
                "HSK 对应内容属于 AI 分析建议，正式用于教学前请教师核对。"
            )

    with tab_original:
        original_text = record.get("original_text") or ""
        st.text_area(
            "课堂材料原文",
            value=original_text,
            height=400,
            disabled=True
        )

    with tab_review:
        st.info(
            "你可以在下面修改 AI 教案。当前修改只保留在本次页面会话中，"
            "尚未提供数据库保存功能。"
        )
        edited = st.text_area(
            "教师修改稿",
            key="edited_plan",
            height=500
        )
        st.download_button(
            "下载教师修改稿（Markdown）",
            data=edited,
            file_name=f"lesson_{record['id']}_teacher_review.md",
            mime="text/markdown",
            use_container_width=True
        )

else:
    st.divider()
    st.info("上传一份课堂材料并开始分析后，结果会显示在这里。")
