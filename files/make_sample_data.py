"""샘플 데이터 생성: inventory.csv (상품 마스터) + sales_data.csv (일별 판매량)"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

products = [
    # SKU, 상품명, 카테고리, 현재고, 단가, 리드타임(일), 평균수요
    ("SKU-001", "무선 이어폰", "전자기기", 120, 45000, 5, 20),
    ("SKU-002", "보조배터리", "전자기기", 400, 25000, 7, 30),
    ("SKU-003", "텀블러", "생활용품", 90, 15000, 4, 18),
    ("SKU-004", "물티슈(10팩)", "생활용품", 700, 8000, 3, 60),
    ("SKU-005", "요가매트", "스포츠", 35, 22000, 10, 6),
    ("SKU-006", "프로틴바(박스)", "식품", 150, 18000, 6, 22),
    ("SKU-007", "USB-C 케이블", "전자기기", 260, 7000, 5, 35),
    ("SKU-008", "에코백", "패션잡화", 500, 9000, 8, 14),
]

inv = pd.DataFrame(products, columns=["SKU", "ProductName", "Category", "Stock", "UnitPrice", "LeadTime", "_mu"])

dates = pd.date_range("2026-08-26", periods=90, freq="D")
rows = []
for _, p in inv.iterrows():
    weekly = np.where(dates.dayofweek >= 5, 1.3, 1.0)       # 주말 수요 증가
    trend = np.linspace(0.9, 1.15, len(dates)) if p.SKU in ("SKU-001", "SKU-006") else 1.0
    qty = rng.poisson(p._mu * weekly * trend)
    rows += [(d.strftime("%Y-%m-%d"), p.SKU, int(q)) for d, q in zip(dates, qty)]

sales = pd.DataFrame(rows, columns=["Date", "SKU", "Qty"])
inv.drop(columns="_mu").to_csv("inventory.csv", index=False, encoding="utf-8-sig")
sales.to_csv("sales_data.csv", index=False, encoding="utf-8-sig")
print("생성 완료:", len(inv), "개 상품,", len(sales), "행 판매 데이터")
