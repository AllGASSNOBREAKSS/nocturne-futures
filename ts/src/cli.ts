import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

import { CallSchema } from "./schema.js";
import { fetchChart } from "./yahoo.js";

const SYMBOLS = ["ES=F", "NQ=F", "GC=F", "SI=F", "^VIX", "^GSPC", "^IXIC"];

async function fetchCommand(date: string): Promise<void> {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    throw new Error(`date must be YYYY-MM-DD, got ${date}`);
  }
  const directory = resolve("data", "raw", date);
  mkdirSync(directory, { recursive: true });

  for (const symbol of SYMBOLS) {
    const bars = await fetchChart(symbol, "1mo", "1d");
    const file = resolve(directory, `${symbol.replace(/[^A-Za-z]/g, "")}.json`);
    writeFileSync(file, JSON.stringify({ symbol, date, bars }, null, 2));
    console.log(`${symbol.padEnd(7)} ${String(bars.length).padStart(3)} bars -> ${file}`);
    await new Promise((r) => setTimeout(r, 350));
  }
}

function validateCommand(path: string): void {
  const raw = JSON.parse(readFileSync(resolve(path), "utf8"));
  const parsed = CallSchema.safeParse(raw);
  if (!parsed.success) {
    console.error(parsed.error.format());
    process.exit(1);
  }
  const call = parsed.data;
  console.log(
    `OK ${call.call_id} -> ${call.session} · ` +
      `${Object.keys(call.instruments).join(", ")} · ` +
      `${call.scenarios.length} scenarios`,
  );
}

const [command, argument] = process.argv.slice(2);

if (command === "fetch" && argument) {
  await fetchCommand(argument);
} else if (command === "validate" && argument) {
  validateCommand(argument);
} else {
  console.error("usage: tsx src/cli.ts fetch <YYYY-MM-DD> | validate <call.json>");
  process.exit(1);
}
