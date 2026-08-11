"""
마케팅 대시보드 — Streamlit 판

실행:  streamlit run app.py
배포:  GitHub 에 올린 뒤 share.streamlit.io 에서 저장소 연결

숫자는 전부 예시로 만들어낸 것입니다. 실제 매출·계정 정보가 아닙니다.
"""

import math
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ads import render_ads_tab   # 〈광고 성과〉 탭 (ads.py)

# ──────────────────────────────────────────────────────────────
# 기본 설정
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="마케팅 대시보드", page_icon="📊", layout="wide")

# 기본 틀이 밋밋해서 카드·탭·여백만 손봤습니다 (색은 .streamlit/config.toml)
st.markdown("""
<style>
  html, body, [data-testid="stApp"]{
    font-family:"Pretendard Variable",Pretendard,-apple-system,"Segoe UI","Malgun Gothic",sans-serif;
  }
  [data-testid="stMainBlockContainer"]{ padding:2.4rem 2.6rem 4rem; max-width:1500px; }
  [data-testid="stHeader"]{ background:transparent; }

  h1{ font-size:1.65rem !important; font-weight:800 !important; letter-spacing:-.03em; }
  h4{ font-size:.95rem !important; font-weight:700 !important; color:#4a5061 !important;
      letter-spacing:-.01em; margin-bottom:.4rem !important; }
  h5{ font-size:.86rem !important; font-weight:700 !important; color:#666d82 !important;
      margin:.2rem 0 .5rem !important; }
  hr{ border-color:#e2e4ec !important; margin:1.3rem 0 !important; }

  /* 숫자 카드 */
  [data-testid="stMetric"]{
    background:#ffffff; border:1px solid #e2e4ec; border-radius:11px;
    padding:13px 15px 12px; box-shadow:0 1px 2px rgba(20,24,40,.05);
  }
  [data-testid="stMetricLabel"] p{ font-size:.72rem !important; font-weight:700; color:#666d82; }
  [data-testid="stMetricValue"]{ font-size:1.35rem !important; font-weight:800; letter-spacing:-.03em; }
  [data-testid="stMetricDelta"]{ font-size:.72rem !important; font-weight:700; }

  /* 탭 */
  [data-testid="stTabs"] [role="tablist"]{
    gap:4px; background:#eaecf2; padding:4px; border-radius:11px;
    width:fit-content; border-bottom:none;
  }
  [data-testid="stTabs"] [role="tab"]{
    border-radius:8px; padding:5px 18px; font-weight:700; font-size:.86rem; color:#666d82;
  }
  [data-testid="stTabs"] [role="tab"][aria-selected="true"]{
    background:#ffffff; color:#1a1c24; box-shadow:0 1px 3px rgba(20,24,40,.10);
  }
  [data-testid="stTabs"] [role="tablist"] [data-baseweb="tab-highlight"],
  [data-testid="stTabs"] [role="tablist"] [data-baseweb="tab-border"]{ display:none; }

  /* 진행률 막대 */
  [data-testid="stProgress"] > div > div{ height:7px; }
  [data-testid="stProgress"] p{ font-size:.68rem !important; color:#8d94a8; }

  /* 표·확장 패널 */
  [data-testid="stDataFrame"]{ border:1px solid #e2e4ec; border-radius:10px; }
  [data-testid="stExpander"]{ border:1px solid #e2e4ec; border-radius:10px; background:#ffffff; }
  [data-testid="stCaptionContainer"] p{ font-size:.72rem !important; color:#8d94a8; line-height:1.55; }

  /* 할 일 카드 */
  .todocard{
    border-left:3px solid var(--c); background:#ffffff; border:1px solid #e2e4ec;
    border-left-width:3px; padding:7px 11px; margin-bottom:6px; border-radius:8px;
    font-size:13px; box-shadow:0 1px 2px rgba(20,24,40,.04);
  }
  .todocard .w{ opacity:.55; font-size:11px; }

  /* 사이드바 */
  [data-testid="stSidebar"]{ border-right:1px solid #e2e4ec; }
  [data-testid="stSidebar"] h3{ font-size:.9rem !important; font-weight:800; }
</style>
""", unsafe_allow_html=True)

