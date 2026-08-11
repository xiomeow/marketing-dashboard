"""
구글 애즈 성과 — app.py 의 〈광고 성과〉 탭에서 불러 씁니다.

검색·디스플레이·동영상 캠페인을 돌렸다고 가정한 화면입니다.
숫자는 전부 예시로 만들어낸 것입니다. 실제 광고 계정 자료가 아닙니다.
"""

import math
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ── 색 (app.py 와 같은 톤)
BLUE, GREEN, YELLOW, RED = "#1668c9", "#2c9d5d", "#c99400", "#c93872"
GRID = "rgba(26,28,36,.10)"
TYPE_COLOR = {"검색": BLUE, "디스플레이": YELLOW, "동영상": RED}

BASE = dict(
    margin=dict(l=8, r=8, t=34, b=8),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(size=12, color="#4a5061"),
    title_font=dict(size=13, color="#666d82"),
    hoverlabel=dict(font_size=12, bgcolor="#ffffff", bordercolor="#d0d4e0"),
)
LEGEND_TOP = dict(orientation="h", y=1.14, x=0, font=dict(size=11))
WD = ["월", "화", "수", "목", "금", "토", "일"]


# ──────────────────────────────────────────────────────────────
# 캠페인 설정 — 실제로 돌렸다면 이랬을 법한 값들
# ──────────────────────────────────────────────────────────────
CAMPAIGNS = [
    # 이름, 유형, 일예산, 기본CPC, 기본CTR%, 전환율%, 전환1건 가치, 노출점유율%
    ("[검색] Live2D 리깅 외주",     "검색",      15000, 820, 5.2, 4.6, 81000, 42),
    ("[검색] 버튜버 모델 제작",      "검색",      12000, 960, 4.4, 3.8, 81000, 31),
    ("[검색] 브랜드 · 몽글 스튜디오", "검색",       3000, 380, 12.6, 6.0, 81000, 78),
    ("[디스플레이] 클릭커 리타게팅",  "디스플레이", 8000, 160, 0.62, 2.1, 20000, 18),
    ("[동영상] 작업 과정 유튜브",     "동영상",     6000,  95, 1.15, 1.4, 20000, 12),
]

KEYWORDS = [
    # 키워드, 매치타입, 캠페인 인덱스, 노출비중, CTR배수, CPC배수, 품질점수
    ("live2d 리깅",         "구문검색", 0, .34, 1.15, 1.00, 8),
    ("라이브2d 외주",        "완전일치", 0, .21, 1.30, 0.92, 9),
    ("live2d 커미션",       "구문검색", 0, .18, 1.05, 1.05, 7),
    ("리깅 가격",            "구문검색", 0, .15, 0.82, 0.88, 6),
    ("라이브2d 리깅 추천",    "확장검색", 0, .12, 0.70, 1.18, 5),
    ("버튜버 모델 제작",      "구문검색", 1, .38, 1.20, 0.96, 8),
    ("vtuber 모델링",       "확장검색", 1, .26, 0.85, 1.12, 6),
    ("버튜버 커미션",        "확장검색", 1, .21, 0.95, 1.08, 7),
    ("버튜버 일러스트 리깅",   "확장검색", 1, .15, 0.72, 1.22, 5),
    ("몽글 스튜디오",         "완전일치", 2, .72, 1.10, 0.90, 10),
    ("몽글 리깅",            "구문검색", 2, .28, 0.95, 1.00, 9),
]

SEARCH_TERMS = [
    ("live2d 리깅 외주 가격", "live2d 리깅", 412, 26, 2),
    ("버튜버 모델 제작해주는곳", "버튜버 모델 제작", 388, 19, 1),
    ("라이브2d 리깅 잘하는곳", "라이브2d 외주", 274, 21, 2),
    ("live2d 리깅 얼마", "리깅 가격", 233, 9, 0),
    ("버튜버 모델 커미션 오픈", "버튜버 커미션", 198, 12, 1),
    ("live2d 무료 리깅", "live2d 리깅", 186, 4, 0),
    ("몽글스튜디오", "몽글 스튜디오", 164, 21, 3),
    ("vtuber 모델 만들기", "vtuber 모델링", 152, 6, 0),
    ("버튜버 리깅 독학", "라이브2d 리깅 추천", 141, 3, 0),
    ("live2d 리깅 포트폴리오", "live2d 커미션", 128, 11, 1),
]

