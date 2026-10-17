import io

import pytest

from app import SAMPLE, app
from dashboard import analytics, loader

SIMPLE = """order_id,order_date,customer_id,product_name,quantity,unit_price
1,2026-09-01,a,Mug,2,10
2,2026-09-02,b,Mug,1,10
3,2026-09-08,a,Candle,1,25
4,2026-09-09,c,Candle,3,25
5,2026-09-15,a,Mug,1,10
"""


@pytest.fixture(scope="module")
def sample():
    db, meta = loader.load(SAMPLE.read_text(encoding="utf-8"))
    return db, meta, analytics.build(db)


@pytest.fixture
def client():
    return app.test_client()


def test_sample_loads_every_row(sample):
    _, meta, _ = sample
    assert meta["skipped_rows"] == 0
    assert meta["orders"] > 5000


def test_shopify_subtotal_is_used_for_order_revenue(sample):
    db, _, _ = sample
    # order-level net sales (after discounts) never exceed the gross of its line items
    worse = db.execute("""SELECT COUNT(*) FROM orders o JOIN (SELECT order_id, SUM(revenue) g FROM lines
                          GROUP BY order_id) l USING (order_id) WHERE o.revenue > l.g + 0.01""").fetchone()[0]
    assert worse == 0


def test_returning_flag_marks_all_but_first_order():
    db, _ = loader.load(SIMPLE)
    flags = dict(db.execute("SELECT order_id, is_returning FROM orders"))
    assert flags == {"1": 0, "2": 0, "3": 1, "4": 0, "5": 1}


def test_weekly_and_insights_use_complete_weeks(sample):
    _, _, d = sample
    assert d["week"]["end"] <= d["as_of"]
    assert len(d["weekly"]["labels"]) == 52
    assert d["insights"][0]["title"] == "Last week in one line"
    assert all(n["text"].endswith(".") for n in d["insights"])


def test_kpis_have_values_and_deltas(sample):
    _, _, d = sample
    ids = [k["id"] for k in d["kpis"]]
    assert ids == ["revenue", "orders", "aov", "returning_share", "repeat_rate"]
    assert all(k["delta"] is not None for k in d["kpis"][:4])


def test_short_history_still_builds():
    db, _ = loader.load(SIMPLE)
    d = analytics.build(db)
    assert d["kpis"][0]["value"] == pytest.approx(140)
    assert d["seasonality"]["series"] == []  # no complete month


def test_missing_columns_are_explained():
    with pytest.raises(loader.CSVError, match="order id"):
        loader.load("foo,bar\n1,2\n")


def test_dates_in_us_format():
    db, _ = loader.load('Order ID,Date,Product,Qty,Price\n1,09/30/2026,Mug,1,"$1,200.00"\n')
    assert db.execute("SELECT day, revenue FROM orders").fetchone() == ("2026-09-30", 1200.0)


def test_index_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"This week's notes" in r.data


def test_upload_returns_dashboard(client):
    r = client.post("/api/upload", data={"file": (io.BytesIO(SIMPLE.encode()), "shop.csv")},
                    content_type="multipart/form-data")
    assert r.status_code == 200
    assert r.get_json()["source"] == {"name": "shop", "sample": False, "orders": 5, "lines": 5, "skipped_rows": 0}


def test_upload_rejects_bad_file(client):
    r = client.post("/api/upload", data={"file": (io.BytesIO(b"x,y\n1,2"), "bad.csv")},
                    content_type="multipart/form-data")
    assert r.status_code == 422
    assert "Couldn't find" in r.get_json()["error"]
