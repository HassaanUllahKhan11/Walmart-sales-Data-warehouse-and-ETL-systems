import re
from pathlib import Path

import pytest

from app import app
from warehouse import answers, etl, queries

ORIGINAL = Path(__file__).resolve().parent.parent / "original-warehouse-project" / "queries_dw.sql"


@pytest.fixture(scope="module")
def built():
    return answers.build()


def test_star_schema_loads_every_transaction(built):
    data, db, _ = built
    stats = data["stats"]
    assert stats["skipped"] == 0
    assert stats["DIM_TIME"] == 4018  # 2015-01-01 .. 2025-12-31, as in the report
    assert (stats["DIM_STORE"], stats["DIM_SUPPLIER"], stats["DIM_CITY"]) == (8, 7, 3)
    rows = sum(1 for _ in open(etl.DATA / "transactional_data.csv", encoding="utf-8")) - 1
    assert stats["FACT_SALES"] == rows


def test_fact_amounts_are_quantity_times_price(built):
    _, db, _ = built
    off = db.execute("SELECT COUNT(*) FROM FACT_SALES WHERE ABS(total_amount - quantity * unit_price) > 0.01").fetchone()[0]
    assert off == 0


def test_all_twenty_queries_from_the_original_file_are_ported():
    titles = re.findall(r"^-- Q(\d+)\.", ORIGINAL.read_text(encoding="utf-8"), flags=re.M)
    assert [int(t) for t in titles] == list(range(1, 21))
    assert [q["id"] for q in queries.Q] == [f"q{i}" for i in range(1, 21)]


def test_every_query_returns_rows_and_an_answer(built):
    data, _, results = built
    for q in data["queries"]:
        assert results[q["id"]]["rows"], q["id"]
        assert q["headline"].endswith("."), q["id"]


def test_rollup_grand_total_matches_fact_table(built):
    _, db, results = built
    cols = results["q17"]["columns"]
    grand = [dict(zip(cols, r)) for r in results["q17"]["rows"] if r[0] == "ALL STORES"]
    assert len(grand) == 1
    total = db.execute("SELECT SUM(total_amount) FROM FACT_SALES").fetchone()[0]
    assert grand[0]["total_revenue"] == pytest.approx(total)


def test_q6_window_matches_mysql_date_sub(built):
    _, _, results = built
    months = {(r[0], r[1]) for r in results["q6"]["rows"]}
    assert min(months) == (2020, 6) and max(months) == (2020, 12)


def test_q16_pairs_are_ranked(built):
    _, _, results = built
    counts = [r[4] for r in results["q16"]["rows"]]
    assert counts == sorted(counts, reverse=True) and len(counts) == 5


def test_q19_stddev_is_population_stddev(built):
    _, db, results = built
    pid = results["q19"]["rows"][0][0]
    daily = [r[0] for r in db.execute(
        "SELECT SUM(f.total_amount) FROM FACT_SALES f JOIN DIM_PRODUCT p ON f.product_key = p.product_key "
        "JOIN DIM_TIME t ON f.time_key = t.time_key WHERE p.product_id = ? GROUP BY t.date_value", (pid,))]
    mean = sum(daily) / len(daily)
    sd = (sum((x - mean) ** 2 for x in daily) / len(daily)) ** 0.5
    assert results["q19"]["rows"][0][5] == pytest.approx(sd)


def test_warehouse_page_and_csv():
    client = app.test_client()
    page = client.get("/warehouse")
    assert page.status_code == 200 and b"All 20 queries" in page.data
    csv = client.get("/warehouse/q/q20.csv")
    assert csv.status_code == 200 and csv.data.startswith(b"store_id,store_name,year,quarter")
    assert client.get("/warehouse/q/nope.csv").status_code == 404
