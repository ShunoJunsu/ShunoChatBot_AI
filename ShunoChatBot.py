from functools import wraps
import streamlit as st
import requests
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import os
import urllib3
import asyncio
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain_classic.agents import AgentExecutor
from langchain_classic.agents import create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from streamlit.runtime.scriptrunner import get_script_run_ctx, add_script_run_ctx

st.set_page_config(
    page_title="IM4U 코딩 비서",
    page_icon="💻",
    layout="wide"
)

main_ctx = get_script_run_ctx()

def with_streamlit_context(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        add_script_run_ctx(ctx=main_ctx)
        return func(*args, **kwargs)
    return wrapper

def with_async_streamlit_context(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        add_script_run_ctx(ctx=main_ctx)
        return await func(*args, **kwargs)
    return wrapper

cookie_manager = stx.CookieManager()

if not "already_displayed_complete_login" in st.session_state:
    st.session_state.already_displayed_complete_login = False

if not "already_displayed_welcome_back" in st.session_state:
    st.session_state.already_displayed_welcome_back = False

if not "recommendation" in st.session_state:
    st.session_state.recommendation = True
    
if not "logged_in" in st.session_state:
    st.session_state.logged_in = False

if not "current_session" in st.session_state:
    st.session_state.current_session = requests.Session()
    st.session_state.current_session.verify = False

st.title("💻 im4u 학원 코딩 비서 💻")
st.subheader("문제를 모르겠다고요? 저를 이용해 보세요!")
st.caption("💻 문제를 묻거나 방법을 물어보세요!")
st.caption("예쁜 자유 게시판 등록 같은 일도 할 수 있답니다!")
st.info("사용자에게 로그인 요청 중...")

@st.dialog("다시 오신 것을 환영합니다!")
def welcome_back_popup():
    st.write("저희의 AI를 사용해 주셔서 감사합니다.")
    st.caption("현재 저장된 정보로 자동 로그인을 하였습니다.")
    st.caption("만약 다른 계정으로 로그인하고 싶으시다면, 로그아웃 후 다시 시도해 주세요.")
    st.button("확인")

if username := cookie_manager.get(cookie="username"):
    if password := cookie_manager.get(cookie="password"):
        post_data = {"username": username, "password": password}
        try:
            req = st.session_state.current_session.post("https://43.200.211.173/api/login", data=post_data)
            req_text = req.json()
            
            if "error" not in req_text or not req_text["error"]:
                st.session_state.user_id = username
                print(f"automatically logged in: user={st.session_state.user_id}, pw={user_pw}, timestamp={datetime.now()}")
                st.session_state.logged_in = True
                st.session_state.recommendation = False
                st.rerun()
                cookie_manager.set(
                    cookie="username",
                    val=username,
                    expires_at=datetime.now() + timedelta(days=1)
                )
                cookie_manager.set(
                    cookie="password",
                    val=password,
                    expires_at=datetime.now() + timedelta(days=1)
                )
                st.success("자동 로그인이 되었습니다.")
                if not st.session_state.already_displayed_welcome_back:
                    st.session_state.already_displayed_welcome_back = True
                    welcome_back_popup()
            else:
                st.error("자동 로그인 실패")
        except Exception as e:
            st.error(f"서버 연결 오류: {e}")

@st.dialog("로그인", dismissible=False)
def login_popup():
    st.write("저희의 AI를 사용하기 앞서 로그인이 필요합니다.")
    st.caption("로그인 정보는 로그인하는 데에만 사용됩니다.")
    st.caption("로그인하지 않으면 클래스 문제에 접근할 수 없습니다.")
    
    with st.form("login_form"):
        txtinput = st.text_input("AJIT 사이트의 ID를 입력하세요")
        user_pw = st.text_input("AJIT 사이트의 비밀번호를 입력하세요", type="password")
        
        submit_clicked = st.form_submit_button("로그인")
        
        if submit_clicked:
            post_data = {"username": txtinput, "password": user_pw}
            try:
                req = st.session_state.current_session.post("https://43.200.211.173/api/login", data=post_data)
                req_text = req.json()
                
                if "error" not in req_text or not req_text["error"]:
                    st.session_state.user_id = txtinput
                    print(f"logged in: user={st.session_state.user_id}, pw={user_pw}, timestamp={datetime.now()}")
                    st.session_state.logged_in = True
                    st.session_state.recommendation = False
                    st.rerun()
                    cookie_manager.set(
                        cookie="username",
                        val=st.session_state.user_id,
                        expires_at=datetime.now() + timedelta(days=1)
                    )
                    cookie_manager.set(
                        cookie="password",
                        val=user_pw,
                        expires_at=datetime.now() + timedelta(days=1)
                    )
                else:
                    st.toast("ID 또는 비밀번호가 잘못되었습니다.")
            except Exception as e:
                st.error(f"서버 연결 오류: {e}")

    if st.button("로그인 없이 진행"):
        st.session_state.recommendation = False
        st.rerun()

placeholder = st.empty()

if not st.session_state.logged_in:
    if placeholder.button("지금 로그인하기"):
        login_popup()
    
    if st.session_state.recommendation:
        login_popup()
else:
    st.success("로그인된 상태입니다.")
    if not st.session_state.already_displayed_complete_login:
        st.session_state.already_displayed_complete_login = True
        st.toast("로그인이 성공적으로 진행되었습니다.")

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_AI_API_KEY"]

def search_string(param: str, dest: str) -> bool:
    return all(word in dest.lower() for word in param.strip().lower().split())

@tool
@with_streamlit_context
def check_ranking(username: str) -> int:
    """
    특정 사용자에 대한 랭킹을 검색합니다.
    'Me'는 지금 사용자를 의미합니다.
    """
    try:
        if username.strip().lower() == "me":
            if not "user_id" in st.session_state:
                return "지금 로그인이 되어 있지 않아 사용자가 누구인지 특정할 수 없습니다. 로그인 한 뒤 다시 시도해 주세요."
            else:
                username = st.session_state.user_id
        res = st.session_state.current_session.get("https://43.200.211.173/api/user_rank/single?username=" + username)
        res_json = res.json()
        if res_json["data"]["rank"] == 0:
            return "해당 사용자의 랭킹이 존재하지 않습니다. 랭킹이 매우 낮거나 존재하지 않는 계정일 수 있습니다."
        return f"해당 사용자의 랭킹은 {res_json['data']['rank']}위이며, 정답 수는 {res_json['data']['profile']['accepted_number']}이고 제출 수는 {res_json['data']['profile']['submission_number']}입니다."    
    except Exception as e:
        return "문제가 발생하여 랭킹을 검색하지 못했습니다. 네트워크 연결 상태를 확인해 주세요."

@tool
@with_streamlit_context
def create_board(title: str, detail: str) -> str:
    """
    게시판을 등록합니다.
    게시판은 HTML 형식으로 등록하고 태그는 p, a, h1, h2, h3, h4, h5, h6, code, img만 사용 가능하고
    속성은 인라인 CSS만 가능합니다.
    title에는 제목 (Plain Text),
    detail에는 본문 (HTML) 이 들어갑니다.
    """
    if not st.session_state.logged_in:
        return "게시판을 등록하려면 로그인이 되어 있어야 합니다. 로그인을 하여 더 많은 기능에 접근해 보세요."
    try:
        post_ready = {
            "title": title,
            "content": "<h6>//이 글은 AI 비서에 의해 제작되었습니다.//</h6>" + detail,
            "visible": "true"
        }
        res = st.session_state.current_session.post("https://43.200.211.173/api/board", post_ready)
        res.raise_for_status()
        return "성공적으로 등록되었습니다."
    except Exception:
        return "문제가 발생하여 게시판을 등록하지 못했습니다. 네트워크 연결 상태를 확인해 주세요."

@tool
@with_streamlit_context
def search_problem_db(query: str) -> str:
    """
    문제를 검색한다.
    """
    try:
        res = st.session_state.current_session.get(f"https://43.200.211.173/api/problem?paging=true&offset=0&limit=10&keyword={query}&page=1", timeout=5, verify=False)
        res.raise_for_status()
        resjson = res.json()
        if not resjson["data"]["results"][0]:
            return "문제를 검색하지 못했습니다. 존재하는 문제인지 확인해 주세요."
        result = "=== 문제 내용 ===\n" + resjson["data"]["results"][0]["description"] + "\n\n=== 문제 input ===\n" + resjson["data"]["results"][0]["input_description"] + "\n\n=== 문제 output ===\n" + resjson['data']['results'][0]['output_description'] + f"\n\n=====\n\n문제 시간제한: {resjson['data']['results'][0]['time_limit']}ms\n문제 메모리 제한: {resjson['data']['results'][0]['memory_limit']}MB"
        for i, sample in enumerate(resjson["data"]["results"][0]["samples"]):
            result = f"{result}\n\n=== 예제 {i + 1} ===\ninput: {sample['input']}\noutput: {sample['output']}"
        return result
    except Exception:
        return "문제가 발생하여 문제 정보를 가져오지 못했습니다. 네트워크 연결 상태를 확인해 주세요."

@tool
@with_streamlit_context
def search_contest_db(query: str) -> str:
    """
    클래스에 있는 문제를 검색한다.
    """
    if not st.session_state.logged_in:
        return "로그인이 되어 있지 않아 클래스 문제를 가져올 수 없습니다. 로그인을 하여 클래스 문제를 가져오세요."
    try:
        res = st.session_state.current_session.get("https://43.200.211.173/api/contests?offset=0&limit=30", timeout=5, verify=False)
        res.raise_for_status()
        res_json = res.json()
        result = "문제를 찾지 못했습니다. 문제의 철자가 맞는지, 문제가 존재하는지 확인해 주세요."
        for contest in res_json["data"]["results"]:
            res_second = st.session_state.current_session.get(f"https://43.200.211.173/api/contest/problem?contest_id={contest['id']}&paging=true&offset=0&limit=30", timeout=5, verify=False)
            res_second.raise_for_status()
            res_second_json = res_second.json()
            brake = False
            for problem in res_second_json["data"]:
                if search_string(query, problem["title"]):
                    result = "=== 문제 내용 ===\n" + problem["description"] + "\n\n=== 문제 input ===\n" + problem["input_description"] + "\n\n=== 문제 output ===\n" + problem['output_description'] + f"\n\n=====\n\n문제 시간제한: {problem['time_limit']}ms\n문제 메모리 제한: {problem['memory_limit']}MB"
                    for i, sample in enumerate(problem["samples"]):
                        result = f"{result}\n\n=== 예제 {i + 1} ===\ninput: {sample['input']}\noutput: {sample['output']}"
                    brake = True
                    break
            if brake:
                break
        return result
    except Exception as e:
        return "문제가 발생하여 문제 정보를 가져오지 못했습니다. 네트워크 연결 상태를 확인해 주세요."

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.1,
    streaming=True
)

prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        "당신은 im4u라는 코딩 학원의 코딩 문제 풀이/기타 활동 비서입니다. "
        "사용자가 말한 문제가 무엇인지 모를 때나 게시판을 등록해야 할 때, 랭킹을 확인해야 할 때에는 tool을 사용합니다. "
        "문제 관련 tool을 사용하기 전 사용자가 그냥 문제를 알려달라고 하면 클래스 문제인지 아니면 그냥 문제인지 물어보세요. "
        "확실하지 않으면 모른다고 대답하세요."
        "이 사이트에서는 로그인을 하지 않으면 극히 제한적인 일만 할 수 있습니다. 로그인을 하는 것을 권장합니다."
        f"{f' 사용자의 이름은 {st.session_state.user_id}입니다. 이미 로그인되었습니다.' if 'user_id' in st.session_state else '사용자가 로그인을 하지 않았습니다. 로그인 버튼은 위쪽에 있습니다. 버튼의 이름은 지금 로그인하기 입니다.'}"
    ),
    HumanMessagePromptTemplate.from_template("{chat_history}\n{input}\n{agent_scratchpad}")
])

