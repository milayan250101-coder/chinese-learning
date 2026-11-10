# ==================== HSK 3.0 前端查询模块 ====================
import streamlit as st
import requests
import json
import pandas as pd

st.title("🇨🇳 国际中文教学助手 - 备课与词汇中心")

st.divider()
st.header("📚 新版 HSK 3.0 官方词汇库查询")

selected_level = st.slider("选择 HSK 3.0 级别：", min_value=1, max_value=9, value=1)

if st.button("🔍 加载词汇表"):
    with st.spinner(f"正在从后端加载 HSK 3.0 第 {selected_level} 级词汇..."):
        try:
            res = requests.get(f"http://127.0.0.1:8000/api/hsk3/{selected_level}")
            if res.status_code == 200:
                result = res.json()
                words = result.get("words", [])
                st.success(f"加载成功！HSK {selected_level} 级共计 {result['total']} 个词汇。")
                
                df = pd.DataFrame(words)
                st.dataframe(df, use_container_width=True)
                
                st.download_button(
                    label=f"📥 下载 HSK {selected_level} 级原始 JSON 词库",
                    data=json.dumps(words, ensure_ascii=False, indent=2),
                    file_name=f"HSK3.0_Level_{selected_level}.json",
                    mime="application/json"
                )
            else:
                st.error("获取 HSK 数据失败，请检查后端状态。")
        except Exception as e:
            st.error(f"连接后端失败: {e}")
