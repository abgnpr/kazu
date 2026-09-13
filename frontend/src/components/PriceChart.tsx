import { Alert, Group, Loader, SegmentedControl, Stack, Text, Title } from "@mantine/core";
import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useHistory } from "../api/queries";
import { fmtDate, fmtPrice } from "../theme/format";

const RANGES = [
  { label: "3M", value: "66" },
  { label: "6M", value: "132" },
  { label: "1Y", value: "252" },
  { label: "Max", value: "5000" },
];

export function PriceChart({ symbol }: { symbol: string | null }) {
  const [range, setRange] = useState("252");
  const { data, isLoading, error } = useHistory(symbol, Number(range));

  // Recharts needs a plain array; the indicator columns come precomputed from
  // DuckDB so there is no client-side rolling-window maths here.
  const series = useMemo(() => data?.candles ?? [], [data]);

  if (!symbol) {
    return (
      <Stack align="center" justify="center" h="100%">
        <Text c="dimmed">Select an instrument to view its chart</Text>
      </Stack>
    );
  }

  const last = series.at(-1);
  const first = series.at(0);
  const changed = last && first ? ((last.close - first.close) / first.close) * 100 : null;
  const up = (changed ?? 0) >= 0;
  const stroke = up ? "var(--mantine-color-teal-6)" : "var(--mantine-color-red-6)";

  return (
    <Stack gap="xs" h="100%">
      <Group justify="space-between" align="flex-end" wrap="nowrap">
        <div>
          <Title order={4}>{data?.meta?.name ?? symbol}</Title>
          <Group gap="xs">
            <Text size="xl" fw={600} className="numeric">
              {fmtPrice(last?.close)}
            </Text>
            {changed != null && (
              <Text size="sm" c={up ? "teal" : "red"}>
                {up ? "+" : ""}
                {changed.toFixed(2)}% over range
              </Text>
            )}
          </Group>
        </div>
        <SegmentedControl size="xs" data={RANGES} value={range} onChange={setRange} />
      </Group>

      {error && <Alert color="red">{(error as Error).message}</Alert>}
      {isLoading && (
        <Group justify="center" py="xl">
          <Loader size="sm" />
        </Group>
      )}

      {!isLoading && series.length > 0 && (
        <ResponsiveContainer width="100%" height="100%" minHeight={260}>
          <AreaChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={stroke} stopOpacity={0.28} />
                <stop offset="100%" stopColor={stroke} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--mantine-color-dark-4)" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={fmtDate}
              minTickGap={48}
              tick={{ fontSize: 11 }}
              stroke="var(--mantine-color-dimmed)"
            />
            <YAxis
              domain={["auto", "auto"]}
              width={64}
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => v.toFixed(0)}
              stroke="var(--mantine-color-dimmed)"
            />
            <Tooltip
              labelFormatter={(l) => fmtDate(String(l))}
              formatter={(v) => fmtPrice(Number(v))}
              contentStyle={{
                background: "var(--mantine-color-body)",
                border: "1px solid var(--mantine-color-dark-4)",
                borderRadius: 4,
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Area
              type="monotone"
              dataKey="close"
              name="Close"
              stroke={stroke}
              strokeWidth={1.6}
              fill="url(#priceFill)"
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="sma20"
              name="SMA 20"
              stroke="var(--mantine-color-yellow-5)"
              strokeWidth={1}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="sma50"
              name="SMA 50"
              stroke="var(--mantine-color-grape-4)"
              strokeWidth={1}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </Stack>
  );
}
