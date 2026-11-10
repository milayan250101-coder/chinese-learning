import os
import requests
import streamlit as st


API_BASE = os.getenv(
    "TEACHER_API_BASE_URL",
    "http://127.0.0.1:8000"
).rstrip("/")

st.set_page_config(
    page_title="教师端 · 学生知识档案",
    page_icon="📚",
    layout="wide",
)

st.title("📚 学生知识档案")
st.caption("管理每位学生的课堂资料，查看分析状态，并在需要时重新分析。")


def response_message(response):
    try:
        data = response.json()
        if isinstance(data, dict):
            return data.get("detail") or data.get("message") or str(data)
        return str(data)
    except Exception:
        return response.text[:500] or f"HTTP {response.status_code}"


def api_headers():
    return {
        "Authorization": f"Bearer {st.session_state['teacher_token']}"
    }


def status_label(status):
    labels = {
        "analyzed": "已分析",
        "reused": "已完成",
        "completed": "已完成",
        "duplicate": "重复资料",
        "failed": "分析失败",
        "not_started": "待分析",
        "running": "分析中",
        "unknown": "状态未知",
    }
    return labels.get(status or "unknown", status or "状态未知")


def note_label(note):
    title = note.get("title") or note.get("filename") or "未命名资料"
    filename = note.get("filename") or ""
    status = status_label(note.get("analysis_status"))
    note_id = note.get("id")
    return f"📄 {title}　|　{filename}　|　{status}　|　ID {note_id}"


# ---------- 教师登录 ----------

if "teacher_token" not in st.session_state:
    st.session_state.teacher_token = None