DEVICES = [("휴대전화", .62), ("컴퓨터", .33), ("태블릿", .05)]
DEV_MULT = {"휴대전화": (1.05, 0.88), "컴퓨터": (0.88, 1.35), "태블릿": (0.72, 0.75)}

HOUR_W = [.28, .20, .15, .12, .11, .14, .25, .42, .58, .66, .72, .78,
          .84, .82, .80, .84, .92, 1.12, 1.38, 1.55, 1.62, 1.48, 1.10, .58]
DOW_W = [1.02, 1.08, 0.98, 1.12, 1.05, 0.88, 0.82]   # 월~일


def _rnd(i: int) -> float:
    x = math.sin(i * 91.7 + 47.3) * 28461.1937
    return x - math.floor(x)


@st.cache_data
def build_ads(today: date):
    """일별 × 캠페인 × 기기 성과. 날짜가 같으면 결과도 같습니다."""
    rows, k = [], 0
    for ago in range(55, -1, -1):
        d = today - timedelta(days=ago)
        ramp = 0.45 + (1 - ago / 55) * 0.85          # 초반엔 학습기간이라 적게 씀
        for nm, typ, budget, cpc0, ctr0, cvr0, val, _is in CAMPAIGNS:
            for dev, share in DEVICES:
                k += 1
                dm_ctr, dm_cvr = DEV_MULT[dev]
                spend = budget * share * ramp * DOW_W[d.weekday()] * (0.72 + _rnd(k) * 0.5)
                spend = min(spend, budget * share * 1.02)      # 예산을 넘지 않게
                cpc = cpc0 * (0.85 + _rnd(k + 1) * 0.35)
                clicks = max(0, round(spend / cpc))
                ctr = ctr0 * dm_ctr * (0.85 + _rnd(k + 2) * 0.32)
                imps = round(clicks / (ctr / 100)) if clicks else round(spend / cpc * 20)
                cvr = cvr0 * dm_cvr * (0.7 + _rnd(k + 3) * 0.7)
                # 하루·기기 단위로는 전환이 0.4건처럼 나옵니다. 그냥 반올림하면
                # 전부 0이 되어 합계가 사라지므로 소수부는 확률로 처리합니다.
                cf = clicks * cvr / 100
                conv = int(cf) + (1 if _rnd(k + 4) < (cf - int(cf)) else 0)
                rows.append({
                    "날짜": d, "캠페인": nm, "유형": typ, "기기": dev,
                    "노출": imps, "클릭": clicks, "비용": round(spend),
                    "전환": conv, "전환가치": conv * val, "예산": budget,
                })
    df = pd.DataFrame(rows)

    tot = df[["노출", "클릭", "비용", "전환"]].sum()
    ws = sum(HOUR_W)
    hours = pd.DataFrame([{
        "시": h,
        "노출": round(tot["노출"] * HOUR_W[h] / ws),
        "클릭": round(tot["클릭"] * HOUR_W[h] / ws * (0.9 + HOUR_W[h] * 0.12)),
        "비용": round(tot["비용"] * HOUR_W[h] / ws),
        "전환": round(tot["전환"] * HOUR_W[h] / ws * (0.85 + HOUR_W[h] * 0.18)),
    } for h in range(24)])
    return df, hours


