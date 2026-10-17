"""Know Your Numbers: a sales dashboard for small online shops.

    python app.py            # http://localhost:5000
"""

import csv
import io
import os
from functools import lru_cache
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, send_file

from dashboard import analytics, loader
from warehouse import answers as warehouse_answers

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "data" / "sample_orders.csv"
MAX_UPLOAD = 4 * 1024 * 1024  # Vercel caps request bodies at 4.5 MB

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD


@lru_cache(maxsize=1)
def sample_dashboard():
    db, meta = loader.load(SAMPLE.read_text(encoding="utf-8"))
    data = analytics.build(db)
    data["source"] = {"name": "Loom & Ember (sample store)", "sample": True, **meta}
    return data


def owner():
    return {
        "name": os.getenv("OWNER_NAME", ""),
        "email": os.getenv("OWNER_EMAIL", ""),
        "link": os.getenv("OWNER_BOOKING_LINK", ""),
    }


@app.get("/")
def index():
    return render_template("index.html", data=sample_dashboard(), owner=owner())


@app.get("/api/dashboard")
def api_dashboard():
    return jsonify(sample_dashboard())


@app.post("/api/upload")
def api_upload():
    """Build a dashboard from an uploaded CSV. Processed in memory and never stored."""
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(error="Choose a CSV file to upload."), 400
    raw = f.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    try:
        db, meta = loader.load(text)
        data = analytics.build(db)
    except loader.CSVError as e:
        return jsonify(error=str(e)), 422
    data["source"] = {"name": Path(f.filename).stem[:60], "sample": False, **meta}
    return jsonify(data)


@app.errorhandler(413)
def too_large(_):
    return jsonify(error="That file is over 4 MB. Export a shorter date range and try again."), 413


@app.get("/sample.csv")
def sample_csv():
    return send_file(SAMPLE, mimetype="text/csv", as_attachment=True, download_name="sample_orders.csv")


@lru_cache(maxsize=1)
def warehouse():
    """Build the star schema, run all 20 queries once per process and keep the results."""
    data, _db, results = warehouse_answers.build()
    return data, results


@app.get("/warehouse")
def warehouse_page():
    return render_template("warehouse.html", data=warehouse()[0])


@app.get("/warehouse/q/<qid>.csv")
def warehouse_csv(qid):
    results = warehouse()[1]
    if qid not in results:
        abort(404)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(results[qid]["columns"])
    writer.writerows(results[qid]["rows"])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=walmart_dw_{qid}.csv"})


@app.get("/healthz")
def healthz():
    return {"ok": True}


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