if not st.session_state.teacher_token:
    st.subheader("教师登录")

    with st.form("teacher_login"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        login_clicked = st.form_submit_button("登录")

    if login_clicked:
        try:
            response = requests.post(
                f"{API_BASE}/api/auth/login",
                data={"username": username, "password": password},
                timeout=20,
            )

            if response.ok:
                st.session_state.teacher_token = response.json()["access_token"]
                st.rerun()
            else:
                st.error(response_message(response))

        except requests.RequestException as exc:
            st.error(f"无法连接后端：{exc}")

    st.stop()


# ---------- 验证当前教师 ----------

try:
    me_response = requests.get(
        f"{API_BASE}/api/auth/me",
        headers=api_headers(),
        timeout=20,
    )

    if me_response.status_code == 401:
        st.session_state.teacher_token = None
        st.warning("登录已过期，请重新登录。")
        st.rerun()

    if not me_response.ok:
        st.error(response_message(me_response))
        st.stop()

    teacher_info = me_response.json()

except requests.RequestException as exc:
    st.error(f"无法连接后端：{exc}")
    st.stop()


top_left, top_right = st.columns([4, 1])

with top_left:
    st.success(f"已登录教师：{teacher_info.get('username', '教师')}")

with top_right:
    if st.button("退出登录"):
        st.session_state.teacher_token = None
        st.rerun()


# ---------- 获取当前教师的学生 ----------

try:
    students_response = requests.get(
        f"{API_BASE}/api/students/",
        headers=api_headers(),
        params={"is_active": "true"},
        timeout=20,
    )

    if not students_response.ok:
        st.error(response_message(students_response))
        st.stop()

    students_data = students_response.json()
    students = (
        students_data.get("items", [])
        if isinstance(students_data, dict)
        else students_data
    )

except requests.RequestException as exc:
    st.error(f"获取学生列表失败：{exc}")
    st.stop()


if not students:
    st.warning("目前没有可用的学生，请先在学生管理功能中创建学生。")
    st.stop()


student_map = {
    int(student["id"]): student
    for student in students
}


def student_label(student_id):
    if student_id is None:
        return "请选择学生"

    student = student_map[student_id]
    name = student.get("display_name") or "未命名学生"
    code = student.get("student_code") or ""
    return f"{name}（{code}）" if code else name


st.subheader("选择学生")

student_options = [None] + list(student_map.keys())

selected_student_id = st.selectbox(
    "学生",
    options=student_options,
    format_func=student_label,
    key="student_choice",
    label_visibility="collapsed",
)

if selected_student_id is None:
    st.info("请选择一位学生，查看其课堂资料。")
    st.stop()

selected_student = student_map[selected_student_id]
student_name = selected_student.get("display_name") or "当前学生"

st.markdown(f"### 📁 {student_name} 的课堂资料")


# ---------- 读取该学生已有资料 ----------

notes = []

try:
    notes_response = requests.get(
        f"{API_BASE}/api/student-knowledge/"
        f"students/{selected_student_id}/notes",
        headers=api_headers(),
        timeout=20,
    )

    if not notes_response.ok:
        st.error(f"读取课堂资料失败：{response_message(notes_response)}")
        st.stop()

    notes_data = notes_response.json()
    notes = notes_data.get("items", [])

except requests.RequestException as exc:
    st.error(f"读取课堂资料失败：{exc}")
    st.stop()


st.caption(f"资料总数：{notes_data.get('total', len(notes))}")


# ---------- 文件列表与选择 ----------

if notes:
    note_map = {
        int(note["id"]): note
        for note in notes
    }

    note_ids = list(note_map.keys())

    selected_note_id = st.selectbox(
        "选择一份资料",
        options=note_ids,
        format_func=lambda note_id: note_label(note_map[note_id]),
        key=f"note_choice_{selected_student_id}",
    )

    selected_note = note_map[selected_note_id]

    # 只读取数据库中已经保存的分析结果，不调用 AI。
    analysis_view = None
    analysis_view_error = None
    try:
        analysis_view_response = requests.get(
            f"{API_BASE}/api/student-knowledge/"
            f"students/{selected_student_id}/notes/"
            f"{selected_note_id}/analysis",
            headers=api_headers(),
            timeout=20,
        )
        if analysis_view_response.ok:
            analysis_view = analysis_view_response.json()
        else:
            analysis_view_error = response_message(analysis_view_response)
    except requests.RequestException as exc:
        analysis_view_error = str(exc)

    st.divider()
    st.subheader("资料详情")

    detail_left, detail_right = st.columns(2)

    with detail_left:
        st.write(f"**标题：** {selected_note.get('title') or '未命名资料'}")
        st.write(f"**文件名：** {selected_note.get('filename') or '未知'}")
        st.write(f"**文件类型：** {selected_note.get('file_type') or '未知'}")

    with detail_right:
        st.write(f"**资料 ID：** {selected_note.get('id')}")
        st.write(f"**上传时间：** {selected_note.get('created_at') or '未知'}")
        current_status = selected_note.get("analysis_status") or "unknown"
        st.write(f"**分析状态：** {status_label(current_status)}")

    if current_status in ("failed", "not_started", "unknown"):
        button_label = (
            "重新分析这份资料"
            if current_status == "failed"
            else "开始分析这份资料"
        )

        if st.button(button_label, type="primary"):
            try:
                with st.spinner("正在提交分析任务，请稍候……"):
                    analysis_response = requests.post(
                        f"{API_BASE}/api/student-knowledge/"
                        f"students/{selected_student_id}/notes/"
                        f"{selected_note_id}/analyze",
                        headers=api_headers(),
                        params={"force": "true"},
                        timeout=300,
                    )

                if analysis_response.ok:
                    analysis_data = analysis_response.json()
                    st.session_state.last_note_action = {
                        "student_name": student_name,
                        "note_title": selected_note.get("title") or selected_note.get("filename"),
                        "status": analysis_data.get("status", "unknown"),
                        "result": analysis_data,
                        "error": None,
                    }
                    st.success("分析请求已完成，资料状态将刷新。")
                    st.rerun()
                else:
                    st.error(
                        f"分析未成功：{response_message(analysis_response)}"
                    )

            except requests.RequestException as exc:
                st.error(f"分析请求失败：{exc}")

    elif current_status == "running":
        st.info("这份资料正在分析中，请稍后刷新页面查看。")

    elif current_status == "duplicate":
        st.info("这份资料与以前的资料重复，将显示原始资料的分析结果。")

    elif current_status in ("analyzed", "reused", "completed"):
        st.success("这份资料已经完成分析。")

    # 分开显示已保存的词汇和语法结果。
    if analysis_view_error:
        st.warning(f"读取已保存分析结果失败：{analysis_view_error}")
    elif analysis_view:
        saved_status = analysis_view.get("status")
        saved_result = analysis_view.get("result")

        if saved_status == "duplicate":
            original_id = analysis_view.get("duplicate_of_note_id")
            st.info(f"重复资料：读取原始资料 ID {original_id} 的分析结果。")

        if saved_status in ("completed", "duplicate"):
            if isinstance(saved_result, dict):
                vocabulary = saved_result.get("vocabulary", [])
                grammar = saved_result.get("grammar", [])

                if not isinstance(vocabulary, list):
                    vocabulary = []
                if not isinstance(grammar, list):
                    grammar = []

                st.divider()
                st.subheader("本课分析结果")

                col1, col2 = st.columns(2)
                col1.metric("识别词汇数量", len(vocabulary))
                col2.metric("识别语法数量", len(grammar))

                with st.expander("查看本课词汇", expanded=False):
                    st.json(vocabulary)

                with st.expander("查看本课语法", expanded=False):
                    st.json(grammar)
            else:
                st.warning("分析状态已完成，但暂时没有读取到有效结果。")

    if "last_note_action" in st.session_state:
        action = st.session_state.last_note_action
        st.divider()
        st.subheader("最近一次重新分析结果")
        st.write(f"资料：{action.get('note_title') or '未命名资料'}")

        if action.get("error"):
            st.error(action["error"])
        else:
            result_data = action.get("result") or {}
            st.write(f"返回状态：{status_label(action.get('status'))}")
            if "vocabulary_count" in result_data:
                st.metric("识别词汇数量", result_data.get("vocabulary_count", 0))
            if "grammar_count" in result_data:
                st.metric("识别语法数量", result_data.get("grammar_count", 0))

            with st.expander("查看分析接口返回数据"):
                st.json(result_data)

else:
    st.info("这位学生目前还没有课堂资料。上传第一份资料后，它会显示在这里。")


# ---------- 上传新资料：独立区域 ----------

st.divider()

with st.expander("＋ 上传新课堂资料", expanded=False):
    st.caption(
        f"新资料将保存到当前学生：{student_name}。"
        "上传成功后会自动启动分析。"
    )

    with st.form("upload_note_form", clear_on_submit=True):
        uploaded_file = st.file_uploader(
            "选择课堂资料",
            type=["txt", "pdf", "docx"],
            help="支持 TXT、PDF、DOCX，单个文件最大 10 MB。",
        )

        note_title = st.text_input(
            "资料标题（可选）",
            placeholder="例如：第 8 课 · 吃与喝",
        )

        upload_clicked = st.form_submit_button("上传并自动分析")

    if upload_clicked and uploaded_file is None:
        st.warning("请先选择一份课堂资料文件。")

    if upload_clicked and uploaded_file is not None:
        try:
            with st.spinner("正在上传资料……"):
                upload_response = requests.post(
                    f"{API_BASE}/api/student-knowledge/"
                    f"students/{selected_student_id}/notes",
                    headers=api_headers(),
                    data={"title": note_title} if note_title.strip() else {},
                    files={
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type or "application/octet-stream",
                        )
                    },
                    timeout=120,
                )

            if not upload_response.ok:
                st.error(f"上传失败：{response_message(upload_response)}")
            else:
                note_data = upload_response.json()
                note_id = note_data["id"]

                action_result = {
                    "student_name": student_name,
                    "student_id": selected_student_id,
                    "note_id": note_id,
                    "title": note_data.get("title") or uploaded_file.name,
                    "analysis_status": "not_started",
                    "analysis_result": None,
                    "analysis_error": None,
                }

                try:
                    with st.spinner("资料已上传，正在自动分析……"):
                        analysis_response = requests.post(
                            f"{API_BASE}/api/student-knowledge/"
                            f"students/{selected_student_id}/notes/"
                            f"{note_id}/analyze",
                            headers=api_headers(),
                            timeout=300,
                        )

                    if analysis_response.ok:
                        action_result["analysis_result"] = analysis_response.json()
                        action_result["analysis_status"] = (
                            action_result["analysis_result"].get("status", "unknown")
                        )
                    else:
                        action_result["analysis_error"] = response_message(
                            analysis_response
                        )
                        action_result["analysis_status"] = "failed"

                except requests.RequestException as exc:
                    action_result["analysis_error"] = str(exc)
                    action_result["analysis_status"] = "failed"

                st.session_state.last_upload_result = action_result
                st.success("资料已保存，页面正在刷新资料列表。")
                st.rerun()

        except requests.RequestException as exc:
            st.error(f"上传请求失败：{exc}")


