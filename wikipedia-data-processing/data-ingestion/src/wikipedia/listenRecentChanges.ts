import { EventSource } from "eventsource";

import { KinesisPublisher } from "../aws/kinesisPublisher.js";
import { error, info } from "../utils/logger.js";

interface WikimediaRecentChange {
  id?: string | number;
  meta?: {
    id?: string;
    uri?: string;
    dt?: string;
    domain?: string;
    stream?: string;
    request_id?: string;
  };
  title?: string;
  user?: string;
  type?: string;
  wiki?: string;
}

export interface ListenOptions {
  sseUrl: string;
  publisher: KinesisPublisher;
  logEveryNEvents: number;
}

export interface StopHandle {
  stop: () => void;
}

export function listenRecentChanges(options: ListenOptions): StopHandle {
  const source = new EventSource(options.sseUrl);
  let processed = 0;

  source.addEventListener("open", () => {
    info(`Connected to Wikipedia SSE stream: ${options.sseUrl}`);
  });

  source.addEventListener("error", (event: Event) => {
    const err = event as Event & { code?: number; message?: string };
    const code = err.code ?? "unknown";
    const message = err.message ?? "unknown";
    error(`SSE error (code=${String(code)}): ${message}`);
  });

  source.addEventListener("message", (event: MessageEvent) => {
    void handleMessage(event.data, options.publisher)
      .then(() => {
        processed += 1;
        if (processed % options.logEveryNEvents === 0) {
          info(`Processed and published ${processed} events`);
        }
      })
      .catch((cause: unknown) => {
        const message = cause instanceof Error ? cause.message : "Unknown error";
        error(`Failed to process SSE message: ${message}`);
      });
  });

  return {
    stop: () => {
      source.close();
      info("SSE listener stopped");
    },
  };
}

async function handleMessage(data: string, publisher: KinesisPublisher): Promise<void> {
  const parsed = JSON.parse(data) as WikimediaRecentChange;

  const partitionKey =
    parsed.wiki ??
    parsed.meta?.domain ??
    parsed.user ??
    parsed.title ??
    String(parsed.id ?? Date.now());

  await publisher.publish({
    partitionKey,
    payload: JSON.stringify(parsed),
  });
}