BRANDS = {
    "mongle": {"name": "몽글 스튜디오", "color": "#c99400"},
    "clicker": {"name": "클릭커", "color": "#1668c9"},
}
ACCENT = "#c93872"      # 흰 배경에서도 읽히는 진한 핑크
ACCENT_SOFT = "rgba(201,56,114,.10)"
OK_COLOR = "#2c9d5d"
GRID = "rgba(26,28,36,.10)"

CHANNELS = [
    {"id": "c5", "brand": "mongle", "name": "X (트위터)"},
    {"id": "c2", "brand": "mongle", "name": "유튜브"},
    {"id": "c4", "brand": "mongle", "name": "인스타"},
    {"id": "c6", "brand": "mongle", "name": "브이젠"},
    {"id": "c7", "brand": "mongle", "name": "포트폴리오 사이트"},
    {"id": "c8", "brand": "clicker", "name": "X (트위터)"},
    {"id": "c9", "brand": "clicker", "name": "판매 페이지"},
]
CH_NAME = {c["id"]: c["name"] for c in CHANNELS}
# 갈래가 달라도 이름이 같은 채널(X 등)이 있어 그래프에서는 갈래를 앞에 붙입니다
SHORT = {"mongle": "몽글", "clicker": "클릭커"}
CH_LABEL = {c["id"]: f"{SHORT[c['brand']]} · {c['name']}" for c in CHANNELS}
CH_BRAND = {c["id"]: c["brand"] for c in CHANNELS}

WD = ["월", "화", "수", "목", "금", "토", "일"]          # pandas weekday: 월=0
SLOTS = [(0, 5, "새벽\n0-5시"), (5, 9, "아침\n5-9시"), (9, 13, "낮\n9-13시"),
         (13, 17, "오후\n13-17시"), (17, 21, "저녁\n17-21시"), (21, 24, "밤\n21-24시")]

STAGES = [("idea", "생각만 해둠"), ("making", "만드는 중"),
          ("ready", "올릴 준비됨"), ("posted", "올림")]


# ──────────────────────────────────────────────────────────────
# 예시 데이터 — 같은 입력이면 항상 같은 결과가 나오게 만들었습니다
# ──────────────────────────────────────────────────────────────
def rnd(i: int) -> float:
    """시드 없는 의사난수. 실행할 때마다 그래프가 흔들리지 않게 고정합니다."""
    x = math.sin(i * 127.1 + 311.7) * 43758.5453
    return x - math.floor(x)


DOW_W = [0.85, 1.20, 0.90, 1.30, 1.00, 1.15, 0.75]      # 월화수목금토일


def hour_w(h: int) -> float:
    if h < 6:
        return 0.35
    if h < 9:
        return 0.55
    if h < 13:
        return 0.75
    if h < 17:
        return 0.85
    if h < 21:
        return 1.35
    return 1.15


DEMO_POSTS = {
    "mongle": {"base": 1600, "ctr": 2.1, "ch": "c5", "items": [
        "리깅 작업물 before/after", "표정 세트 8종 공개", "작업 과정 타임랩스",
        "수주 안내", "눈 깜빡임 리깅 비교", "물리 연산 시연"]},
    "clicker": {"base": 700, "ctr": 4.5, "ch": "c8", "items": [
        "무료 GIF 배포 알림", "클릭커 움직이는 화면", "구매자 후기 소개",
        "클릭커 사용법 짧게", "신규 스킨 미리보기"]},
}

