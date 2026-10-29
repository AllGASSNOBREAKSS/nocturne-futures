export type Bar = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

const USER_AGENT =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36";

/**
 * Fetch daily or intraday bars from Yahoo's public chart endpoint.
 * No key, no crumb. The endpoint is undocumented and can rate-limit.
 */
export async function fetchChart(
  symbol: string,
  range = "1mo",
  interval = "1d",
): Promise<Bar[]> {
  const url =
    `https://query2.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}` +
    `?range=${encodeURIComponent(range)}&interval=${encodeURIComponent(interval)}`;

  const response = await fetch(url, {
    headers: { "User-Agent": USER_AGENT, Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`${symbol}: HTTP ${response.status}`);
  }

  const payload = (await response.json()) as {
    chart?: {
      result?: Array<{
        timestamp: number[];
        indicators: { quote: Array<Record<string, Array<number | null>>> };
      }>;
    };
  };

  const result = payload.chart?.result?.[0];
  if (!result) throw new Error(`${symbol}: empty chart result`);

  const quote = result.indicators.quote[0];
  const bars: Bar[] = [];
  for (let i = 0; i < result.timestamp.length; i += 1) {
    const close = quote.close[i];
    if (close == null) continue;
    bars.push({
      date: new Date(result.timestamp[i] * 1000).toISOString().slice(0, 10),
      open: quote.open[i] ?? close,
      high: quote.high[i] ?? close,
      low: quote.low[i] ?? close,
      close,
      volume: quote.volume[i] ?? 0,
    });
  }
  return bars;
}

export async function fetchMany(symbols: string[], range = "1mo", interval = "1d") {
  const out: Record<string, Bar[]> = {};
  for (const symbol of symbols) {
    out[symbol] = await fetchChart(symbol, range, interval);
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  return out;
}
