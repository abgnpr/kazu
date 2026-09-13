import { createTheme, type MantineColorsTuple } from "@mantine/core";

// Muted blue-grey accent: dense financial tables get unreadable fast when the
// accent colour competes with the red/green of the price changes.
const accent: MantineColorsTuple = [
  "#eef3f9",
  "#dde3ec",
  "#b8c5d8",
  "#90a6c4",
  "#6f8cb3",
  "#5a7ca9",
  "#4e74a6",
  "#3f6392",
  "#365783",
  "#2a4b74",
];

export const theme = createTheme({
  primaryColor: "accent",
  colors: { accent },
  defaultRadius: "sm",
  fontFamily:
    "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  fontFamilyMonospace:
    "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
  headings: { fontWeight: "600" },
  components: {
    Table: { defaultProps: { fontSize: "sm", verticalSpacing: "xs", horizontalSpacing: "md" } },
  },
});

/** Semantic colours for gains/losses, used by both tables and charts. */
export const TONE = {
  up: "var(--mantine-color-teal-6)",
  down: "var(--mantine-color-red-6)",
  neutral: "var(--mantine-color-dimmed)",
} as const;