SERIES = {
    "X 팔로워":         {"brand": "mongle",  "unit": "명", "goal": 500,
                         "v": [62, 84, 103, 121, 148, 167, 190, 218]},
    "유튜브 구독자":     {"brand": "mongle",  "unit": "명", "goal": 100,
                         "v": [8, 13, 19, 24, 31, 38, 44, 51]},
    "들어온 문의":       {"brand": "mongle",  "unit": "건", "goal": 10,
                         "v": [1, 2, 1, 3, 2, 4, 3, 5]},
    "실제로 계약된 것":   {"brand": "mongle",  "unit": "건", "goal": 5,
                         "v": [0, 1, 0, 1, 1, 1, 2, 1]},
    "클릭커 판 개수":    {"brand": "clicker", "unit": "개", "goal": 10,
                         "v": [0, 1, 2, 1, 3, 2, 4, 3]},
    "무료 GIF 받아간 수": {"brand": "clicker", "unit": "회", "goal": 50,
                         "v": [4, 9, 7, 14, 11, 18, 16, 23]},
}

DEMO_DONE = [
    ("mongle", "작업물 3컷 올림"), ("mongle", "타임랩스 영상 올림"), ("mongle", "표정 세트 공개"),
    ("mongle", "리깅 비교 영상"), ("mongle", "물리 연산 시연"), ("mongle", "수주 안내 공지"),
    ("mongle", "고객 후기 정리"), ("mongle", "작업 툴 소개"),
    ("clicker", "무료 GIF 배포 알림"), ("clicker", "사용법 영상 올림"), ("clicker", "후기 소개"),
    ("clicker", "스킨 미리보기"), ("clicker", "업데이트 알림"), ("clicker", "할인 안내"),
    ("mongle", "포트폴리오 새 컷"), ("clicker", "사용 예시 모음"),
]

TODO = [
    ("mongle", "작업물 새 컷 3개 올리기", "c7", 5, "making",
     "포트폴리오는 최근 것이 계속 올라와야 살아 있어 보입니다"),
    ("mongle", "작업 과정 before / after 영상", "c5", 1, "making",
     "결과물만 보여주는 것보다 반응이 좋습니다"),
    ("mongle", "표정 세트 8종 소개", "c2", 3, "ready", "짧은 영상. 자막으로 설명 붙일 것"),
    ("mongle", "수주 열림 공지", "c5", None, "idea", "슬롯 수와 납기를 같이 적을 것"),
    ("mongle", "고객 후기 모아서 정리", "c7", 7, "idea", "처음 보는 사람이 제일 궁금해하는 것"),
    ("clicker", "무료 GIF 홍보 트윗", "c8", 2, "ready", "배포 페이지에 클릭커 링크가 이미 있습니다"),
    ("clicker", "클릭커 움직이는 화면 짧게", "c8", None, "idea", "글보다 보여주는 게 빠릅니다"),
    ("clicker", "산 사람 후기 모아두기", "c9", None, "idea", "처음 보는 사람이 제일 궁금해하는 것"),
]


