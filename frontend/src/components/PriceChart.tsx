import {
  Alert,
  Badge,
  Group,
  Loader,
  SegmentedControl,
  Stack,
  Switch,
  Text,
  Title,
} from "@mantine/core";
import { useMemo, useState } from "react";
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useHistory } from "../api/queries";
import { fmtCompact, fmtDate, fmtPrice } from "../theme/format";

const RANGES = [
  { label: "3M", value: "66" },
  { label: "6M", value: "132" },
  { label: "1Y", value: "252" },
  { label: "2Y", value: "504" },
];

// The three averages the breakout screen actually tests. Keeping the chart and
// the screen on the same periods is the whole point: a stock listed as "above
// its 200 DMA" must show that line.
const MAS = [
  { key: "sma30", label: "30 DMA", color: "var(--mantine-color-yellow-5)" },
  { key: "sma50", label: "50 DMA", color: "var(--mantine-color-grape-4)" },
  { key: "sma200", label: "200 DMA", color: "var(--mantine-color-blue-4)" },
] as const;

const AXIS = { fontSize: 11 };
const GRID = "var(--mantine-color-dark-4)";

const TOOLTIP_STYLE = {
  background: "var(--mantine-color-body)",
  border: "1px solid var(--mantine-color-dark-4)",
  borderRadius: 4,
  fontSize: 12,
};

export function PriceChart({ symbol }: { symbol: string | null }) {
  const [range, setRange] = useState("252");
  const [showVolume, setShowVolume] = useState(true);
  const { data, isLoading, error } = useHistory(symbol, Number(range));

  // Indicators arrive precomputed from DuckDB; nothing is derived here.
  const series = useMemo(() => data?.candles ?? [], [data]);

  if (!symbol) {
    return (
      <Stack align="center" justify="center" h="100%">
        <Text c="dimmed" size="sm">
          Select a stock to chart it against the 30/50/200 DMA
        </Text>
      </Stack>
    );
  }

  const last = series.at(-1);
  const first = series.at(0);
  const changed =
    last && first ? ((last.close - first.close) / first.close) * 100 : null;
  const up = (changed ?? 0) >= 0;
  const priceColor = up
    ? "var(--mantine-color-teal-6)"
    : "var(--mantine-color-red-6)";

  // Where price sits against the 200 DMA is the screen's ranking metric, so it
  // belongs in the header rather than buried in a tooltip.
  const dist200 =
    last?.sma200 != null
      ? ((last.close - last.sma200) / last.sma200) * 100
      : null;

  // Each average only starts once its window is full, so a short history makes
  // the 200 DMA begin partway across. Without a note that reads as a bug.
  const sma200Start = series.findIndex((c) => c.sma200 != null);
  const partial200 = sma200Start > 0;

  return (
    <Stack gap={4} h="100%">
      <Group justify="space-between" align="flex-end" wrap="nowrap">
        <div style={{ minWidth: 0 }}>
          <Group gap="xs" wrap="nowrap">
            <Title order={5} style={{ whiteSpace: "nowrap" }}>
              {data?.meta?.name ?? symbol}
            </Title>
            {data?.meta?.sector && (
              <Text size="xs" c="dimmed">
                {data.meta.sector}
              </Text>
            )}
          </Group>
          <Group gap="xs" wrap="nowrap">
            <Text size="lg" fw={600} className="numeric">
              {fmtPrice(last?.close)}
            </Text>
            {changed != null && (
              <Text size="xs" c={up ? "teal" : "red"}>
                {up ? "+" : ""}
                {changed.toFixed(2)}% range
              </Text>
            )}
            {dist200 != null && (
              <Badge
                size="xs"
                variant="light"
                color={dist200 >= 0 ? "teal" : "red"}
              >
                {dist200 >= 0 ? "+" : ""}
                {dist200.toFixed(2)}% vs 200 DMA
              </Badge>
            )}
            {last?.rsi14 != null && (
              <Badge
                size="xs"
                variant="light"
                color={
                  last.rsi14 >= 70 ? "red" : last.rsi14 <= 30 ? "teal" : "gray"
                }
              >
                RSI {last.rsi14.toFixed(0)}
              </Badge>
            )}
          </Group>
        </div>
        <Group gap="xs" wrap="nowrap">
          <Switch
            size="xs"
            label="Volume"
            checked={showVolume}
            onChange={(e) => setShowVolume(e.currentTarget.checked)}
          />
          <SegmentedControl
            size="xs"
            data={RANGES}
            value={range}
            onChange={setRange}
          />
        </Group>
      </Group>

      {partial200 && (
        <Text size="xs" c="dimmed">
          200 DMA begins {fmtDate(series[sma200Start].date)} — it needs 200
          sessions, and only {series.length} are loaded for this range.
        </Text>
      )}
      {error && <Alert color="red">{(error as Error).message}</Alert>}
      {isLoading && (
        <Group justify="center" py="xl">
          <Loader size="sm" />
        </Group>
      )}

      {!isLoading && series.length > 0 && (
        <ResponsiveContainer width="100%" height="100%" minHeight={200}>
          <ComposedChart
            data={series}
            margin={{ top: 4, right: 4, bottom: 0, left: 0 }}
          >
            <defs>
              <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={priceColor} stopOpacity={0.26} />
                <stop offset="100%" stopColor={priceColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={GRID}
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tickFormatter={fmtDate}
              minTickGap={52}
              tick={AXIS}
              stroke="var(--mantine-color-dimmed)"
            />
            <YAxis
              yAxisId="price"
              domain={["auto", "auto"]}
              width={58}
              tick={AXIS}
              tickFormatter={(v: number) => v.toFixed(0)}
              stroke="var(--mantine-color-dimmed)"
            />
            {/* Volume shares the x axis on its own hidden scale, kept to the
                lower third so it reads as context rather than competing. */}
            <YAxis
              yAxisId="vol"
              orientation="right"
              domain={[0, (m: number) => m * 3]}
              hide
            />

            <Tooltip
              labelFormatter={(l) => fmtDate(String(l))}
              formatter={(v, name) =>
                name === "Volume" ? fmtCompact(Number(v)) : fmtPrice(Number(v))
              }
              contentStyle={TOOLTIP_STYLE}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} iconSize={8} />

            {showVolume && (
              <Bar
                yAxisId="vol"
                dataKey="volume"
                name="Volume"
                fill="var(--mantine-color-dark-3)"
                isAnimationActive={false}
              />
            )}

            <Area
              yAxisId="price"
              type="monotone"
              dataKey="close"
              name="Close"
              stroke={priceColor}
              strokeWidth={1.6}
              fill="url(#priceFill)"
              dot={false}
              isAnimationActive={false}
            />
            {MAS.map((ma) => (
              <Line
                key={ma.key}
                yAxisId="price"
                type="monotone"
                dataKey={ma.key}
                name={ma.label}
                stroke={ma.color}
                strokeWidth={1}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            ))}

            {/* The 52-week high: the level the CAR window is measured from.
                Declared after the series so it paints above them. */}
            {last?.high_52w != null && (
              <ReferenceLine
                yAxisId="price"
                y={last.high_52w}
                stroke="var(--mantine-color-yellow-7)"
                strokeDasharray="3 4"
                ifOverflow="extendDomain"
                label={{
                  value: `52w high ${fmtPrice(last.high_52w)}`,
                  position: "insideTopRight",
                  fill: "var(--mantine-color-yellow-7)",
                  fontSize: 10,
                }}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </Stack>
  );
}
