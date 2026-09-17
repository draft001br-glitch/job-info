import os
import streamlit as st
from google import genai


# Page Config MUST be the very first Streamlit command executed
st.set_page_config(
    page_title="事実埋めシステム",
    page_icon="◎",
    layout="wide"
)


# Helper to safely check secrets without crashing locally
def safe_get_secret(key: str, default: str = ""):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


# Security check
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False


    if not st.session_state["password_correct"]:
        user_password = st.text_input("Enter App Password", type="password")
        if st.button("Login"):
            target_password = safe_get_secret("APP_PASSWORD", "buraiha")
            if user_password == target_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Incorrect password")
        return False
    return True


if not check_password():
    st.stop()


# Bring your own key feature UI　is threres no api key in the secrets.toml, you should bring your own api to make it work
# if an api is already set, you dont need to
st.sidebar.title("設定")
user_key = st.sidebar.text_input("Custom Gemini API Key (任意)", type="password")


# client getter
@st.cache_resource
def get_genai_client(custom_api_key: str):
    api_key = custom_api_key or os.environ.get("GEMINI_API_KEY") or safe_get_secret("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


# Helper function to load prompts dynamically from file
@st.cache_data
def load_prompt(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        st.error(f"プロンプトファイルが見つかりません: {filepath}")
        st.stop()


# Load System Instructions from the 'prompts' directory
SYSTEM_INSTRUCTION_RE = load_prompt("prompts/re_shukatsu.txt")
SYSTEM_INSTRUCTION_CAM = load_prompt("prompts/re_campus.txt")


# UI Setup
st.title("事実埋め生成システム")


mode = st.radio(
    "作成する媒体を選択してください:",
    ["Ｒｅ就活", "Ｒｅ就活キャンパス"],
    horizontal=True
)


st.divider()


user_input = ""
uploaded_file_text = ""


# File Uploader component
uploaded_file = st.file_uploader("添付資料 (.txt ファイルなど)", type=["txt", "md", "csv"])
if uploaded_file is not None:
    try:
        uploaded_file_text = uploaded_file.read().decode("utf-8")
        st.success("ファイルの読み込みに成功しました")
    except Exception as e:
        st.error(f"ファイル読み込みエラー: {e}")


if mode == "Ｒｅ就活":
    st.subheader("Ｒｅ就活 入力")
   
    input_syutsukai = st.text_area("①【取材情報】 (必須)", height=200)
    input_joho = st.text_area("②【情報】 (補助情報／他社媒体など）)", height=150)
    input_doc_text = st.text_area("③【追加資料】 (情報を資料からコピペする場合)", height=150)
   
    final_doc = f"{uploaded_file_text}\n{input_doc_text}".strip()


    user_input = f"①【取材情報】\n{input_syutsukai}\n\n②【情報】\n{input_joho}\n\n③【追加資料】\n{final_doc}"
    system_instruction = SYSTEM_INSTRUCTION_RE


else:
    st.subheader("Ｒｅ就活キャンパス 入力")
   
    input_camtsukai = st.text_area("①【取材情報】 (必須)", height=200)
    input_johocam = st.text_area("②【情報】 (補助情報／他社媒体など)", height=150)
    input_doc_text = st.text_area("③【追加資料】 (情報を資料からコピペする場合)", height=150)
   
    final_doc = f"{uploaded_file_text}\n{input_doc_text}".strip()


    user_input = f"①【取材情報】\n{input_camtsukai}\n\n②【情報】\n{input_johocam}\n\n③【追加資料】\n{final_doc}"
    system_instruction = SYSTEM_INSTRUCTION_CAM


if st.button("生成開始", type="primary"):
    if not user_input.strip():
        st.warning("情報を入力してください。")
    else:
        client = get_genai_client(user_key)
       
        if not client:
            st.error("API Key が設定されていません。サイドバーに入力するか、Streamlit Secrets に設定してください。")
            st.stop()
           
        st.subheader("生成結果")
       
        # UI placeholder for streaming output
        output_placeholder = st.empty()
        full_response = ""
       
        try:
            response_stream = client.models.generate_content_stream(
                model="models/gemini-3.1-pro-preview",
                contents=user_input,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1,
                    max_output_tokens=65536,
                    top_p=0.95,
                )
            )
           
            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    output_placeholder.markdown(full_response + "▌")
           
            # Remove the cursor block when finished
            output_placeholder.markdown(full_response)
           
            # --- COPY & DOWNLOAD SECTION ---
            if full_response:
                st.divider()
               
                # Download Button
                st.download_button(
                    label="生成結果をダウンロード",
                    data=full_response,
                    file_name=f"{mode}_extracted_info.txt",
                    mime="text/plain",
                    use_container_width=True
                )
               
                # Copyable Block with Streamlit's built-in 1-click copy button
                st.subheader("コピペ用")
                st.caption("右上の「コピーアイコン」をクリックすると、レイアウトを保ったまま全選択コピーできます。")
                st.code(full_response, language="markdown")


        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
