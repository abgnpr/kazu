import {
  ActionIcon,
  Anchor,
  Divider,
  Group,
  Popover,
  Stack,
  Text,
  Tooltip,
} from "@mantine/core";
import { IconInfoCircle } from "@tabler/icons-react";
import { useState } from "react";

import { useCoverage } from "../api/queries";
import { APP_AUTHOR, APP_NAME, APP_TAGLINE, APP_VERSION } from "../brand";

/** Authorship and build details. Kept out of the header chrome so the app reads
 *  as the product and the byline stays one click away. */
export function AboutMenu() {
  const [open, setOpen] = useState(false);
  const { data: coverage } = useCoverage();

  return (
    <Popover opened={open} onChange={setOpen} position="bottom-end" withArrow shadow="md" width={260}>
      <Popover.Target>
        <Tooltip label="About">
          <ActionIcon
            variant="subtle"
            color="gray"
            size="sm"
            aria-label="About this app"
            onClick={() => setOpen((o) => !o)}
          >
            <IconInfoCircle size={16} />
          </ActionIcon>
        </Tooltip>
      </Popover.Target>

      <Popover.Dropdown>
        <Stack gap={6}>
          <div>
            <Text size="sm" fw={600}>
              {APP_NAME}
            </Text>
            <Text size="xs" c="dimmed">
              {APP_TAGLINE}
            </Text>
          </div>

          <Divider />

          <Group justify="space-between" gap="xs">
            <Text size="xs" c="dimmed">
              Version
            </Text>
            <Text size="xs">{APP_VERSION}</Text>
          </Group>
          <Group justify="space-between" gap="xs">
            <Text size="xs" c="dimmed">
              Built by
            </Text>
            <Text size="xs" fw={600}>
              {APP_AUTHOR}
            </Text>
          </Group>
          {coverage && (
            <Group justify="space-between" gap="xs">
              <Text size="xs" c="dimmed">
                Data
              </Text>
              <Text size="xs">
                NSE · {coverage.sessions} sessions
              </Text>
            </Group>
          )}

          <Divider />

          <Text size="xs" c="dimmed">
            Market data from NSE end-of-day bhavcopy. Screening output is not
            investment advice.
          </Text>
          <Anchor href="https://www.nseindia.com" target="_blank" size="xs">
            nseindia.com
          </Anchor>
        </Stack>
      </Popover.Dropdown>
    </Popover>
  );
}