# ---------- 最近一次上传结果 ----------

if "last_upload_result" in st.session_state:
    result = st.session_state.last_upload_result

    st.divider()
    st.subheader("最近一次上传结果")

    st.write(
        f"学生：**{result['student_name']}** "
        f"（ID：{result['student_id']}）"
    )
    st.write(f"资料：{result['title']}")
    st.write(f"资料 ID：{result['note_id']}")

    if result["analysis_status"] == "duplicate":
        st.info("这份资料属于重复资料，可在上方资料列表中查看原始分析结果。")

    elif result["analysis_status"] in ("analyzed", "reused", "completed"):
        st.success(f"分析状态：{status_label(result['analysis_status'])}")

        analysis = result.get("analysis_result") or {}
        col1, col2 = st.columns(2)

        col1.metric("识别词汇数量", analysis.get("vocabulary_count", 0))
        col2.metric("识别语法数量", analysis.get("grammar_count", 0))

        with st.expander("查看本次分析返回数据"):
            st.json(analysis)

    elif result["analysis_status"] == "running":
        st.warning("分析任务正在运行，请稍后刷新页面查看。")

    else:
        st.error("资料已经保存，但 AI 分析没有成功完成。")
        st.write(result.get("analysis_error") or "可以在上方资料列表中选择这份资料并重新分析。")
