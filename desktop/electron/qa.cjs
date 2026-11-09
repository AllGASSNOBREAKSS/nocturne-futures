// UI acceptance harness: drives the real renderer like a user (click by visible
// text, fill fields by their label, wait for on-screen text, read values) and
// records every step with timings and screenshots. Enabled only by
// NOCTURNE_QA=<scenario.json> NOCTURNE_QA_OUT=<dir>; never active in normal use.
const fs = require("node:fs");
const path = require("node:path");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Executed inside the page. Finds elements by visible text / field label.
const PAGE_HELPERS = `
window.__qa = {
  scope(within) {
    if (!within) return document;
    const norm = (s) => (s || "").replace(/\\s+/g, " ").trim().toLowerCase();
    const label = [...document.querySelectorAll("label")].find((l) => norm(l.querySelector("span")?.textContent) === norm(within));
    if (label) return label;
    const panel = [...document.querySelectorAll("section")].find((s) => norm(s.querySelector("h2")?.textContent).includes(norm(within)));
    if (panel) return panel;
    throw new Error("scope not found: " + within);
  },
  click(text, within, exact) {
    const norm = (s) => (s || "").replace(/\\s+/g, " ").trim().toLowerCase();
    const root = this.scope(within);
    const candidates = [...root.querySelectorAll("button, a, tr, [role=button]")].filter((el) => el.offsetParent !== null);
    const target = candidates.find((el) => norm(el.textContent) === norm(text)) || (!exact && candidates.find((el) => norm(el.textContent).includes(norm(text))));
    if (!target) throw new Error("clickable not found: " + text);
    if (target.disabled) throw new Error("clickable disabled: " + text);
    target.click();
    return norm(target.textContent).slice(0, 80);
  },
  fill(label, value) {
    const field = this.scope(label).querySelector("input, select, textarea");
    if (!field) throw new Error("field not found: " + label);
    const proto = field.tagName === "SELECT" ? HTMLSelectElement.prototype : field.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    if (field.tagName === "SELECT" && ![...field.options].some((o) => o.value === String(value))) throw new Error("option not available: " + label + "=" + value);
    Object.getOwnPropertyDescriptor(proto, "value").set.call(field, String(value));
    field.dispatchEvent(new Event(field.tagName === "SELECT" ? "change" : "input", { bubbles: true }));
    return field.value;
  },
  fillSel(selector, value) {
    const field = document.querySelector(selector);
    if (!field) throw new Error("selector not found: " + selector);
    const proto = field.tagName === "SELECT" ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, "value").set.call(field, String(value));
    field.dispatchEvent(new Event(field.tagName === "SELECT" ? "change" : "input", { bubbles: true }));
    return field.value;
  },
  text(within) { return (this.scope(within).innerText || "").replace(/\\s+/g, " ").trim(); },
  has(text) { return document.body.innerText.toLowerCase().includes(String(text).toLowerCase()); },
};
true;
`;

async function run(win, bridgeCall, scenarioPath, outDir, status) {
  fs.mkdirSync(outDir, { recursive: true });
  const scenario = JSON.parse(fs.readFileSync(scenarioPath, "utf8"));
  const results = { scenario: scenario.name, started: new Date().toISOString(), steps: [], values: {} };
  for (let i = 0; i < 240 && !["ready", "error"].includes(status().state); i++) await sleep(500);
  results.backend = status();
  const js = (code) => win.webContents.executeJavaScript(code);
  for (const [index, step] of scenario.steps.entries()) {
    const started = Date.now();
    const record = { index, step };
    try {
      await js(PAGE_HELPERS);
      if (step.nav) { await js(`location.hash = "#${step.nav}"`); await sleep(step.settle ?? 1500); }
      if (step.click) record.result = await js(`__qa.click(${JSON.stringify(step.click)}, ${JSON.stringify(step.within ?? null)}, ${!!step.exact})`);
      if (step.fillSel) record.result = await js(`__qa.fillSel(${JSON.stringify(step.fillSel)}, ${JSON.stringify(step.value)})`);
      if (step.fill) record.result = await js(`__qa.fill(${JSON.stringify(step.fill)}, ${JSON.stringify(step.value)})`);
      if (step.waitText) {
        const deadline = Date.now() + (step.timeout ?? 60000);
        let ok = false;
        while (Date.now() < deadline) { await js(PAGE_HELPERS); if (await js(`__qa.has(${JSON.stringify(step.waitText)})`)) { ok = true; break; } await sleep(1000); }
        if (!ok) throw new Error("timed out waiting for text: " + step.waitText);
      }
      if (step.read) results.values[step.save] = await js(`__qa.text(${JSON.stringify(step.read)})`);
      if (step.eval) results.values[step.save] = await js(step.eval);
      if (step.api) {
        const t0 = Date.now();
        const r = await bridgeCall(step.api.method || "GET", step.api.path, step.api.body);
        results.values[step.save] = { ok: r.ok, status: r.status, ms: Date.now() - t0, data: step.keep === false ? undefined : r.data, error: r.error };
        if (!r.ok && !step.expectError) throw new Error(`api ${step.api.path}: ${r.error}`);
        if (r.ok && step.expectError) throw new Error(`api ${step.api.path} unexpectedly succeeded`);
      }
      if (step.waitJob) {
        const deadline = Date.now() + (step.timeout ?? 900000);
        let job = null;
        while (Date.now() < deadline) {
          for (const kind of ["/v1/training-jobs", "/v1/backtests"]) {
            const r = await bridgeCall("GET", kind);
            job = (r.data || []).find((j) => j.name === step.waitJob) || job;
          }
          if (job && !["QUEUED", "RUNNING"].includes(job.state)) break;
          await sleep(2000);
        }
        if (!job) throw new Error("job not found: " + step.waitJob);
        const detail = await bridgeCall("GET", `/v1/jobs/${job.job_id}`);
        const report = detail.data?.report;
        results.values[step.save || step.waitJob] = { job_id: job.job_id, state: job.state, result: job.result, seconds: (Date.now() - started) / 1000,
          report_summary: report?.summary ?? report?.metrics ?? null, economics: report?.economics ?? null };
        if (step.expectState && job.state !== step.expectState) throw new Error(`job ${step.waitJob} ended ${job.state}`);
      }
      if (step.wait) await sleep(step.wait);
      if (step.shot) fs.writeFileSync(path.join(outDir, `${step.shot}.png`), (await win.webContents.capturePage()).toPNG());
      record.status = "PASS";
    } catch (e) {
      record.status = step.optional ? "SKIPPED" : "FAIL";
      record.error = String(e && e.message || e);
      try { fs.writeFileSync(path.join(outDir, `fail-${index}.png`), (await win.webContents.capturePage()).toPNG()); } catch { /* ignore */ }
    }
    record.ms = Date.now() - started;
    results.steps.push(record);
    fs.writeFileSync(path.join(outDir, "qa-results.json"), JSON.stringify(results, null, 2));
  }
  results.finished = new Date().toISOString();
  results.passed = results.steps.filter((s) => s.status === "PASS").length;
  results.failed = results.steps.filter((s) => s.status === "FAIL").length;
  fs.writeFileSync(path.join(outDir, "qa-results.json"), JSON.stringify(results, null, 2));
}

module.exports = { run };
