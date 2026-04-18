import { EventSource } from "eventsource";
import producer from "../kafka/producer.js";
import { error, info } from "../utils/logger.js";
import { WikimediaRecentChange } from "../types/wikimedia.js";
import config from "../config/index.js";

export interface StopHandle {
	stop: () => void;
}

export function listenRecentChanges(): StopHandle {
	const source = new EventSource(config.wikipedia.sseUrl);
	let processed = 0;

	source.addEventListener("open", () => {
		info(`Connected to Wikipedia SSE stream: ${config.wikipedia.sseUrl}`);
	});

	source.addEventListener("error", (event: Event) => {
		const err = event as Event & { code?: number; message?: string };
		const code = err.code ?? "unknown";
		const message = err.message ?? "unknown";
		error(`SSE error (code=${String(code)}): ${message}`);
	});

	source.addEventListener("message", (event: MessageEvent) => {
		void handleMessage(event.data)
			.then(() => {
				processed += 1;
				if (processed % config.logEveryNEvents === 0) {
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

async function handleMessage(data: string): Promise<void> {
	const parsed: WikimediaRecentChange = JSON.parse(data);

	await producer.send({
		topic: "wikipedia-stream",
		messages: [{ value: JSON.stringify(parsed) }],
	});
}
