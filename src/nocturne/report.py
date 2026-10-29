"""Render the call, the scorecard, the charts and the dashboard."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .models import Call  # noqa: E402
from .score import ScoreRow, score_call, summary  # noqa: E402

INK = "#0f172a"
MUTED = "#64748b"
GRID = "#e2e8f0"
BLUE = "#2563eb"
LIGHT_BLUE = "#93c5fd"
RED = "#dc2626"
GREEN = "#059669"
AMBER = "#d97706"


def _fmt(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}"


def _pct(value: float, decimals: int = 2) -> str:
    return f"{value:+.{decimals}f}%"


def _md_table(headers: list[str], rows: list[list[Any]], align: list[str] | None = None) -> str:
    align = align or ["---"] * len(headers)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(align) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _history_by_code(history: dict, call: Call) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for code, inst in call.instruments.items():
        out[code] = history.get(inst.symbol, [])
    return out


def _bias_label(bias: str) -> str:
    return bias.replace("-", " ").title()


def call_markdown(call: Call, study: dict, history: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Nocturne call · {call.session} session")
    lines.append("")
    lines.append(
        f"**Published:** {call.published_at}  \n"
        f"**Engine:** {call.engine}  \n"
        f"**Call ID:** `{call.call_id}`  \n"
        f"**Session covered:** {call.session} (US equities close)"
    )
    lines.append("")
    lines.append("## The call")
    lines.append("")
    rows = []
    for code, inst in call.instruments.items():
        low, high = call.predicted_close[code]
        rlow, rhigh = call.predicted_range[code]
        s_low, s_high = call.sigma_close[code]
        rows.append(
            [
                f"**{code}** · {inst.name}",
                _bias_label(call.bias[code]),
                f"{call.confidence[code]:.0%}",
                f"{_fmt(low)}–{_fmt(high)}",
                f"{_fmt(rlow)}–{_fmt(rhigh)}",
                f"±{_fmt(s_low, 1)}–{_fmt(s_high, 1)}" if s_high else f"±{_fmt(call.sigma_close_point(code), 1)}",
            ]
        )
    lines.append(
        _md_table(
            ["Instrument", "Bias", "Confidence", "Predicted close", "Expected range", "1σ close"],
            rows,
        )
    )
    lines.append("")
    lines.append("## Levels")
    lines.append("")
    rows = []
    for code, inst in call.instruments.items():
        lv = call.levels[code]
        rows.append(
            [
                f"**{code}**",
                _fmt(lv.r2),
                _fmt(lv.r1),
                _fmt(lv.pivot),
                _fmt(lv.s1),
                _fmt(lv.s2),
                _fmt(inst.last),
            ]
        )
    lines.append(
        _md_table(["Instrument", "R2", "R1", "Pivot (VWAP)", "S1", "S2", "Last"], rows)
    )
    lines.append("")
    lines.append("## Scenario map")
    lines.append("")
    rows = []
    for scenario in call.scenarios:
        cells = [scenario.label, f"{scenario.probability:.0%}"]
        for code in call.instruments:
            low, high = scenario.closes[code]
            cells.append(f"{_fmt(low)}–{_fmt(high)}")
        rows.append(cells)
    lines.append(
        _md_table(["Scenario", "Prob.", *call.instruments.keys()], rows)
    )
    lines.append("")
    lines.append("## Historical base rates")
    lines.append("")
    rows = []
    for key in ("all", "fomc_2024_2026", "oct28"):
        window = study["windows"][key]
        cells = [window["label"], f"{window['n']:,}"]
        for code in call.instruments:
            stats = window["instruments"][code]
            cells.append(
                f"{_pct(stats['avg_ret'])} avg · {stats['pct_up']:.0f}% up · "
                f"{stats['avg_range']:.2f}% range"
            )
        rows.append(cells)
    lines.append(_md_table(["Window", "n", *call.instruments.keys()], rows))
    lines.append("")
    lines.append(
        "Base rates are descriptive, not predictive. The FOMC sample is 22 decisions "
        "from 2024–2026 and the Oct-28 sample is 11 observations; both are small. "
        "The all-days row is 15 years of daily bars."
    )
    lines.append("")
    lines.append("## Macro context")
    lines.append("")
    macro = call.macro
    rows = [
        ["Fed funds target", macro.get("fed_funds", "—")],
        ["Last FOMC action", macro.get("last_action", "—")],
        ["Consensus for this meeting", macro.get("consensus", "—")],
        ["US 2Y / 10Y / 30Y", f"{macro.get('ust_2y', '—')} / {macro.get('ust_10y', '—')} / {macro.get('ust_30y', '—')}"],
        ["DXY / VIX / WTI", f"{macro.get('dxy', '—')} / {macro.get('vix', '—')} / {macro.get('wti', '—')}"],
    ]
    lines.append(_md_table(["Item", "Value"], rows))
    lines.append("")
    lines.append("### Scheduled events")
    lines.append("")
    for event in macro.get("events", []):
        lines.append(f"- **{event['time']}** — {event['event']} ({event['note']})")
    lines.append("")
    lines.append("## Provenance")
    lines.append("")
    lines.append(
        f"Data timestamp: **{macro.get('data_timestamp', '—')}**. "
        f"Levels and bands were computed from the snapshot in "
        f"`data/snapshots/{call.call_id}/call.json`."
    )
    lines.append("")
    for source in call.sources:
        lines.append(f"- {source}")
    lines.append("")
    lines.append("---")
    lines.append(
        "*Research artifact, not investment advice. Futures are leveraged; a 1-point "
        "ES move is $50 per contract.*"
    )
    return "\n".join(lines)


def score_markdown(call: Call, rows: list[ScoreRow], actual: dict) -> str:
    stats = summary(rows)
    lines: list[str] = []
    lines.append(f"# Scorecard · {call.session} session")
    lines.append("")
    lines.append(
        f"**Call:** `{call.call_id}` · published {call.published_at}  \n"
        f"**Scored:** {actual.get('as_of', call.session)} · official settlement"
    )
    lines.append("")
    lines.append(
        f"**Verdict:** direction {stats['direction']:.0%} · close band "
        f"{stats['band']:.0%} · range {stats['range_full']:.0%} full "
        f"({stats['range_any']:.0%} touched) · mean absolute close error "
        f"{stats['mean_abs_error_pct']:.2f}%."
    )
    lines.append("")
    rows_md = []
    for row in rows:
        if row.range_hit:
            range_cell = "✅"
        elif row.range_partial:
            range_cell = "⚠️ partial"
        else:
            range_cell = "❌"
        rows_md.append(
            [
                f"**{row.code}**",
                _fmt(row.prior_close),
                f"{_fmt(row.predicted_low)}–{_fmt(row.predicted_high)}",
                _fmt(row.actual_close),
                f"{row.close_error:+,.2f} ({_pct(row.close_error_pct)})",
                "✅" if row.direction_hit else "❌",
                "✅" if row.band_hit else "❌",
                range_cell,
                f"{row.r1_break:+,.2f}",
                f"{row.s1_break:+,.2f}",
                row.bucket,
            ]
        )
    lines.append(
        _md_table(
            [
                "Instrument",
                "Prior",
                "Predicted",
                "Actual",
                "Error",
                "Dir",
                "Band",
                "Range",
                "R1 break",
                "S1 break",
                "Bucket",
            ],
            rows_md,
        )
    )
    lines.append("")
    lines.append(
        "`R1 break` / `S1 break` are in points; positive means the session ran past "
        "that level. `Bucket` is the published scenario that contained the settlement; "
        "`outside` means the scenario bands left a gap."
    )
    lines.append("")
    lines.append("## What happened")
    lines.append("")
    context = actual.get("context", {})
    lines.append(context.get("summary", "No context recorded."))
    lines.append("")
    if context.get("statement_quote"):
        lines.append(f"> {context['statement_quote']}")
        lines.append("")
    macro_rows = [
        ["S&P 500 cash", _fmt(context.get("spx", 0.0))],
        ["Nasdaq Composite", _fmt(context.get("ndx", 0.0))],
        ["VIX", _fmt(context.get("vix", 0.0))],
        ["US 10Y", _fmt(context.get("ust_10y", 0.0), 3)],
        ["DXY", _fmt(context.get("dxy", 0.0))],
    ]
    lines.append(_md_table(["Market", "Close"], macro_rows))
    lines.append("")
    lines.append("## What worked, what did not")
    lines.append("")
    for item in actual.get("postmortem", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Calibration note")
    lines.append("")
    lines.append(actual.get("calibration_note", ""))
    lines.append("")
    lines.append("---")
    lines.append(
        "*Scored on the official settlement: CME equity index futures at 16:00 ET, "
        "COMEX metals at 13:30 ET. The 16:00 ET mark for metals is shown below for "
        "transparency.*"
    )
    lines.append("")
    rows_4pm = [
        [code, _fmt(actual["instruments"][code].get("close_4pm", actual["instruments"][code]["close"]))]
        for code in call.instruments
    ]
    lines.append(_md_table(["Instrument", "16:00 ET mark"], rows_4pm))
    return "\n".join(lines)


def plot_call(call: Call, history: dict, actual: dict | None, out_path: Path) -> None:
    codes = list(call.instruments)
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    fig.patch.set_facecolor("white")

    for ax, code in zip(axes.flat, codes):
        inst = call.instruments[code]
        bars = [b for b in history.get(code, []) if b["date"] <= call.call_id][-12:]
        x = np.arange(len(bars))
        closes = [b["close"] for b in bars]
        ax.plot(x, closes, color=INK, lw=1.9, zorder=4, label="daily close")

        pred_low, pred_high = call.predicted_close[code]
        range_low, range_high = call.predicted_range[code]
        ax.axhspan(range_low, range_high, color=LIGHT_BLUE, alpha=0.20, zorder=1, label="expected range")
        ax.axhspan(pred_low, pred_high, color=BLUE, alpha=0.26, zorder=2, label="predicted close")

        level = call.levels[code]
        for name, price, color in (
            ("R2", level.r2, RED),
            ("R1", level.r1, "#f87171"),
            ("S1", level.s1, "#34d399"),
            ("S2", level.s2, GREEN),
        ):
            ax.axhline(price, color=color, lw=1.0, ls="--", alpha=0.9, zorder=3)
            ax.text(
                0.15,
                price,
                f"{name} {_fmt(price)}",
                va="center",
                ha="left",
                fontsize=6.5,
                color=color,
                bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=0.85),
                zorder=5,
            )
        ax.axhline(level.pivot, color=MUTED, lw=0.9, ls=":", alpha=0.7, zorder=3)

        y_values = list(closes) + [pred_low, pred_high, range_low, range_high, level.r2, level.s2]
        if actual and code in actual.get("instruments", {}):
            result = actual["instruments"][code]
            y_values.append(result["close"])
            color = GREEN if pred_low <= result["close"] <= pred_high else RED
            ax.scatter([len(bars)], [result["close"]], s=95, color=color, edgecolor="white", zorder=6)
            ax.annotate(
                f"actual {_fmt(result['close'])}",
                (len(bars), result["close"]),
                textcoords="offset points",
                xytext=(-9, 9),
                ha="right",
                fontsize=8,
                color=color,
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85),
            )
            ax.set_xlim(-0.6, len(bars) + 1.6)
            ticks = list(x) + [len(bars)]
            labels = [b["date"][5:] for b in bars] + ["actual"]
        else:
            ax.set_xlim(-0.6, len(bars) - 0.4)
            ticks = list(x)
            labels = [b["date"][5:] for b in bars]

        low_y, high_y = min(y_values), max(y_values)
        pad = (high_y - low_y) * 0.06 or 1.0
        ax.set_ylim(low_y - pad, high_y + pad)
        ax.set_xticks(ticks[::3] if len(ticks) > 8 else ticks)
        ax.set_xticklabels(labels[::3] if len(labels) > 8 else labels, fontsize=7)
        ax.tick_params(labelsize=8, colors=MUTED)
        ax.grid(axis="y", color=GRID, lw=0.8)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_color(GRID)
        ax.spines["bottom"].set_color(GRID)
        ax.set_title(
            f"{code} · {inst.name} · {inst.contract}\n"
            f"Bias: {_bias_label(call.bias[code])} · predicted close {_fmt(pred_low)}–{_fmt(pred_high)}",
            fontsize=10,
            loc="left",
            color=INK,
        )

    fig.suptitle(
        f"Nocturne · {call.call_id} call for the {call.session} session",
        fontsize=15,
        fontweight="bold",
        x=0.012,
        ha="left",
        color=INK,
    )
    fig.savefig(out_path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_score(rows: list[ScoreRow], out_path: Path) -> None:
    codes = [r.code for r in rows]
    predicted = [(r.predicted_mid / r.prior_close - 1.0) * 100.0 for r in rows]
    actual = [(r.actual_close / r.prior_close - 1.0) * 100.0 for r in rows]

    fig, ax = plt.subplots(figsize=(10, 5.4), constrained_layout=True)
    x = np.arange(len(codes))
    width = 0.36
    ax.bar(x - width / 2, predicted, width, color=BLUE, label="predicted (mid)")
    ax.bar(x + width / 2, actual, width, color=INK, label="actual settlement")
    ax.axhline(0, color=MUTED, lw=1)
    for index, (p, a) in enumerate(zip(predicted, actual)):
        ax.text(index - width / 2, p + (0.05 if p >= 0 else -0.12), _pct(p), ha="center", fontsize=8, color=BLUE)
        ax.text(index + width / 2, a + (0.05 if a >= 0 else -0.12), _pct(a), ha="center", fontsize=8, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels(codes, fontsize=11, color=INK)
    ax.set_ylabel("% change vs prior settlement", fontsize=9, color=MUTED)
    ax.set_title("Predicted vs actual: the call missed the equity relief rally", fontsize=12, loc="left", color=INK)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.grid(axis="y", color=GRID, lw=0.8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)
    fig.savefig(out_path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _html_table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{cell}</th>" for cell in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def build_dashboard(call: Call, rows: list[ScoreRow], study: dict, actual: dict, out_dir: Path) -> Path:
    stats = summary(rows)
    chart_path = out_dir / f"{call.call_id}_levels.png"
    score_chart = out_dir / f"{call.session}_scorecard.png"
    call_img = base64.b64encode(chart_path.read_bytes()).decode("ascii")
    score_img = base64.b64encode(score_chart.read_bytes()).decode("ascii")

    call_rows = []
    for code, inst in call.instruments.items():
        low, high = call.predicted_close[code]
        rlow, rhigh = call.predicted_range[code]
        call_rows.append(
            [
                f"<b>{code}</b> · {inst.name}",
                _bias_label(call.bias[code]),
                f"{call.confidence[code]:.0%}",
                f"{_fmt(low)}–{_fmt(high)}",
                f"{_fmt(rlow)}–{_fmt(rhigh)}",
            ]
        )

    score_rows = []
    for row in rows:
        score_rows.append(
            [
                f"<b>{row.code}</b>",
                _fmt(row.prior_close),
                f"{_fmt(row.predicted_low)}–{_fmt(row.predicted_high)}",
                _fmt(row.actual_close),
                f"{row.close_error:+,.2f}",
                "✅" if row.direction_hit else "❌",
                "✅" if row.band_hit else "❌",
                "✅" if row.range_hit else ("⚠️" if row.range_partial else "❌"),
            ]
        )

    stats_rows = []
    for key in ("all", "fomc_2024_2026", "oct28"):
        window = study["windows"][key]
        stats_rows.append(
            [
                window["label"],
                f"{window['n']:,}",
                *[
                    f"{_pct(window['instruments'][code]['avg_ret'])} · "
                    f"{window['instruments'][code]['pct_up']:.0f}% up"
                    for code in call.instruments
                ],
            ]
        )

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nocturne · {call.call_id} → {call.session}</title>
<style>
  :root {{ --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; --blue:#2563eb; --bg:#f8fafc; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:1120px; margin:0 auto; padding:0 28px 64px; }}
  header {{ background:var(--ink); color:#fff; padding:38px 0 30px; margin-bottom:28px; }}
  header .wrap {{ padding-bottom:0; }}
  .kicker {{ letter-spacing:.16em; text-transform:uppercase; font-size:11px; color:#93c5fd; font-weight:700; }}
  h1 {{ font-size:34px; line-height:1.15; margin:8px 0 6px; font-weight:750; }}
  h2 {{ font-size:18px; margin:34px 0 10px; }}
  .sub {{ color:#cbd5e1; font-size:14px; }}
  .cards {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:22px 0 4px; }}
  .card {{ background:#fff; border:1px solid var(--line); border-radius:10px; padding:14px 16px; }}
  .card .v {{ font-size:26px; font-weight:750; letter-spacing:-.02em; }}
  .card .l {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; margin-top:3px; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); border-radius:10px; overflow:hidden; font-size:13px; }}
  th {{ text-align:left; background:#f1f5f9; color:#334155; font-size:11px; text-transform:uppercase; letter-spacing:.06em; padding:9px 11px; border-bottom:1px solid var(--line); }}
  td {{ padding:9px 11px; border-bottom:1px solid #f1f5f9; }}
  tr:last-child td {{ border-bottom:0; }}
  .note {{ color:var(--muted); font-size:12px; margin:8px 0 0; }}
  img {{ width:100%; height:auto; border:1px solid var(--line); border-radius:10px; background:#fff; }}
  .quote {{ border-left:3px solid var(--blue); background:#eff6ff; padding:12px 16px; margin:14px 0; font-size:14px; }}
  footer {{ color:var(--muted); font-size:12px; margin-top:36px; border-top:1px solid var(--line); padding-top:16px; }}
  @media (max-width:760px) {{ .cards {{ grid-template-columns:repeat(2,1fr); }} h1 {{ font-size:26px; }} }}
</style>
</head>
<body>
<header><div class="wrap">
  <div class="kicker">Nocturne · overnight futures outlook</div>
  <h1>{call.call_id} call → {call.session} session</h1>
  <div class="sub">Published {call.published_at} · scored on the official settlement</div>
</div></header>
<div class="wrap">

<div class="cards">
  <div class="card"><div class="v">{stats['direction']:.0%}</div><div class="l">Direction hit</div></div>
  <div class="card"><div class="v">{stats['band']:.0%}</div><div class="l">Close band hit</div></div>
  <div class="card"><div class="v">{stats['range_any']:.0%}</div><div class="l">Range touched</div></div>
  <div class="card"><div class="v">{stats['mean_abs_error_pct']:.2f}%</div><div class="l">Mean abs. close error</div></div>
</div>

<h2>The call</h2>
{_html_table(["Instrument", "Bias", "Conf.", "Predicted close", "Expected range"], call_rows)}

<h2>What happened</h2>
<p>{actual.get('context', {}).get('summary', '')}</p>
<div class="quote">{actual.get('context', {}).get('statement_quote', '')}</div>

<h2>Scorecard</h2>
{_html_table(["Instrument", "Prior", "Predicted", "Actual", "Error", "Dir", "Band", "Range"], score_rows)}
<p class="note">Error is actual settlement minus the midpoint of the predicted band, in contract points. Range ✅ = high and low stayed inside the expected range; ⚠️ = close inside, one extreme outside.</p>

<h2>Chart</h2>
<img src="data:image/png;base64,{call_img}" alt="Call chart">

<h2>Predicted vs actual</h2>
<img src="data:image/png;base64,{score_img}" alt="Score chart">

<h2>Historical base rates</h2>
{_html_table(["Window", "n", *call.instruments.keys()], stats_rows)}
<p class="note">Close-to-close returns. FOMC sample is 22 decisions (2024–2026); Oct-28 sample is 11 observations. Treat seasonality as weak evidence.</p>

<h2>Postmortem</h2>
<ul>{''.join(f'<li>{item}</li>' for item in actual.get('postmortem', []))}</ul>
<p>{actual.get('calibration_note', '')}</p>

<footer>
  Research artifact, not investment advice. Futures are leveraged. Data: Yahoo Finance chart API,
  US Treasury, Federal Reserve, ForexFactory calendar, Nasdaq earnings calendar.
</footer>
</div>
</body>
</html>"""
    path = out_dir / f"{call.call_id}_dashboard.html"
    path.write_text(html, encoding="utf-8")
    return path


def build_reports(call: Call, study: dict, history: dict, actual: dict | None, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    call_md = out_dir / f"{call.call_id}_call.md"
    call_md.write_text(call_markdown(call, study, history), encoding="utf-8")
    outputs["call_md"] = call_md

    chart = out_dir / f"{call.call_id}_levels.png"
    plot_call(call, _history_by_code(history, call), actual, chart)
    outputs["levels_png"] = chart

    if actual:
        rows = score_call(call, actual)
        score_md = out_dir / f"{call.session}_scorecard.md"
        score_md.write_text(score_markdown(call, rows, actual), encoding="utf-8")
        outputs["score_md"] = score_md

        score_png = out_dir / f"{call.session}_scorecard.png"
        plot_score(rows, score_png)
        outputs["score_png"] = score_png

        outputs["dashboard"] = build_dashboard(call, rows, study, actual, out_dir)

    return outputs
