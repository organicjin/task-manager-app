import streamlit as st
import os
import plotly.graph_objects as go
from datetime import date
from database import (
    init_db, add_task, get_tasks, update_task, delete_task,
    add_project, get_projects, delete_project, get_project_progress,
)
from models import Task
from ai_classifier import classify_task

# .env 파일 (로컬) 또는 Streamlit Cloud secrets 지원
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def get_secret(key: str, default: str = "") -> str:
    """Streamlit Cloud secrets → 환경변수 → 기본값 순으로 조회"""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.getenv(key, default)

# --- 초기 설정 ---
st.set_page_config(page_title="프로젝트 관리 에이전트", page_icon="📋", layout="wide")
init_db()

# --- 모바일 반응형 CSS ---
st.markdown("""
<style>
    /* 모바일 반응형 */
    @media (max-width: 768px) {
        .block-container { padding: 1rem 0.5rem !important; }
        [data-testid="stMetric"] { padding: 0.5rem !important; }
        [data-testid="stMetric"] label { font-size: 0.75rem !important; }
        [data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 0 !important; }
        .stTabs [data-baseweb="tab"] { font-size: 0.8rem !important; padding: 0.5rem !important; }
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1rem !important; }
    }

    /* 로그인 화면 중앙 정렬 */
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
    }

    /* 사분면 카드 */
    .quadrant-card {
        padding: 12px;
        border-radius: 8px;
        min-height: 120px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 비밀번호 인증
# ============================================================
def check_password() -> bool:
    """비밀번호 인증. .env 파일의 APP_PASSWORD 사용."""
    if st.session_state.get("authenticated"):
        return True

    stored_password = get_secret("APP_PASSWORD", "admin1234")

    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.title("🔐 로그인")
    st.caption("프로젝트 관리 에이전트에 접속하려면 비밀번호를 입력하세요.")

    with st.form("login_form"):
        password = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력")
        submitted = st.form_submit_button("로그인", use_container_width=True)

        if submitted:
            if password == stored_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")

    st.markdown('</div>', unsafe_allow_html=True)
    return False


if not check_password():
    st.stop()

# --- 로그아웃 버튼 ---
with st.sidebar:
    if st.button("🚪 로그아웃", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

# --- 사이드바 필터 ---
st.sidebar.title("필터")
category_filter = st.sidebar.radio("카테고리", ["전체", "업무", "개인"])
status_filter = st.sidebar.radio("상태", ["전체", "진행전", "진행중", "완료"])

projects = get_projects()
project_names = {"전체": None}
for p in projects:
    project_names[p.name] = p.id
project_filter = st.sidebar.selectbox("프로젝트", list(project_names.keys()))
selected_project_id = project_names[project_filter]

sort_option = st.sidebar.selectbox("정렬", ["기한순", "중요도순", "사분면순", "최신순"])
sort_map = {"기한순": "due_date", "중요도순": "priority", "사분면순": "quadrant", "최신순": "created_at"}

# --- 데이터 로드 ---
tasks = get_tasks(
    category=category_filter,
    project_id=selected_project_id,
    status=status_filter,
    order_by=sort_map[sort_option],
)

# --- 탭 구성 ---
tab_dashboard, tab_tasks, tab_matrix, tab_projects = st.tabs(
    ["📊 대시보드", "📝 태스크", "🎯 매트릭스", "📁 프로젝트"]
)

# ============================================================
# 탭 1: 대시보드
# ============================================================
with tab_dashboard:
    st.header("대시보드")

    all_tasks = get_tasks()

    # 요약 메트릭
    col1, col2, col3, col4 = st.columns(4)
    total = len(all_tasks)
    done = sum(1 for t in all_tasks if t.status == "완료")
    in_progress = sum(1 for t in all_tasks if t.status == "진행중")
    overdue = sum(1 for t in all_tasks if t.due_date and t.days_left is not None and t.days_left < 0 and t.status != "완료")

    col1.metric("전체 태스크", total)
    col2.metric("완료", done)
    col3.metric("진행중", in_progress)
    col4.metric("기한 초과", overdue)

    st.divider()

    chart_col1, chart_col2 = st.columns(2)

    # 업무/개인 비율 파이차트
    with chart_col1:
        st.subheader("업무 / 개인 비율")
        work_count = sum(1 for t in all_tasks if t.category == "업무")
        personal_count = sum(1 for t in all_tasks if t.category == "개인")
        if total > 0:
            fig = go.Figure(data=[go.Pie(
                labels=["업무", "개인"],
                values=[work_count, personal_count],
                marker_colors=["#636EFA", "#EF553B"],
                hole=0.4,
            )])
            fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("태스크가 없습니다.")

    # 프로젝트별 진행률
    with chart_col2:
        st.subheader("프로젝트 진행률")
        if projects:
            names, ratios = [], []
            for p in projects:
                prog = get_project_progress(p.id)
                if prog["total"] > 0:
                    names.append(p.name)
                    ratios.append(round(prog["ratio"] * 100, 1))
            if names:
                fig = go.Figure(data=[go.Bar(
                    x=ratios, y=names, orientation="h",
                    marker_color="#00CC96",
                    text=[f"{r}%" for r in ratios],
                    textposition="auto",
                )])
                fig.update_layout(
                    xaxis=dict(range=[0, 100], title="완료율 (%)"),
                    height=300, margin=dict(t=20, b=20, l=20, r=20),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("프로젝트에 할당된 태스크가 없습니다.")
        else:
            st.info("프로젝트가 없습니다.")

    # 기한 임박 태스크
    st.divider()
    st.subheader("기한 임박 태스크 (D-3 이내)")
    urgent_tasks = [
        t for t in all_tasks
        if t.due_date and t.days_left is not None and t.days_left <= 3 and t.status != "완료"
    ]
    if urgent_tasks:
        for t in sorted(urgent_tasks, key=lambda x: x.days_left or 0):
            days = t.days_left
            if days < 0:
                badge = f"🔴 D+{abs(days)} (기한 초과)"
            elif days == 0:
                badge = "🟠 D-Day"
            else:
                badge = f"🟡 D-{days}"
            st.markdown(f"- **{t.title}** | {badge} | {t.category} | {t.priority}")
    else:
        st.success("기한 임박 태스크가 없습니다!")

# ============================================================
# 탭 2: 태스크 관리
# ============================================================
with tab_tasks:
    st.header("태스크 관리")

    # 태스크 추가 폼
    with st.expander("새 태스크 추가", expanded=False):
        with st.form("add_task_form"):
            title = st.text_input("제목 *")
            description = st.text_area("설명")

            form_col1, form_col2 = st.columns(2)
            with form_col1:
                due = st.date_input("마감일", value=None)
                project_options = {"없음": None}
                for p in projects:
                    project_options[p.name] = p.id
                proj = st.selectbox("프로젝트", list(project_options.keys()), key="add_proj")
            with form_col2:
                auto_classify = st.checkbox("AI 자동 분류", value=True)
                manual_category = st.selectbox("카테고리", ["업무", "개인"], key="add_cat")
                manual_priority = st.selectbox("중요도", ["높음", "중간", "낮음"], key="add_pri")
                manual_urgency = st.selectbox("긴급도", ["긴급", "보통", "여유"], key="add_urg")

            submitted = st.form_submit_button("추가", use_container_width=True)
            if submitted and title:
                if auto_classify:
                    with st.spinner("AI가 분류 중..."):
                        result = classify_task(title, description)
                    cat = result["category"]
                    pri = result["priority"]
                    urg = result["urgency"]
                    quad = result["quadrant"]
                    st.info(f"AI 분류 결과: {cat} | {pri} | {urg} | 사분면 {quad}")
                else:
                    cat = manual_category
                    pri = manual_priority
                    urg = manual_urgency
                    is_urgent = urg == "긴급"
                    is_important = pri == "높음"
                    if is_urgent and is_important:
                        quad = 1
                    elif not is_urgent and is_important:
                        quad = 2
                    elif is_urgent and not is_important:
                        quad = 3
                    else:
                        quad = 4

                new_task = Task(
                    title=title,
                    description=description,
                    category=cat,
                    priority=pri,
                    urgency=urg,
                    quadrant=quad,
                    project_id=project_options[proj],
                    due_date=due,
                )
                add_task(new_task)
                st.success("태스크가 추가되었습니다!")
                st.rerun()
            elif submitted and not title:
                st.warning("제목을 입력해주세요.")

    # 태스크 목록
    st.divider()
    if not tasks:
        st.info("표시할 태스크가 없습니다.")
    else:
        for t in tasks:
            days_badge = ""
            if t.due_date and t.days_left is not None and t.status != "완료":
                d = t.days_left
                if d < 0:
                    days_badge = f" 🔴 D+{abs(d)}"
                elif d == 0:
                    days_badge = " 🟠 D-Day"
                elif d <= 3:
                    days_badge = f" 🟡 D-{d}"

            status_icon = {"진행전": "⬜", "진행중": "🔵", "완료": "✅"}.get(t.status, "⬜")
            cat_icon = "💼" if t.category == "업무" else "🏠"

            with st.expander(f"{status_icon} {cat_icon} {t.title}{days_badge}"):
                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    new_status = st.selectbox(
                        "상태", ["진행전", "진행중", "완료"],
                        index=["진행전", "진행중", "완료"].index(t.status),
                        key=f"status_{t.id}",
                    )
                    new_cat = st.selectbox(
                        "카테고리", ["업무", "개인"],
                        index=["업무", "개인"].index(t.category),
                        key=f"cat_{t.id}",
                    )
                    new_pri = st.selectbox(
                        "중요도", ["높음", "중간", "낮음"],
                        index=["높음", "중간", "낮음"].index(t.priority),
                        key=f"pri_{t.id}",
                    )
                with edit_col2:
                    new_urg = st.selectbox(
                        "긴급도", ["긴급", "보통", "여유"],
                        index=["긴급", "보통", "여유"].index(t.urgency),
                        key=f"urg_{t.id}",
                    )
                    new_due = st.date_input(
                        "마감일", value=t.due_date, key=f"due_{t.id}",
                    )
                    st.markdown(f"**사분면**: {t.quadrant_label}")

                if t.description:
                    st.markdown(f"**설명**: {t.description}")

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("저장", key=f"save_{t.id}", use_container_width=True):
                        t.status = new_status
                        t.category = new_cat
                        t.priority = new_pri
                        t.urgency = new_urg
                        t.due_date = new_due
                        is_u = new_urg == "긴급"
                        is_i = new_pri == "높음"
                        t.quadrant = 1 if is_u and is_i else 2 if not is_u and is_i else 3 if is_u else 4
                        update_task(t)
                        st.success("저장 완료!")
                        st.rerun()
                with btn_col2:
                    if st.button("삭제", key=f"del_{t.id}", use_container_width=True, type="secondary"):
                        delete_task(t.id)
                        st.rerun()

# ============================================================
# 탭 3: 아이젠하워 매트릭스
# ============================================================
with tab_matrix:
    st.header("아이젠하워 매트릭스")

    active_tasks = [t for t in get_tasks() if t.status != "완료"]

    q1 = [t for t in active_tasks if t.quadrant == 1]
    q2 = [t for t in active_tasks if t.quadrant == 2]
    q3 = [t for t in active_tasks if t.quadrant == 3]
    q4 = [t for t in active_tasks if t.quadrant == 4]

    def render_quadrant(title, color, task_list):
        st.markdown(
            f'<div class="quadrant-card" style="background:{color}">'
            f'<strong>{title}</strong></div>',
            unsafe_allow_html=True,
        )
        if task_list:
            for t in task_list:
                cat_icon = "💼" if t.category == "업무" else "🏠"
                due_str = ""
                if t.days_left is not None:
                    due_str = f" (D-{t.days_left})" if t.days_left >= 0 else f" (D+{abs(t.days_left)})"
                st.markdown(f"- {cat_icon} {t.title}{due_str}")
        else:
            st.caption("없음")

    st.markdown("##### ← 긴급 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 비긴급 →")

    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        render_quadrant("🔴 Q1: 긴급 + 중요 (즉시 실행)", "#FFEBEE", q1)
    with row1_col2:
        render_quadrant("🟡 Q2: 비긴급 + 중요 (계획 수립)", "#FFF8E1", q2)

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        render_quadrant("🟠 Q3: 긴급 + 비중요 (위임)", "#FFF3E0", q3)
    with row2_col2:
        render_quadrant("🟢 Q4: 비긴급 + 비중요 (제거 고려)", "#E8F5E9", q4)

# ============================================================
# 탭 4: 프로젝트 관리
# ============================================================
with tab_projects:
    st.header("프로젝트 관리")

    with st.expander("새 프로젝트 추가"):
        with st.form("add_project_form"):
            pname = st.text_input("프로젝트 이름")
            pdesc = st.text_area("설명", key="proj_desc")
            if st.form_submit_button("추가", use_container_width=True):
                if pname:
                    add_project(pname, pdesc)
                    st.success("프로젝트가 추가되었습니다!")
                    st.rerun()
                else:
                    st.warning("이름을 입력해주세요.")

    st.divider()

    if not projects:
        st.info("프로젝트가 없습니다.")
    else:
        for p in projects:
            prog = get_project_progress(p.id)
            with st.expander(f"📁 {p.name} ({prog['done']}/{prog['total']})"):
                st.progress(prog["ratio"], text=f"완료율: {prog['ratio']*100:.0f}%")
                if p.description:
                    st.markdown(f"**설명**: {p.description}")

                ptasks = get_tasks(project_id=p.id)
                if ptasks:
                    for t in ptasks:
                        icon = {"진행전": "⬜", "진행중": "🔵", "완료": "✅"}.get(t.status, "⬜")
                        st.markdown(f"  {icon} {t.title} ({t.priority})")
                else:
                    st.caption("할당된 태스크가 없습니다.")

                if st.button(f"프로젝트 삭제", key=f"delp_{p.id}", type="secondary"):
                    delete_project(p.id)
                    st.rerun()
