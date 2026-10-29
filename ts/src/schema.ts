import { z } from "zod";

export const LevelSchema = z.object({
  r2: z.number(),
  r1: z.number(),
  pivot: z.number(),
  s1: z.number(),
  s2: z.number(),
});

export const InstrumentSchema = z.object({
  symbol: z.string().min(1),
  name: z.string().min(1),
  contract: z.string().min(1),
  tick: z.number().positive(),
  multiplier: z.number().positive(),
  last: z.number().positive(),
  prior_close: z.number().positive(),
  rth_open: z.number(),
  rth_high: z.number(),
  rth_low: z.number(),
  rth_close: z.number(),
  vwap: z.number(),
  overnight_high: z.number(),
  overnight_low: z.number(),
  atr14: z.number().positive(),
  sma20: z.number(),
  sma50: z.number(),
  sma200: z.number(),
  high_52w: z.number(),
  low_52w: z.number(),
  vol20: z.number().positive(),
});

export const ScenarioSchema = z.object({
  name: z.string().min(1),
  label: z.string().min(1),
  probability: z.number().min(0).max(1),
  closes: z.record(z.tuple([z.number(), z.number()])),
});

export const CallSchema = z
  .object({
    call_id: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    session: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    published_at: z.string().min(1),
    engine: z.string().min(1),
    macro: z.record(z.any()),
    instruments: z.record(InstrumentSchema),
    bias: z.record(z.string()),
    confidence: z.record(z.number().min(0).max(1)),
    predicted_close: z.record(z.tuple([z.number(), z.number()])),
    predicted_range: z.record(z.tuple([z.number(), z.number()])),
    sigma_close: z.record(z.tuple([z.number(), z.number()])),
    levels: z.record(LevelSchema),
    scenarios: z.array(ScenarioSchema).min(1),
    sources: z.array(z.string()),
  })
  .superRefine((call, ctx) => {
    const total = call.scenarios.reduce((sum, s) => sum + s.probability, 0);
    if (Math.abs(total - 1) > 1e-6) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `scenario probabilities must sum to 1.0 (got ${total.toFixed(6)})`,
      });
    }
    for (const code of Object.keys(call.instruments)) {
      for (const field of ["predicted_close", "predicted_range", "sigma_close", "levels"] as const) {
        if (!call[field][code]) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `${field} is missing ${code}`,
          });
        }
      }
    }
  });

export type Call = z.infer<typeof CallSchema>;
export type Instrument = z.infer<typeof InstrumentSchema>;
export type Scenario = z.infer<typeof ScenarioSchema>;