def _agg(df):
    if df.empty:
        return dict(imp=0, clk=0, cost=0, conv=0, val=0, ctr=None,
                    cpc=None, cvr=None, cpa=None, roas=None)
    imp, clk = int(df["노출"].sum()), int(df["클릭"].sum())
    cost, conv = int(df["비용"].sum()), int(df["전환"].sum())
    val = int(df["전환가치"].sum())
    return dict(imp=imp, clk=clk, cost=cost, conv=conv, val=val,
                ctr=clk / imp * 100 if imp else None,
                cpc=cost / clk if clk else None,
                cvr=conv / clk * 100 if clk else None,
                cpa=cost / conv if conv else None,
                roas=val / cost * 100 if cost else None)


def _fmt(n, dec=0):
    return "—" if n is None else f"{n:,.{dec}f}"


def _dlt(now, before):
    if not before or now is None:
        return None
    return f"{(now - before) / before * 100:+.1f}%"


# ══════════════════════════════════════════════════════════════
def render_ads_tab(today: date, days: int):
    """app.py 의 〈광고 성과〉 탭 본문."""
    DF, HOURS = build_ads(today)
    span_days = days if days else 56

    c = st.columns([1.4, 1.4, 2])
    with c[0]:
        types = st.multiselect("캠페인 유형", ["검색", "디스플레이", "동영상"],
                               default=["검색", "디스플레이", "동영상"], key="ads_types")
    with c[1]:
        devs = st.multiselect("기기", [d for d, _ in DEVICES],
                              default=[d for d, _ in DEVICES], key="ads_devs")
    types = types or ["검색", "디스플레이", "동영상"]
    devs = devs or [d for d, _ in DEVICES]

    frm = today - timedelta(days=span_days - 1)
    D = DF[(DF["날짜"] >= frm) & (DF["유형"].isin(types)) & (DF["기기"].isin(devs))].copy()
    PREV = DF[(DF["날짜"] >= today - timedelta(days=span_days * 2 - 1)) & (DF["날짜"] < frm)
              & (DF["유형"].isin(types)) & (DF["기기"].isin(devs))].copy()
    CUR, WAS = _agg(D), _agg(PREV)

    with c[2]:
        st.caption(f"최근 {span_days}일 · 캠페인 {D['캠페인'].nunique()}개 · "
                   f"광고비 {_fmt(CUR['cost'])}원")

    if D.empty:
        st.info("고른 조건에 해당하는 광고 기록이 없습니다.")
        return

    # ── KPI 10칸
    a = st.columns(5)
    a[0].metric("노출수", _fmt(CUR["imp"]), _dlt(CUR["imp"], WAS["imp"]),
                help="광고가 화면에 뜬 횟수")
    a[1].metric("클릭수", _fmt(CUR["clk"]), _dlt(CUR["clk"], WAS["clk"]),
                help="광고를 눌러 사이트로 들어온 횟수")
    a[2].metric("CTR", f"{CUR['ctr']:.2f}%" if CUR["ctr"] else "—",
                _dlt(CUR["ctr"], WAS["ctr"]), help="클릭 ÷ 노출. 광고 문구가 끌리는지를 봅니다")
    a[3].metric("평균 CPC", f"{_fmt(CUR['cpc'])}원", _dlt(CUR["cpc"], WAS["cpc"]),
                delta_color="inverse", help="클릭 한 번에 든 돈. 경쟁이 셀수록 올라갑니다")
    a[4].metric("총 비용", f"{_fmt(CUR['cost'])}원", _dlt(CUR["cost"], WAS["cost"]),
                delta_color="inverse", help="이 기간에 실제로 쓴 광고비")

    b = st.columns(5)
    b[0].metric("전환수", _fmt(CUR["conv"]), _dlt(CUR["conv"], WAS["conv"]),
                help="문의·구매까지 이어진 건수")
    b[1].metric("전환율", f"{CUR['cvr']:.2f}%" if CUR["cvr"] else "—",
                _dlt(CUR["cvr"], WAS["cvr"]), help="전환 ÷ 클릭. 들어온 뒤 실제로 행동한 비율")
    b[2].metric("CPA", f"{_fmt(CUR['cpa'])}원", _dlt(CUR["cpa"], WAS["cpa"]),
                delta_color="inverse", help="전환 1건을 얻는 데 든 돈. 낮을수록 좋습니다")
    b[3].metric("전환 가치", f"{_fmt(CUR['val'])}원", _dlt(CUR["val"], WAS["val"]),
                help="전환으로 생긴 매출(예상)")
    b[4].metric("ROAS", f"{CUR['roas']:.0f}%" if CUR["roas"] else "—",
                _dlt(CUR["roas"], WAS["roas"]),
                help="광고비 대비 매출. 100%면 본전, 400%면 1원 써서 4원 번 것")

    if CUR["roas"]:
        st.caption(f"광고비 {_fmt(CUR['cost'])}원을 써서 {_fmt(CUR['val'])}원어치 전환이 생겼습니다 "
                   f"— **1원당 {CUR['roas'] / 100:.1f}원**.")

    st.divider()

    # ── 일별 비용 vs 전환
    st.markdown("#### 날마다 얼마 쓰고 몇 건 얻었나")
    g = D.groupby("날짜").agg({"비용": "sum", "전환": "sum"}).reset_index()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=g["날짜"], y=g["비용"], name="비용",
                         marker_color="rgba(22,104,201,.28)",
                         hovertemplate="%{x|%m/%d}<br>비용 %{y:,.0f}원<extra></extra>"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=g["날짜"], y=g["전환"], name="전환", mode="lines+markers",
                             line=dict(color=GREEN, width=3), marker=dict(size=6),
                             hovertemplate="%{x|%m/%d}<br>전환 %{y}건<extra></extra>"),
                  secondary_y=True)
    fig.update_layout(height=300, hovermode="x unified", legend=LEGEND_TOP, **BASE)
    fig.update_yaxes(title_text="비용(원)", gridcolor=GRID, secondary_y=False)
    fig.update_yaxes(title_text="전환(건)", gridcolor="rgba(0,0,0,0)", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("파란 막대가 쓴 돈, 초록 선이 얻은 건수입니다. "
               "**막대는 높은데 선이 낮은 날**이 돈이 새는 날입니다.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 유형별로 돈이 어디로 갔나")
        byt = D.groupby("유형")["비용"].sum().reset_index()
        fig = go.Figure(go.Pie(labels=byt["유형"], values=byt["비용"], hole=.58,
                               marker=dict(colors=[TYPE_COLOR[t] for t in byt["유형"]]),
                               textinfo="percent",
                               hovertemplate="%{label}<br>%{value:,.0f}원<extra></extra>"))
        fig.update_layout(height=250, **BASE)
        fig.add_annotation(text=f"<b>{_fmt(CUR['cost'])}</b><br>"
                                f"<span style='font-size:10px'>총 광고비</span>",
                           showarrow=False, font=dict(size=15))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("##### 깔때기 — 어디서 빠지나")
        fig = go.Figure(go.Funnel(y=["노출", "클릭", "전환"],
                                  x=[CUR["imp"], CUR["clk"], CUR["conv"]],
                                  textinfo="value+percent previous",
                                  marker=dict(color=[BLUE, YELLOW, GREEN])))
        fig.update_layout(height=250, **BASE)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("퍼센트는 바로 위 단계 대비입니다. 클릭이 낮으면 **광고 문구**, "
                   "전환이 낮으면 **도착 페이지**가 문제입니다.")

    st.divider()

    # ── 캠페인별
    st.markdown("#### 캠페인별 성과")
    cam = D.groupby(["캠페인", "유형"]).agg(
        노출=("노출", "sum"), 클릭=("클릭", "sum"), 비용=("비용", "sum"),
        전환=("전환", "sum"), 전환가치=("전환가치", "sum"), 예산=("예산", "first"),
    ).reset_index()
    cam["CTR"] = (cam["클릭"] / cam["노출"] * 100).round(2)
    cam["평균CPC"] = (cam["비용"] / cam["클릭"]).round(0)
    cam["전환율"] = (cam["전환"] / cam["클릭"] * 100).round(2)
    cam["CPA"] = cam.apply(lambda r: round(r["비용"] / r["전환"]) if r["전환"] else None, axis=1)
    cam["ROAS"] = (cam["전환가치"] / cam["비용"] * 100).round(0)
    cam = cam.sort_values("비용", ascending=False)

    st.dataframe(
        cam[["캠페인", "유형", "노출", "클릭", "CTR", "평균CPC", "비용",
             "전환", "전환율", "CPA", "ROAS"]],
        use_container_width=True, hide_index=True,
        column_config={
            "CTR": st.column_config.NumberColumn(format="%.2f%%"),
            "평균CPC": st.column_config.NumberColumn(format="%d원"),
            "비용": st.column_config.NumberColumn(format="%d원"),
            "전환율": st.column_config.NumberColumn(format="%.2f%%"),
            "CPA": st.column_config.NumberColumn(format="%d원"),
            "ROAS": st.column_config.ProgressColumn(
                format="%d%%", min_value=0, max_value=float(max(cam["ROAS"].max(), 100))),
        })

    best, worst = cam.loc[cam["ROAS"].idxmax()], cam.loc[cam["ROAS"].idxmin()]
    st.caption(f"**{best['캠페인']}** 이 가장 남습니다 (ROAS {best['ROAS']:.0f}%). "
               f"**{worst['캠페인']}** 은 {worst['ROAS']:.0f}% 로 가장 낮습니다 — "
               f"예산을 옮기거나 광고 문구를 바꿔볼 자리입니다.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 예산을 얼마나 쓰고 있나")
        span = D["날짜"].nunique()
        for _, r in cam.iterrows():
            used = r["비용"] / (r["예산"] * span) if span else 0
            st.progress(min(1.0, used),
                        text=f"{r['캠페인']} · 하루 {r['예산']:,}원 중 {used * 100:.0f}% 소진")
        st.caption("100% 에 가까우면 **예산이 모자라 광고가 멈추고 있다**는 뜻입니다. "
                   "ROAS 가 높은 캠페인이 100% 라면 예산을 올릴 자리입니다.")
    with c2:
        st.markdown("##### 노출 점유율 — 뜰 수 있었는데 못 뜬 비율")
        isr = pd.DataFrame([{"캠페인": x[0], "점유율": x[7]} for x in CAMPAIGNS
                            if x[0] in set(cam["캠페인"])]).sort_values("점유율")
        fig = go.Figure()
        fig.add_trace(go.Bar(y=isr["캠페인"], x=isr["점유율"], orientation="h",
                             marker_color=BLUE, text=[f"{v}%" for v in isr["점유율"]],
                             textposition="inside", name="차지"))
        fig.add_trace(go.Bar(y=isr["캠페인"], x=100 - isr["점유율"], orientation="h",
                             marker_color="#eaecf2", name="놓침",
                             hovertemplate="놓침 %{x}%<extra></extra>"))
        fig.update_layout(height=260, barmode="stack", showlegend=False, **BASE)
        fig.update_xaxes(range=[0, 100], ticksuffix="%", gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("내 광고가 뜰 수 있었던 기회 중 실제로 뜬 비율입니다. "
                   "낮으면 **예산이 부족하거나 입찰가가 낮은** 것입니다.")

    st.divider()

    # ── 키워드
    st.markdown("#### 키워드별 성과")
    krows = []
    for i, (kw, mt, ci, share, ctrm, cpcm, qs) in enumerate(KEYWORDS):
        nm, typ, budget, cpc0, ctr0, cvr0, val, _ = CAMPAIGNS[ci]
        if typ not in types or nm not in set(cam["캠페인"]):
            continue
        base = cam[cam["캠페인"] == nm].iloc[0]
        imp = round(base["노출"] * share)
        ctr = ctr0 * ctrm * (0.92 + _rnd(i * 7) * 0.18)
        clk = max(1, round(imp * ctr / 100))
        cpc = cpc0 * cpcm * (0.9 + _rnd(i * 11) * 0.2)
        cost = round(clk * cpc)
        conv = round(clk * cvr0 * (0.75 + _rnd(i * 13) * 0.6) / 100)
        krows.append({"키워드": kw, "매치 타입": mt, "캠페인": nm.split("] ")[-1],
                      "노출": imp, "클릭": clk, "CTR": round(ctr, 2), "평균CPC": round(cpc),
                      "비용": cost, "전환": conv,
                      "CPA": round(cost / conv) if conv else None, "품질평가점수": qs})
    if krows:
        kdf = pd.DataFrame(krows).sort_values("비용", ascending=False)
        st.dataframe(
            kdf, use_container_width=True, hide_index=True,
            column_config={
                "CTR": st.column_config.NumberColumn(format="%.2f%%"),
                "평균CPC": st.column_config.NumberColumn(format="%d원"),
                "비용": st.column_config.NumberColumn(format="%d원"),
                "CPA": st.column_config.NumberColumn(format="%d원"),
                "품질평가점수": st.column_config.ProgressColumn(
                    format="%d/10", min_value=0, max_value=10),
            })
        low = kdf[kdf["품질평가점수"] <= 5]
        if not low.empty:
            st.caption(f"**품질평가점수가 5 이하인 키워드 {len(low)}개** — "
                       f"{', '.join(low['키워드'].head(3))}. 점수가 낮으면 같은 자리를 얻는 데 "
                       f"**돈을 더 내야 합니다.** 광고 문구와 도착 페이지를 그 키워드에 맞추면 오릅니다.")

        with st.expander("사람들이 실제로 검색한 말 (검색어 보고서)"):
            sdf = pd.DataFrame(SEARCH_TERMS,
                               columns=["검색어", "걸린 키워드", "노출", "클릭", "전환"])
            sdf["CTR"] = (sdf["클릭"] / sdf["노출"] * 100).round(2)
            st.dataframe(sdf[["검색어", "걸린 키워드", "노출", "클릭", "CTR", "전환"]],
                         use_container_width=True, hide_index=True,
                         column_config={"CTR": st.column_config.NumberColumn(format="%.2f%%")})
            st.caption("「live2d 무료 리깅」·「버튜버 리깅 독학」처럼 **살 생각이 없는 검색**에도 "
                       "광고가 나가고 있습니다. 이런 말은 **제외 키워드**로 막으면 돈이 굳습니다.")
    else:
        st.info("검색 캠페인을 켜면 키워드 성과가 나옵니다.")

    st.divider()

    # ── 시간대
    st.markdown("#### 몇 시에 광고가 잘 먹히나")
    h = HOURS.copy()
    peak = int(h.loc[h["전환"].idxmax(), "시"])
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=h["시"], y=h["전환"], name="전환",
                         marker_color=[GREEN if x == peak else "rgba(44,157,93,.35)" for x in h["시"]],
                         hovertemplate="%{x}시<br>전환 %{y}건<extra></extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(x=h["시"], y=h["비용"], name="비용", mode="lines",
                             line=dict(color=BLUE, width=2.5),
                             hovertemplate="%{x}시<br>비용 %{y:,.0f}원<extra></extra>"), secondary_y=True)
    fig.update_layout(height=280, hovermode="x unified", legend=LEGEND_TOP, **BASE)
    fig.update_xaxes(dtick=2, ticksuffix="시", gridcolor=GRID)
    fig.update_yaxes(title_text="전환(건)", gridcolor=GRID, secondary_y=False)
    fig.update_yaxes(title_text="비용(원)", gridcolor="rgba(0,0,0,0)", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"**{peak}시** 에 전환이 가장 많습니다. 광고 일정에서 이 시간대 입찰가를 올리고, "
               f"새벽(0~5시)처럼 돈만 나가고 전환이 없는 시간은 낮추거나 꺼두면 됩니다.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 기기별")
        dev = D.groupby("기기").agg(노출=("노출", "sum"), 클릭=("클릭", "sum"),
                                   비용=("비용", "sum"), 전환=("전환", "sum")).reset_index()
        dev["CTR"] = (dev["클릭"] / dev["노출"] * 100).round(2)
        dev["전환율"] = (dev["전환"] / dev["클릭"] * 100).round(2)
        dev["CPA"] = dev.apply(lambda r: round(r["비용"] / r["전환"]) if r["전환"] else None, axis=1)
        st.dataframe(dev[["기기", "노출", "클릭", "CTR", "비용", "전환", "전환율", "CPA"]],
                     use_container_width=True, hide_index=True,
                     column_config={
                         "CTR": st.column_config.NumberColumn(format="%.2f%%"),
                         "전환율": st.column_config.NumberColumn(format="%.2f%%"),
                         "비용": st.column_config.NumberColumn(format="%d원"),
                         "CPA": st.column_config.NumberColumn(format="%d원"),
                     })
        if len(dev) > 1:
            bd = dev.loc[dev["전환율"].idxmax()]
            st.caption(f"**{bd['기기']}** 의 전환율이 {bd['전환율']:.2f}% 로 가장 높습니다. "
                       f"클릭은 휴대전화가 많아도 **실제로 계약까지 가는 건 컴퓨터**인 경우가 흔합니다.")
    with c2:
        st.markdown("##### 요일별 CPA — 한 건 얻는 데 든 돈")
        dw = D.copy()
        dw["요일"] = dw["날짜"].apply(lambda x: WD[x.weekday()])
        dg = dw.groupby("요일").agg(비용=("비용", "sum"), 전환=("전환", "sum")).reindex(WD)
        dg["CPA"] = (dg["비용"] / dg["전환"]).round(0)
        cheapest = dg["CPA"].idxmin()
        fig = go.Figure(go.Bar(x=dg.index, y=dg["CPA"],
                               marker_color=[GREEN if i == cheapest else BLUE for i in dg.index],
                               text=[f"{v:,.0f}" for v in dg["CPA"]], textposition="outside",
                               hovertemplate="%{x}요일<br>CPA %{y:,.0f}원<extra></extra>"))
        fig.update_layout(height=270, **BASE)
        fig.update_yaxes(gridcolor=GRID, title_text="원")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"막대가 **낮을수록 싸게 얻은 날**입니다. **{cheapest}요일**이 가장 쌉니다.")

    st.divider()
    st.markdown("#### 요일 × 시간대 — 광고 일정 짜기")
    tot_conv = D["전환"].sum()
    z, txt = [], []
    for wi in range(7):
        rz, rt = [], []
        for hh in range(0, 24, 2):
            w = (HOUR_W[hh] + HOUR_W[hh + 1]) / 2 * DOW_W[wi]
            v = tot_conv * w / (sum(HOUR_W) / 2 * sum(DOW_W)) * 2
            rz.append(v)
            rt.append(f"{v:,.0f}")
        z.append(rz)
        txt.append(rt)
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"{hh}-{hh + 2}시" for hh in range(0, 24, 2)], y=WD,
        text=txt, texttemplate="%{text}",
        colorscale=[[0, "rgba(22,104,201,.06)"], [1, BLUE]],
        hovertemplate="%{y}요일 %{x}<br>전환 %{z:,.0f}건<extra></extra>",
        showscale=False, xgap=3, ygap=3))
    fig.update_layout(height=300, **BASE)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("진한 칸이 전환이 잘 나오는 시간입니다. 구글 애즈의 **〈광고 일정〉** 에서 "
               "이 시간대에 입찰가를 올리고, 옅은 칸은 낮추면 같은 돈으로 더 얻습니다.")
