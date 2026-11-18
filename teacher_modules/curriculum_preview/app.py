import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "curriculum" / "CL-course-catalog.json"
COURSES_DIR = ROOT / "curriculum" / "courses"


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


st.set_page_config(
    page_title="我的课程体系 · CL课程预览",
    page_icon="📚",
    layout="wide",
)

st.title("📚 我的课程体系")
st.caption("Chinese Learning · CL原创中文课程体系 · 教师端只读预览")

if not CATALOG_PATH.exists():
    st.error(f"找不到课程目录：{CATALOG_PATH}")
    st.stop()

catalog = read_json(CATALOG_PATH)
courses = catalog.get("courses", [])
modules = catalog.get("modules", [])

st.sidebar.title("课程导航")
st.sidebar.caption(
    f"{catalog.get('catalog_name', 'CL课程体系')} · "
    f"{len(courses)} 门课程"
)

module_names = []
module_map = {}

for module in modules:
    if isinstance(module, dict):
        name = (
            module.get("module_name")
            or module.get("name")
            or module.get("title")
            or module.get("module_id")
        )
        module_id = module.get("module_id")
        if name:
            module_names.append(name)
            module_map[name] = module_id

if not module_names:
    module_names = sorted({
        c.get("module_name", "未分类")
        for c in courses
    })

selected_module = st.sidebar.selectbox(
    "选择课程模块",
    module_names,
)

module_id = module_map.get(selected_module)

filtered_courses = [
    c for c in courses
    if (
        c.get("module_id") == module_id
        if module_id is not None
        else c.get("module_name", "未分类") == selected_module
    )
]

if not filtered_courses:
    st.warning("这个模块目前没有课程记录。")
    st.stop()

course_labels = {
    f"{c['course_id']} · {c['title']}": c
    for c in filtered_courses
}

selected_label = st.sidebar.selectbox(
    "选择课程",
    list(course_labels.keys()),
)

selected_course = course_labels[selected_label]

content_path = COURSES_DIR / f"{selected_course['course_id']}.json"

if not content_path.exists():
    st.error(f"找不到课程详情文件：{content_path}")
    st.stop()

course = read_json(content_path)

st.caption(
    f"{course.get('course_id', '')}  /  "
    f"{selected_course.get('module_name', selected_module)}"
)
st.header(course.get("title", "未命名课程"))

col1, col2, col3 = st.columns(3)
col1.metric("课程编号", course.get("course_id", "—"))
col2.metric("课程状态", course.get("status", "—"))
col3.metric(
    "词汇记录数",
    len([
        v for v in course.get("vocabulary", [])
        if isinstance(v, dict)
        and (v.get("simplified") or "").strip()
    ]),
)

st.divider()

def show_list_section(title, key, display_fields=None):
    st.subheader(title)
    items = course.get(key, [])

    if not items:
        st.info("目前尚未填写。")
        return

    if isinstance(items, list):
        meaningful = []
        for item in items:
            if isinstance(item, dict):
                if any(
                    value not in ("", None, [], {})
                    for value in item.values()
                ):
                    meaningful.append(item)
            elif str(item).strip():
                meaningful.append(item)

        if not meaningful:
            st.info("目前只有空白模板，尚无实际内容。")
            return

        for index, item in enumerate(meaningful, 1):
            if isinstance(item, dict):
                heading = (
                    item.get("simplified")
                    or item.get("pattern")
                    or item.get("title")
                    or item.get("point")
                    or f"项目 {index}"
                )
                with st.expander(str(heading), expanded=True):
                    if display_fields:
                        for field, label in display_fields:
                            value = item.get(field)
                            if value not in ("", None, [], {}):
                                st.markdown(f"**{label}：** {value}")
                    st.json(item, expanded=False)
            else:
                st.markdown(f"- {item}")
    else:
        st.json(items)


with st.expander("🎯 教学目标", expanded=True):
    objectives = course.get("learning_objectives", [])
    if objectives:
        for item in objectives:
            st.markdown(f"- {item}" if isinstance(item, str) else f"- {item}")
    else:
        st.info("尚未填写教学目标。")

st.divider()

st.subheader("📖 主题词汇")
vocabulary = [
    item for item in course.get("vocabulary", [])
    if isinstance(item, dict)
    and (item.get("simplified") or "").strip()
]

if vocabulary:
    st.dataframe(
        [
            {
                "汉字": item.get("simplified", ""),
                "繁体": item.get("traditional", ""),
                "拼音": item.get("pinyin", ""),
                "词性": item.get("part_of_speech", ""),
                "中文释义": item.get("definition_zh", ""),
                "分类": item.get("category", ""),
            }
            for item in vocabulary
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("目前尚未录入真实词汇，现有内容只有空白模板。")

st.divider()

show_list_section("💬 核心表达", "core_expressions")
show_list_section("🧩 核心句型", "sentence_patterns")
show_list_section("🎭 情景对话", "dialogues")
show_list_section("✏️ 课堂练习", "classroom_practice")

with st.expander("📝 综合表达任务"):
    task = course.get("integrated_expression_task", {})
    if task and any(
        value not in ("", None, [], {})
        for value in task.values()
    ):
        st.json(task)
    else:
        st.info("尚未填写。")

show_list_section("📌 教师备注", "teacher_notes")
show_list_section("✅ 学习完成标准", "completion_criteria")
show_list_section("📎 教学资源", "resources")

with st.expander("🌍 多语言内容"):
    translations = course.get("translations", {})
    st.json(translations)

with st.expander("🔍 原始课程JSON"):
    st.json(course)

st.divider()
st.caption(
    "只读预览 · 数据来源：curriculum/CL-course-catalog.json "
    "及 curriculum/courses/ · 本页面不会修改课程数据。"
)