tools = [search_problem_db, search_contest_db, create_board, check_ranking]
agent = create_tool_calling_agent(
    llm = llm,
    tools=tools,
    prompt=prompt
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True
)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    msg_dict = msg.dict()
    with st.chat_message(msg_dict["type"]):
        st.markdown(msg_dict["content"])

@with_async_streamlit_context
async def start_agent_streaming(agent_executor, chat_history, user_input) -> str:
    add_script_run_ctx(ctx=ctx)

    status = st.status("에이전트가 답변을 생성하기 시작하는 중...", expanded=True)
    full_response = ""
    already_displayed = False
    container = st.empty()
    async for event in agent_executor.astream_events(
        {"input": user_input, "chat_history": chat_history},
        version="v2"
    ):
        kind = event["event"]

        if kind == "on_chat_model_stream":
            if not already_displayed:
                status.update(label="에이전트가 답변을 생성하는 중...", state="running")
                status.write("🪄 답변 생성 중...")
                already_displayed = True
            content = event["data"]["chunk"].content
            if content:
                full_response += content
                container.markdown(full_response + "▌")
        else:
            with status:
                if kind == "on_tool_start":
                    status.update(label="에이전트가 도구를 사용하는 중...", state="running")
                    name = ""
                    if event["name"] == "search_problem_db":
                        name = "일반 문제 검색 중"
                    elif event["name"] == "search_contest_db":
                        name = "클래스 문제 검색 중"
                    elif event["name"] == "check_ranking":
                        name = "랭킹 검색 중"
                    elif event["name"] == "create_board":
                        name = "게시판 등록 중"
                    status.write(f"🛠️ {name}...")
                elif kind == "on_tool_end":
                    name = ""
                    if event["name"] == "search_problem_db":
                        name = "일반 문제 검색 완료"
                    elif event["name"] == "search_contest_db":
                        name = "클래스 문제 검색 완료"
                    elif event["name"] == "check_ranking":
                        name = "랭킹 검색 완료"
                    elif event["name"] == "create_board":
                        name = "게시판 등록 완료"
                    status.write(f"✅ {name}!")

    status.update(label="에이전트가 답변을 생성함", state="complete", expanded=False)
    container.markdown(full_response)
    return full_response

user_input = st.chat_input("무엇이든 물어보세요... (예: 월급받는 권종구 문제 알려줘)")
if user_input:
    st.session_state.chat_history.append(HumanMessage(content=user_input))
    
    with st.chat_message("user"):
        st.markdown(user_input)
    
    full_response = ""

    with st.chat_message("assistant"):
        try:
            full_response = asyncio.run(start_agent_streaming(agent_executor, st.session_state.chat_history, user_input))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            full_response = loop.run_until_complete(start_agent_streaming(agent_executor, st.session_state.chat_history, user_input))
    
    st.session_state.chat_history.append(AIMessage(full_response))