@st.cache_data
def build_data(today: date):
    """오늘 날짜를 기준으로 예시 데이터를 만듭니다. 날짜가 같으면 결과도 같습니다."""
    # ① 게시물 성과
    rows, k = [], 0
    keys = list(DEMO_POSTS)
    for ago in range(56, -1, -2):
        if rnd(k) < 0.18:
            k += 1
            continue
        k += 1
        bk = keys[k % len(keys)]
        cfg = DEMO_POSTS[bk]
        d = today - timedelta(days=ago)
        h = [9, 13, 15, 18, 19, 20, 21, 22][int(rnd(k) * 8)]
        k += 1
        grow = 0.55 + (1 - ago / 56) * 0.95
        imp = round(cfg["base"] * grow * DOW_W[d.weekday()] * hour_w(h) * (0.75 + rnd(k) * 0.6))
        k += 1
        ctr = cfg["ctr"] * (0.7 + rnd(k) * 0.7)
        k += 1
        clk = max(1, round(imp * ctr / 100))
        conv = round(clk * (0.03 + rnd(k) * 0.06))
        k += 1
        cost = [5000, 8000, 12000][k % 3] if (ago <= 16 and k % 7 == 0) else 0
        rows.append({
            "날짜": d, "시각": h, "갈래": bk, "채널": cfg["ch"],
            "무엇을": cfg["items"][k % len(cfg["items"])],
            "노출": imp, "클릭": clk, "전환": conv, "비용": cost,
        })
    posts = pd.DataFrame(rows)
    posts["요일"] = posts["날짜"].apply(lambda x: WD[x.weekday()])
    posts["CTR"] = (posts["클릭"] / posts["노출"] * 100).round(2)

    # ② 채널 성장 숫자 (8주치 주간 기록)
    growth = []
    for name, s in SERIES.items():
        for i, v in enumerate(s["v"]):
            growth.append({"항목": name, "갈래": s["brand"], "날짜": today - timedelta(days=(7 - i) * 7),
                           "값": v, "단위": s["unit"], "목표": s["goal"]})
    growth = pd.DataFrame(growth)

    # ③ 이미 올린 것 (꾸준함용) + ④ 아직 안 올린 것
    done = [{"갈래": b, "무엇을": t, "채널": None, "날짜": today - timedelta(days=round(3 + i * 3.4)),
             "단계": "posted"} for i, (b, t) in enumerate(DEMO_DONE)]
    todo = [{"갈래": b, "무엇을": t, "채널": c,
             "날짜": (today + timedelta(days=dd)) if dd is not None else None,
             "단계": stg, "메모": memo} for b, t, c, dd, stg, memo in TODO]
    cards = pd.DataFrame(done + todo)
    return posts, growth, cards


TODAY = date.today()
posts_all, growth_all, cards_all = build_data(TODAY)


# ──────────────────────────────────────────────────────────────
# 사이드바 — 어느 갈래를, 어느 기간으로 볼지
# ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 무엇을 볼까요")
    picked = st.multiselect(
        "갈래", options=list(BRANDS), default=list(BRANDS),
        format_func=lambda b: BRANDS[b]["name"],
    )
    if not picked:
        picked = list(BRANDS)
    days = st.radio("기간", [7, 30, 90, 0],
                    format_func=lambda d: "전체" if d == 0 else f"최근 {d}일", index=1)
    st.divider()
    st.caption("화면에 든 숫자는 전부 예시로 만들어낸 것입니다. "
               "실제 계정·매출 정보가 아닙니다.")

frm = TODAY - timedelta(days=days - 1) if days else date(2000, 1, 1)
P = posts_all[(posts_all["갈래"].isin(picked)) & (posts_all["날짜"] >= frm)].copy()
G = growth_all[growth_all["갈래"].isin(picked)].copy()
C = cards_all[cards_all["갈래"].isin(picked)].copy()

BASE_LAYOUT = dict(
    margin=dict(l=8, r=8, t=32, b=8),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(size=12, color="#4a5061"),
    title_font=dict(size=13, color="#666d82"),
    hoverlabel=dict(font_size=12, bgcolor="#ffffff", bordercolor="#d0d4e0"),
    legend=dict(font=dict(size=11)),
)


def fmt(n, dec=0):
    return f"{n:,.{dec}f}"


# ──────────────────────────────────────────────────────────────
st.title("마케팅 대시보드")
st.caption(f"{'적어둔 것 전부' if not days else f'최근 {days}일'} · "
           f"{' · '.join(BRANDS[b]['name'] for b in picked)}")

tab1, tab2, tab3, tab4 = st.tabs(
    ["📌 할 일 · 일정", "📈 성과 지표", "🌱 채널 성장", "📣 광고 성과 (구글 애즈)"])


