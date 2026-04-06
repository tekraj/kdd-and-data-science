import { KinesisPublisher } from "./aws/kinesisPublisher.js";
import { getConfig } from "./config/env.js";
import { listenRecentChanges } from "./wikipedia/listenRecentChanges.js";
import { error, info } from "./utils/logger.js";

function main(): void {
	const config = getConfig();

	info(
		`Starting Wikipedia SSE -> Kinesis bridge (stream=${config.kinesisStreamName}, region=${config.awsRegion})`,
	);

	const publisher = new KinesisPublisher(config.awsRegion, config.kinesisStreamName);
	const listener = listenRecentChanges({
		sseUrl: config.wikipediaSseUrl,
		publisher,
		logEveryNEvents: config.logEveryNEvents,
	});

	const shutdown = (signal: string): void => {
		info(`Received ${signal}. Shutting down...`);
		listener.stop();
		process.exit(0);
	};

	process.on("SIGINT", () => shutdown("SIGINT"));
	process.on("SIGTERM", () => shutdown("SIGTERM"));
}

try {
	main();
} catch (cause: unknown) {
	const message = cause instanceof Error ? cause.message : "Unknown startup failure";
	error(`Startup failed: ${message}`);
	process.exit(1);
}

