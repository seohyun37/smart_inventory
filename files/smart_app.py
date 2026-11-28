import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib import font_manager

# ------------------------------------------------------------------
# 기본 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="Smart Inventory", page_icon="📦", layout="wide")

# 설치된 한글 폰트만 골라서 사용 (경고 메시지 방지)
_installed = {f.name for f in font_manager.fontManager.ttflist}
for _name in ["Malgun Gothic", "AppleGothic", "NanumGothic"]:
    if _name in _installed:
        plt.rcParams["font.family"] = _name
        break
plt.rcParams["axes.unicode_minus"] = False

INV_COLS = ["SKU", "ProductName", "Category", "Stock", "UnitPrice", "LeadTime"]
SALES_COLS = ["Date", "SKU", "Qty"]

# 색상 팔레트
NAVY, BLUE, SKY = "#1E3A8A", "#3B82F6", "#BFDBFE"
RED, AMBER, GREEN, GRAY = "#EF4444", "#F59E0B", "#10B981", "#94A3B8"

# ------------------------------------------------------------------
# 디자인 (CSS)
# ------------------------------------------------------------------
st.markdown(
    """
<style>
.block-container {padding-top: 1.6rem; max-width: 1300px;}
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}

.hero {background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
       padding: 26px 32px; border-radius: 18px; margin-bottom: 22px;
       box-shadow: 0 6px 18px rgba(30,58,138,.25);}
.hero h1 {color: #fff; margin: 0; padding: 0; font-size: 2rem; font-weight: 800;}
.hero p  {color: #DBEAFE; margin: 6px 0 0 0; font-size: 1rem;}

[data-testid="stMetric"] {background: rgba(128,128,128,.07);
       border: 1px solid rgba(128,128,128,.22); border-radius: 14px;
       padding: 16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,.05);}
[data-testid="stMetricLabel"] {font-weight: 600; opacity: .75;}
[data-testid="stMetricValue"] {font-weight: 800;}

.alert-card {background: rgba(128,128,128,.07); padding: 12px 16px;
       border-radius: 10px; margin-bottom: 10px; line-height: 1.5;}
.alert-card .sub {opacity: .8; font-size: .92rem;}

h2, h3 {font-weight: 700 !important;}
[data-testid="stSidebar"] {border-right: 1px solid rgba(128,128,128,.2);}
.stButton > button, .stDownloadButton > button {border-radius: 10px; font-weight: 600;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero"><h1>📦 Smart Inventory</h1>'
    "<p>판매 데이터 기반 재고관리 &amp; 발주 의사결정 시스템</p></div>",
    unsafe_allow_html=True,
)


def alert_card(title, body, color):
    st.markdown(
        f'<div class="alert-card" style="border-left:5px solid {color}">'
        f'<b>{title}</b><br><span class="sub">{body}</span></div>',
        unsafe_allow_html=True,
    )


def new_fig(w=8, h=4):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#CBD5E1")
    ax.tick_params(colors="#475569", labelsize=9)
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.8)
    ax.set_axisbelow(True)
    return fig, ax


def show_fig(fig):
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


# ------------------------------------------------------------------
# 데이터 로딩
# ------------------------------------------------------------------
def read_csv_safe(path_or_file):
    for enc in ("utf-8-sig", "cp949"):
        try:
            if hasattr(path_or_file, "seek"):
                path_or_file.seek(0)
            return pd.read_csv(path_or_file, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("파일 인코딩을 읽을 수 없습니다.")


def make_sample_data():
    """내장 샘플 데이터 (CSV 파일이 없어도 바로 시연 가능). 시드를 고정해 항상 같은 데이터가 나옵니다."""
    rng = np.random.default_rng(42)
    products = [
        ("SKU-001", "무선 이어폰", "전자기기", 120, 45000, 5, 20),
        ("SKU-002", "보조배터리", "전자기기", 400, 25000, 7, 30),
        ("SKU-003", "텀블러", "생활용품", 90, 15000, 4, 18),
        ("SKU-004", "물티슈(10팩)", "생활용품", 700, 8000, 3, 60),
        ("SKU-005", "요가매트", "스포츠", 35, 22000, 10, 6),
        ("SKU-006", "프로틴바(박스)", "식품", 150, 18000, 6, 22),
        ("SKU-007", "USB-C 케이블", "전자기기", 260, 7000, 5, 35),
        ("SKU-008", "에코백", "패션잡화", 500, 9000, 8, 14),
    ]
    inv = pd.DataFrame(products, columns=INV_COLS + ["_mu"])
    dates = pd.date_range("2026-08-26", periods=90, freq="D")
    rows = []
    for _, p in inv.iterrows():
        weekly = np.where(dates.dayofweek >= 5, 1.3, 1.0)  # 주말 수요 증가
        trend = np.linspace(0.9, 1.15, len(dates)) if p.SKU in ("SKU-001", "SKU-006") else 1.0
        qty = rng.poisson(p["_mu"] * weekly * trend)
        rows += [(d, p.SKU, int(q)) for d, q in zip(dates, qty)]
    sales = pd.DataFrame(rows, columns=SALES_COLS)
    return inv.drop(columns="_mu"), sales


def init_state():
    # 기본값 = 내장 샘플 데이터. 데이터 관리 화면에서 CSV를 업로드하면 교체됩니다.
    if "inv" not in st.session_state or "sales" not in st.session_state:
        st.session_state.inv, st.session_state.sales = make_sample_data()


def check_columns(df, required, name):
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"❌ {name}에 필요한 컬럼이 없습니다: {', '.join(missing)}")
        return False
    return True


init_state()


# ------------------------------------------------------------------
# 핵심 SCM 알고리즘
# ------------------------------------------------------------------
def compute_scm(inv, sales, z, order_cost, holding_rate):
    pivot = sales.pivot_table(index="Date", columns="SKU", values="Qty", aggfunc="sum").fillna(0)
    daily_mean = pivot.mean()
    daily_std = pivot.std().fillna(0)

    out = inv.copy()
    out["DailyDemand"] = out["SKU"].map(daily_mean).fillna(0).round(2)
    out["DemandStd"] = out["SKU"].map(daily_std).fillna(0).round(2)
    out["SafetyStock"] = np.ceil(z * out["DemandStd"] * np.sqrt(out["LeadTime"])).astype(int)
    out["ROP"] = np.ceil(out["DailyDemand"] * out["LeadTime"] + out["SafetyStock"]).astype(int)

    annual = out["DailyDemand"] * 365
    holding = (out["UnitPrice"] * holding_rate).replace(0, np.nan)
    out["EOQ"] = np.ceil(np.sqrt(2 * annual * order_cost / holding)).fillna(0).astype(int)

    out["TargetInventory"] = out["ROP"] + out["EOQ"]
    out["Status"] = np.where(
        out["Stock"] <= out["ROP"], "🚨 긴급 발주",
        np.where(out["Stock"] <= out["ROP"] * 1.2, "⚠️ 주의", "✅ 적정"),
    )
    out["StatusText"] = out["Status"].str.replace(r"^\S+\s", "", regex=True)
    out["Recommended_Order"] = np.where(
        out["Stock"] <= out["ROP"], (out["TargetInventory"] - out["Stock"]).clip(lower=0), 0
    ).astype(int)
    out["OrderCost"] = out["Recommended_Order"] * out["UnitPrice"]
    out["DaysOfStock"] = np.where(out["DailyDemand"] > 0, out["Stock"] / out["DailyDemand"], np.nan).round(1)
    out["StockRatio"] = np.where(out["ROP"] > 0, out["Stock"] / out["ROP"], 0).round(2)
    return out


def highlight_status(row):
    if row["Status"].startswith("🚨"):
        return ["background-color: #FEE2E2"] * len(row)
    if row["Status"].startswith("⚠️"):
        return ["background-color: #FEF3C7"] * len(row)
    return [""] * len(row)


# ------------------------------------------------------------------
# 사이드바
# ------------------------------------------------------------------
st.sidebar.markdown("## 📦 Smart Inventory")
menu = st.sidebar.radio(
    "메뉴",
    ["📊 대시보드", "📦 재고 관리", "📈 수요 분석", "⚙️ 재주문점·발주 추천", "🗄️ 데이터 관리"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
with st.sidebar.expander("🎛️ 알고리즘 파라미터", expanded=True):
    service_level = st.select_slider(
        "목표 서비스 수준", options=[0.90, 0.95, 0.975, 0.99], value=0.95,
        format_func=lambda v: f"{v*100:.1f}%",
    )
    z = {0.90: 1.28, 0.95: 1.65, 0.975: 1.96, 0.99: 2.33}[service_level]
    order_cost = st.number_input("1회 발주 비용 S (원)", min_value=0, value=50000, step=5000)
    holding_rate = st.slider("연 재고 보관비율 H (단가 대비)", 0.05, 0.50, 0.20, 0.05)

inv, sales = st.session_state.inv, st.session_state.sales

if menu != "🗄️ 데이터 관리":
    if inv is None or sales is None:
        st.warning("⚠️ 데이터가 없습니다. '🗄️ 데이터 관리' 화면에서 inventory.csv와 sales_data.csv를 업로드해 주세요.")
        st.stop()
    if not (check_columns(inv, INV_COLS, "재고 데이터") and check_columns(sales, SALES_COLS, "판매 데이터")):
        st.stop()
    calc = compute_scm(inv, sales, z, order_cost, holding_rate)


# ------------------------------------------------------------------
# 1. 대시보드
# ------------------------------------------------------------------
if menu == "📊 대시보드":
    urgent = calc[calc["Status"].str.startswith("🚨")]
    warn = calc[calc["Status"].str.startswith("⚠️")]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("등록 상품 수", f"{len(calc)} 개")
    c2.metric("총 재고 자산 가치", f"{(calc['Stock'] * calc['UnitPrice']).sum():,.0f} 원")
    c3.metric("🚨 긴급 발주 상품", f"{len(urgent)} 개", delta=f"주의 {len(warn)}개", delta_color="off")
    c4.metric("예상 발주 비용", f"{calc['OrderCost'].sum():,.0f} 원")

    st.write("")
    left, right = st.columns([1.15, 1])
    with left:
        st.subheader("🚨 발주 필요 상품")
        if urgent.empty and warn.empty:
            st.success("재주문점 이하로 떨어진 상품이 없습니다. 👍")
        for _, r in urgent.sort_values("DaysOfStock").iterrows():
            alert_card(
                f"{r['ProductName']} <span style='opacity:.6'>({r['SKU']})</span>",
                f"현재고 {r['Stock']}개 ≤ ROP {r['ROP']}개 · 약 {r['DaysOfStock']}일치 재고 "
                f"→ <b style='color:{RED}'>{r['Recommended_Order']}개 발주 권장</b>",
                RED,
            )
        for _, r in warn.iterrows():
            alert_card(
                f"{r['ProductName']} <span style='opacity:.6'>({r['SKU']})</span>",
                f"ROP 근접 · 현재고 {r['Stock']}개 / ROP {r['ROP']}개",
                AMBER,
            )

    with right:
        st.subheader("📊 재고 상태 비율")
        order = ["긴급 발주", "주의", "적정"]
        colors = {"긴급 발주": RED, "주의": AMBER, "적정": GREEN}
        counts = calc["StatusText"].value_counts().reindex(order).fillna(0)
        counts = counts[counts > 0]
        fig, ax = plt.subplots(figsize=(5, 3.6))
        ax.pie(
            counts.values, labels=counts.index, colors=[colors[k] for k in counts.index],
            startangle=90, counterclock=False, autopct=lambda p: f"{p:.0f}%",
            pctdistance=0.8, textprops={"fontsize": 10, "color": "#334155"},
            wedgeprops=dict(width=0.38, edgecolor="white", linewidth=2),
        )
        ax.text(0, 0, f"{len(calc)}\n상품", ha="center", va="center", fontsize=15, fontweight="bold", color=NAVY)
        show_fig(fig)

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        st.subheader("💰 카테고리별 재고 자산")
        asset = ((calc["Stock"] * calc["UnitPrice"]).groupby(calc["Category"]).sum() / 10000).sort_values()
        fig, ax = new_fig(6, 3.6)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color="#E2E8F0")
        bars = ax.barh(asset.index, asset.values, color=BLUE, height=0.6)
        ax.bar_label(bars, labels=[f"{v:,.0f}" for v in asset.values], padding=4, fontsize=9, color="#475569")
        ax.set_xlabel("재고 자산 (만 원)", color="#475569")
        ax.set_xlim(0, asset.max() * 1.18)
        show_fig(fig)
    with b:
        st.subheader("⏳ 재고 소진 예상일 vs 리드타임")
        d = calc.sort_values("DaysOfStock", ascending=False)
        fig, ax = new_fig(6, 3.6)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color="#E2E8F0")
        cols = [RED if (x < lt) else BLUE for x, lt in zip(d["DaysOfStock"], d["LeadTime"])]
        ax.barh(d["ProductName"], d["DaysOfStock"], color=cols, height=0.6)
        ax.scatter(d["LeadTime"], d["ProductName"], marker="|", s=300, color=NAVY, linewidths=3, zorder=3, label="리드타임")
        ax.set_xlabel("남은 재고 일수 (빨강 = 리드타임 안에 소진)", color="#475569")
        ax.legend(frameon=False, loc="lower right")
        show_fig(fig)

# ------------------------------------------------------------------
# 2. 재고 관리
# ------------------------------------------------------------------
elif menu == "📦 재고 관리":
    st.subheader("📦 상품 마스터 및 현재고 관리")
    st.caption("표의 셀을 직접 수정하거나 행을 추가/삭제한 뒤 '저장'을 누르면 모든 화면에 즉시 반영됩니다.")

    cats = sorted(inv["Category"].dropna().unique())
    sel = st.multiselect("카테고리 필터", cats, default=cats)
    view = inv[inv["Category"].isin(sel)]

    edited = st.data_editor(
        view,
        num_rows="dynamic",
        column_config={
            "SKU": st.column_config.TextColumn("SKU"),
            "ProductName": st.column_config.TextColumn("상품명"),
            "Category": st.column_config.TextColumn("카테고리"),
            "Stock": st.column_config.NumberColumn("현재고", min_value=0, step=1),
            "UnitPrice": st.column_config.NumberColumn("단가(원)", min_value=0, format="%d"),
            "LeadTime": st.column_config.NumberColumn("리드타임(일)", min_value=1, step=1),
        },
        key="inv_editor",
    )

    c1, c2, _ = st.columns([1, 1.3, 3])
    if c1.button("💾 변경사항 저장", type="primary"):
        if edited["SKU"].isna().any() or edited["SKU"].duplicated().any():
            st.error("SKU는 비어 있거나 중복될 수 없습니다.")
        else:
            rest = inv[~inv["Category"].isin(sel)]
            st.session_state.inv = pd.concat([rest, edited], ignore_index=True)
            st.success("저장되었습니다!")
            st.rerun()
    c2.download_button("⬇️ 재고 CSV 다운로드", inv.to_csv(index=False).encode("utf-8-sig"), "inventory.csv")

# ------------------------------------------------------------------
# 3. 수요 분석
# ------------------------------------------------------------------
elif menu == "📈 수요 분석":
    st.subheader("📈 상품별 수요 추이 분석")

    names = dict(zip(inv["SKU"], inv["ProductName"]))
    f1, f2 = st.columns([2, 1])
    sku = f1.selectbox("상품 선택", list(names), format_func=lambda s: f"{names[s]} ({s})")
    unit = f2.radio("집계 단위", ["일별", "주별"], horizontal=True)

    s = sales[sales["SKU"] == sku].set_index("Date")["Qty"].sort_index().resample("D").sum()
    row = calc[calc["SKU"] == sku].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("일평균 수요", f"{row['DailyDemand']:.1f} 개")
    c2.metric("수요 표준편차(σ)", f"{row['DemandStd']:.1f}")
    cv = row["DemandStd"] / row["DailyDemand"] if row["DailyDemand"] else 0
    c3.metric("변동계수(CV)", f"{cv:.2f}", help="σ/평균. 클수록 수요가 불규칙 → 안전재고 증가")

    fig, ax = new_fig(11, 4.2)
    if unit == "일별":
        ax.fill_between(s.index, s.values, color=SKY, alpha=0.6, label="일별 판매량")
        ax.plot(s.index, s.rolling(7).mean(), color=NAVY, linewidth=2.4, label="7일 이동평균")
        ax.axhline(row["DailyDemand"], color=RED, linestyle="--", linewidth=1.4, label="전체 평균")
    else:
        w = s.resample("W").sum()
        ax.bar(w.index, w.values, width=5, color=BLUE, label="주별 판매량")
        ax.axhline(row["DailyDemand"] * 7, color=RED, linestyle="--", linewidth=1.4, label="주 평균")
    ax.set_title(f"{names[sku]} · {unit} 수요 추이", fontsize=13, fontweight="bold", color=NAVY, loc="left")
    ax.set_ylabel("판매량", color="#475569")
    ax.legend(frameon=False, ncol=3, loc="upper right")
    show_fig(fig)

    st.markdown("**📋 전체 상품 수요 통계**")
    st.dataframe(
        calc[["SKU", "ProductName", "DailyDemand", "DemandStd"]],
        column_config={
            "ProductName": "상품명",
            "DailyDemand": st.column_config.NumberColumn("일평균수요", format="%.1f"),
            "DemandStd": st.column_config.NumberColumn("표준편차", format="%.1f"),
        },
        hide_index=True,
    )

# ------------------------------------------------------------------
# 4. 재주문점 · 발주 추천
# ------------------------------------------------------------------
elif menu == "⚙️ 재주문점·발주 추천":
    st.subheader("⚙️ 재주문점(ROP) 및 권장 발주량 산출")
    st.latex(r"SS = z\,\sigma_d\sqrt{L},\quad ROP = \bar{d}\,L + SS,\quad EOQ=\sqrt{\frac{2DS}{H}},\quad Q = (ROP+EOQ) - Stock")
    st.caption(f"서비스 수준 {service_level*100:.1f}% (z={z}) · 발주비용 {order_cost:,}원 · 보관비율 {holding_rate:.0%}")

    n_order = int((calc["Recommended_Order"] > 0).sum())
    k1, k2, k3 = st.columns(3)
    k1.metric("발주 필요 상품", f"{n_order} 개")
    k2.metric("총 권장 발주 수량", f"{calc['Recommended_Order'].sum():,} 개")
    k3.metric("예상 발주 비용", f"{calc['OrderCost'].sum():,.0f} 원")

    show = calc[["SKU", "ProductName", "Stock", "DailyDemand", "LeadTime", "SafetyStock", "ROP", "EOQ",
                 "StockRatio", "Status", "Recommended_Order", "OrderCost"]]
    cfg = {
        "ProductName": "상품명",
        "Stock": "현재고",
        "DailyDemand": st.column_config.NumberColumn("일평균수요", format="%.1f"),
        "LeadTime": "리드타임",
        "SafetyStock": "안전재고",
        "ROP": "재주문점",
        "EOQ": "EOQ",
        "StockRatio": st.column_config.ProgressColumn("재고/ROP", min_value=0, max_value=2, format="%.2f"),
        "Status": "상태",
        "Recommended_Order": "권장발주량",
        "OrderCost": st.column_config.NumberColumn("발주비용(원)", format="%d"),
    }
    try:
        st.dataframe(show.style.apply(highlight_status, axis=1), column_config=cfg, hide_index=True)
    except Exception:
        st.dataframe(show, column_config=cfg, hide_index=True)

    st.download_button(
        "⬇️ 발주 리포트 CSV 다운로드",
        calc[calc["Recommended_Order"] > 0][["SKU", "ProductName", "Recommended_Order", "OrderCost"]]
        .to_csv(index=False).encode("utf-8-sig"),
        "order_report.csv",
    )

    st.markdown("---")
    st.subheader("📊 현재고 vs 재주문점(ROP)")
    fig, ax = new_fig(11, 4.6)
    x = np.arange(len(calc))
    colors = [RED if t == "긴급 발주" else (AMBER if t == "주의" else BLUE) for t in calc["StatusText"]]
    ax.bar(x, calc["Stock"], width=0.55, color=colors)
    ax.scatter(x, calc["ROP"], marker="_", s=1500, color=NAVY, linewidths=3.5, zorder=3)
    for i, (stock, rop) in enumerate(zip(calc["Stock"], calc["ROP"])):
        ax.text(i, max(stock, rop) * 1.03, f"{stock}/{rop}", ha="center", fontsize=8.5, color="#475569")
    ax.set_xticks(x)
    ax.set_xticklabels(calc["ProductName"], rotation=15, ha="right")
    ax.set_ylabel("수량", color="#475569")
    from matplotlib.lines import Line2D
    ax.legend(
        handles=[
            Line2D([0], [0], color=RED, lw=8, label="긴급 발주"),
            Line2D([0], [0], color=AMBER, lw=8, label="주의"),
            Line2D([0], [0], color=BLUE, lw=8, label="적정"),
            Line2D([0], [0], color=NAVY, lw=3, label="재주문점(ROP)"),
        ],
        frameon=False, ncol=4, loc="upper right",
    )
    show_fig(fig)

# ------------------------------------------------------------------
# 5. 데이터 관리
# ------------------------------------------------------------------
elif menu == "🗄️ 데이터 관리":
    st.subheader("🗄️ 데이터 업로드 및 관리")
    st.info("💡 기본값은 **내장 샘플 데이터**입니다. 아래에서 CSV를 업로드하면 해당 데이터로 교체되고, "
            "'샘플 데이터로 초기화' 버튼으로 언제든 되돌릴 수 있습니다.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**① 상품 마스터**  \n`SKU, ProductName, Category, Stock, UnitPrice, LeadTime`")
        f1 = st.file_uploader("inventory.csv", type="csv", key="up_inv")
        if f1 is not None:
            try:
                df = read_csv_safe(f1)
                if check_columns(df, INV_COLS, "상품 마스터"):
                    st.session_state.inv = df
                    st.success(f"✅ {len(df)}개 상품 로드 완료")
            except Exception as e:
                st.error(f"파일을 읽는 중 오류: {e}")
    with col2:
        st.markdown("**② 판매 데이터**  \n`Date, SKU, Qty`")
        f2 = st.file_uploader("sales_data.csv", type="csv", key="up_sales")
        if f2 is not None:
            try:
                df = read_csv_safe(f2)
                if check_columns(df, SALES_COLS, "판매 데이터"):
                    df["Date"] = pd.to_datetime(df["Date"])
                    st.session_state.sales = df
                    st.success(f"✅ {len(df):,}행 로드 완료 ({df['Date'].min():%Y-%m-%d} ~ {df['Date'].max():%Y-%m-%d})")
            except Exception as e:
                st.error(f"파일을 읽는 중 오류: {e}")

    st.markdown("---")
    st.markdown("**현재 로드된 데이터 미리보기**")
    t1, t2 = st.tabs(["상품 마스터", "판매 데이터"])
    with t1:
        if st.session_state.inv is not None:
            st.dataframe(st.session_state.inv, hide_index=True)
        else:
            st.info("데이터 없음")
    with t2:
        if st.session_state.sales is not None:
            st.dataframe(st.session_state.sales.tail(200), hide_index=True)
        else:
            st.info("데이터 없음")

    if st.button("🔄 샘플 데이터로 초기화"):
        for k in ("inv", "sales"):
            st.session_state.pop(k, None)
        st.rerun()