# ══════════════════════════════════════════════════════════════
# 탭 1 — 할 일 · 일정
# ══════════════════════════════════════════════════════════════
with tab1:
    todo = C[C["단계"] != "posted"]
    done = C[C["단계"] == "posted"]

    a, b, c, d = st.columns(4)
    a.metric("아직 안 올린 것", f"{len(todo)}개")
    b.metric("이미 올린 것", f"{len(done)}개")
    week_from = TODAY - timedelta(days=6)
    c.metric("최근 7일에 올린 것",
             f"{len(done[done['날짜'] >= week_from])}개")
    soon = todo[todo["날짜"].notna() & (todo["날짜"] <= TODAY + timedelta(days=7))]
    d.metric("이번 주 안에 할 것", f"{len(soon)}개")

    st.divider()
    st.markdown("#### 단계별로 어디까지 왔나")
    cols = st.columns(4)
    for col, (sid, sname) in zip(cols, STAGES):
        sub = C[C["단계"] == sid]
        with col:
            st.markdown(f"**{sname}** &nbsp; `{len(sub)}`", unsafe_allow_html=True)
            if sub.empty:
                st.caption("비어 있음")
            for _, r in sub.head(8).iterrows():
                when = ""
                if pd.notna(r["날짜"]) and r["날짜"] is not None:
                    n = (r["날짜"] - TODAY).days
                    when = "오늘" if n == 0 else (f"{n}일 뒤" if n > 0 else f"{-n}일 지남")
                st.markdown(
                    f"<div class='todocard' style='--c:{BRANDS[r['갈래']]['color']}'>{r['무엇을']}"
                    f"<br><span class='w'>{when or '날짜 안 정함'}</span></div>",
                    unsafe_allow_html=True)
            if len(sub) > 8:
                st.caption(f"외 {len(sub) - 8}개")

    st.divider()
    st.markdown("#### 앞으로 4주 — 언제 뭘 올리기로 했나")
    plan = todo[todo["날짜"].notna()].copy()
    if plan.empty:
        st.info("날짜를 잡아둔 것이 없습니다.")
    else:
        plan = plan[plan["날짜"] <= TODAY + timedelta(days=28)].sort_values("날짜")
        plan_view = plan.assign(
            갈래=plan["갈래"].map(lambda b: BRANDS[b]["name"]),
            채널=plan["채널"].map(lambda c: CH_NAME.get(c, "—")),
            남은일수=plan["날짜"].map(lambda d: (d - TODAY).days),
        )[["날짜", "남은일수", "갈래", "채널", "무엇을", "메모"]]
        st.dataframe(plan_view, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════
# 탭 2 — 성과 지표
# ══════════════════════════════════════════════════════════════
with tab2:
    if P.empty:
        st.info("이 기간에는 기록이 없습니다. 사이드바에서 기간을 넓혀 보세요.")
    else:
        prev = posts_all[
            (posts_all["갈래"].isin(picked))
            & (posts_all["날짜"] >= TODAY - timedelta(days=days * 2 - 1))
            & (posts_all["날짜"] < frm)
        ] if days else pd.DataFrame()

        def agg(df):
            if df.empty:
                return dict(imp=0, clk=0, conv=0, cost=0, ctr=None, cpa=None)
            imp, clk = df["노출"].sum(), df["클릭"].sum()
            conv, cost = df["전환"].sum(), df["비용"].sum()
            return dict(imp=imp, clk=clk, conv=conv, cost=cost,
                        ctr=(clk / imp * 100 if imp else None),
                        cpa=(cost / conv if conv else None))

        cur, was = agg(P), agg(prev)

        def delta(now, before, invert=False):
            if not before or now is None:
                return None
            p = (now - before) / before * 100
            return f"{p:+.1f}%"

        k = st.columns(6)
        k[0].metric("노출수", fmt(cur["imp"]), delta(cur["imp"], was["imp"]),
                    help="내 글이 남의 화면에 뜬 횟수. X·유튜브 통계에서 봅니다")
        k[1].metric("클릭수", fmt(cur["clk"]), delta(cur["clk"], was["clk"]),
                    help="그 중 실제로 눌러본 횟수")
        k[2].metric("CTR", f"{cur['ctr']:.2f}%" if cur["ctr"] else "—",
                    delta(cur["ctr"], was["ctr"]),
                    help="뜬 것 중 몇 %가 눌렀나 (클릭 ÷ 노출). 글이 끌리는지를 봅니다")
        k[3].metric("전환수", fmt(cur["conv"]), delta(cur["conv"], was["conv"]),
                    help="눌러본 사람 중 실제로 팔로우·구매·문의까지 간 수")
        k[4].metric("비용", f"{fmt(cur['cost'])}원", delta(cur["cost"], was["cost"]),
                    delta_color="inverse", help="광고에 쓴 돈. 광고를 안 돌렸으면 0")
        k[5].metric("전환당 비용", f"{fmt(cur['cpa'])}원" if cur["cpa"] else "—",
                    delta(cur["cpa"], was["cpa"], True), delta_color="inverse",
                    help="한 건 얻는 데 든 돈 (비용 ÷ 전환). 낮을수록 좋습니다")

        st.divider()

        # ── 추이
        c1, c2 = st.columns([3, 1])
        with c2:
            grain = st.radio("묶는 단위", ["일별", "월별"], horizontal=True, key="grain")
            metric = st.selectbox("무엇을 볼까", ["노출", "클릭", "CTR", "전환", "비용"])
        with c1:
            key = P["날짜"] if grain == "일별" else P["날짜"].map(lambda d: d.replace(day=1))
            g = P.groupby(key).agg({"노출": "sum", "클릭": "sum", "전환": "sum", "비용": "sum"})
            g["CTR"] = (g["클릭"] / g["노출"] * 100).round(2)
            g = g.reset_index(names="구간")
            fig = go.Figure(go.Bar(x=g["구간"], y=g[metric], marker_color=ACCENT,
                                   hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>"))
            fig.update_layout(height=300, title=f"{metric} 추이 ({grain})", **BASE_LAYOUT)
            fig.update_yaxes(gridcolor=GRID)
            st.plotly_chart(fig, use_container_width=True)

        # ── 깔때기 + 도넛
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 깔때기 — 어디서 사람이 빠지나")
            steps = [("노출", cur["imp"], ACCENT), ("클릭", cur["clk"], "#63b3f5"),
                     ("전환", cur["conv"], OK_COLOR)]
            fig = go.Figure(go.Funnel(
                y=[s[0] for s in steps], x=[s[1] for s in steps],
                textinfo="value+percent previous",
                marker=dict(color=[s[2] for s in steps]),
            ))
            fig.update_layout(height=250, **BASE_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("퍼센트는 **바로 위 단계 대비**입니다. 클릭이 낮으면 첫 줄·썸네일이, "
                       "전환이 낮으면 도착한 곳이 문제입니다.")
        with c2:
            st.markdown("##### 갈래별 비중 (노출 기준)")
            byb = P.groupby("갈래")["노출"].sum()
            fig = go.Figure(go.Pie(
                labels=[BRANDS[b]["name"] for b in byb.index], values=byb.values, hole=.58,
                marker=dict(colors=[BRANDS[b]["color"] for b in byb.index]),
                textinfo="percent", hovertemplate="%{label}<br>%{value:,}회<extra></extra>",
            ))
            fig.update_layout(height=250, showlegend=True, **BASE_LAYOUT)
            fig.add_annotation(text=f"<b>{fmt(byb.sum())}</b><br><span style='font-size:10px'>총 노출</span>",
                               showarrow=False, font=dict(size=16))
            st.plotly_chart(fig, use_container_width=True)

        # ── 요일별 + 채널별 CTR
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 무슨 요일에 올리면 잘 되나")
            dow = P.groupby("요일").agg(평균노출=("노출", "mean"), 노출=("노출", "sum"),
                                       클릭=("클릭", "sum"), 개수=("노출", "size"))
            dow["CTR"] = (dow["클릭"] / dow["노출"] * 100).round(2)
            dow = dow.reindex(WD).fillna(0)
            best = dow["평균노출"].idxmax()
            fig = go.Figure(go.Bar(
                x=dow.index, y=dow["평균노출"],
                marker_color=[OK_COLOR if i == best else ACCENT for i in dow.index],
                text=[f"{v:.2f}%" if v else "" for v in dow["CTR"]], textposition="outside",
                hovertemplate="%{x}요일<br>평균 노출 %{y:,.0f}<extra></extra>",
            ))
            fig.update_layout(height=260, **BASE_LAYOUT)
            fig.update_yaxes(gridcolor=GRID)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"막대 = 평균 노출 · 막대 위 = CTR · 지금까지는 **{best}요일**이 가장 잘 퍼졌습니다.")
        with c2:
            st.markdown("##### 채널별 CTR")
            ch = P.groupby("채널").agg(노출=("노출", "sum"), 클릭=("클릭", "sum"))
            ch["CTR"] = (ch["클릭"] / ch["노출"] * 100).round(2)
            ch = ch.sort_values("CTR")
            fig = go.Figure(go.Bar(
                y=[CH_LABEL.get(i, i) for i in ch.index], x=ch["CTR"], orientation="h",
                marker_color=[BRANDS[CH_BRAND.get(i, "mongle")]["color"] for i in ch.index],
                text=[f"{v:.2f}%" for v in ch["CTR"]], textposition="outside",
                customdata=ch["노출"],
                hovertemplate="%{y}<br>CTR %{x:.2f}% · 노출 %{customdata:,}회<extra></extra>",
            ))
            fig.update_layout(height=260, **BASE_LAYOUT)
            fig.update_xaxes(gridcolor=GRID)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("노출 대비 몇 %가 눌렀는지. 노출이 적어도 CTR 이 높으면 잘 맞는 채널입니다.")

        # ── 히트맵
        st.markdown("##### 언제 올리면 잘 되나 — 요일 × 시간대")
        z, txt = [], []
        for w_i, w in enumerate(WD):
            row_z, row_t = [], []
            for a, b_, _ in SLOTS:
                sub = P[(P["날짜"].map(lambda d: d.weekday()) == w_i)
                        & (P["시각"] >= a) & (P["시각"] < b_)]
                if sub.empty:
                    row_z.append(None)
                    row_t.append("")
                else:
                    row_z.append(sub["노출"].mean())
                    row_t.append(f"{sub['노출'].mean():,.0f}")
            z.append(row_z)
            txt.append(row_t)
        fig = go.Figure(go.Heatmap(
            z=z, x=[s[2] for s in SLOTS], y=WD, text=txt, texttemplate="%{text}",
            colorscale=[[0, "rgba(201,56,114,.07)"], [1, ACCENT]],
            hovertemplate="%{y}요일 %{x}<br>평균 노출 %{z:,.0f}<extra></extra>",
            showscale=False, xgap=3, ygap=3,
        ))
        fig.update_layout(height=280, **BASE_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

        flat = [(WD[i], SLOTS[j][2].replace("\n", " "), z[i][j])
                for i in range(7) for j in range(6) if z[i][j]]
        if flat:
            bw, bs, bv = max(flat, key=lambda x: x[2])
            st.caption(f"진한 칸이 잘 되는 시간입니다. 지금까지는 **{bw}요일 {bs}** 이 가장 잘 퍼졌습니다 "
                       f"— 평균 노출 {bv:,.0f}회.")

        # ── 원본 기록
        with st.expander(f"기록 원본 보기 ({len(P)}건)"):
            view = P.sort_values("날짜", ascending=False).assign(
                갈래=P["갈래"].map(lambda b: BRANDS[b]["name"]),
                채널=P["채널"].map(lambda c: CH_NAME.get(c, "—")),
                전환율=(P["전환"] / P["클릭"] * 100).round(1),
            )[["날짜", "시각", "갈래", "채널", "무엇을", "노출", "클릭", "CTR", "전환", "전환율", "비용"]]
            st.dataframe(view, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════
# 탭 3 — 채널 성장
# ══════════════════════════════════════════════════════════════
with tab3:
    st.markdown("#### 목표까지 얼마나 왔나")
    items = list(G["항목"].unique())
    for row in [items[i:i + 3] for i in range(0, len(items), 3)]:
        for col, name in zip(st.columns(3), row):
            s = G[G["항목"] == name].sort_values("날짜")
            last, prev_ = s.iloc[-1], (s.iloc[-2] if len(s) > 1 else None)
            goal, unit = int(last["목표"]), last["단위"]
            pct = min(1.0, last["값"] / goal) if goal else 0
            with col:
                st.metric(name, f"{fmt(last['값'])}{unit}",
                          f"{int(last['값'] - prev_['값']):+d}" if prev_ is not None else None)
                st.progress(pct, text=f"목표 {fmt(goal)}{unit} · {pct * 100:.0f}%")

    st.divider()
    c1, c2 = st.columns([2, 1])
    with c2:
        pick = st.selectbox("어느 숫자를 볼까", items)
    with c1:
        s = G[G["항목"] == pick].sort_values("날짜")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=s["날짜"], y=s["값"], mode="lines+markers", line=dict(color=ACCENT, width=3),
            marker=dict(size=8), fill="tozeroy", fillcolor=ACCENT_SOFT,
            hovertemplate="%{x|%m/%d}<br>%{y:,}<extra></extra>",
        ))
        goal = int(s.iloc[-1]["목표"])
        fig.add_hline(y=goal, line_dash="dot", line_color=OK_COLOR,
                      annotation_text=f"목표 {goal:,}", annotation_position="top left")
        fig.update_layout(height=300, title=f"{pick} — 8주 흐름", **BASE_LAYOUT)
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("#### 얼마나 꾸준했나 — 최근 12주")
    done = cards_all[(cards_all["단계"] == "posted") & (cards_all["갈래"].isin(picked))]
    this_sun = TODAY - timedelta(days=(TODAY.weekday() + 1) % 7)
    weeks = []
    for i in range(12):
        a = this_sun - timedelta(days=(11 - i) * 7)
        b_ = a + timedelta(days=6)
        weeks.append({"주": "이번 주" if i == 11 else f"{a.month}/{a.day}",
                      "개수": int(((done["날짜"] >= a) & (done["날짜"] <= b_)).sum())})
    wk = pd.DataFrame(weeks)
    fig = go.Figure(go.Bar(x=wk["주"], y=wk["개수"], marker_color=ACCENT,
                           text=wk["개수"], textposition="outside",
                           hovertemplate="%{x}<br>%{y}개<extra></extra>"))
    fig.update_layout(height=250, **BASE_LAYOUT)
    fig.update_yaxes(gridcolor=GRID)
    st.plotly_chart(fig, use_container_width=True)
    total, active = int(wk["개수"].sum()), int((wk["개수"] > 0).sum())
    st.caption(f"12주 동안 {total}개 · 주 평균 {total / 12:.1f}개 · "
               f"**한 개라도 올린 주 {active}/12**. 잘한 주보다 빠진 주가 문제입니다.")


# ══════════════════════════════════════════════════════════════
# 탭 4 — 광고 성과 (구글 애즈)
# ══════════════════════════════════════════════════════════════
with tab4:
    st.caption("돈을 주고 돌린 광고의 성과입니다. 위 세 탭은 돈 안 쓰고 그냥 올린 글의 성적이고, "
               "여기는 **광고비를 써서 얻은 것**입니다.")
    render_ads_tab(TODAY, days)
