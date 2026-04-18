import { connectProducer, disconnectProducer } from "./kafka/producer.js";
import { listenRecentChanges } from "./wikipedia/listenRecentChanges.js";
import { error, info } from "./utils/logger.js";

async function main(): Promise<void> {
	await connectProducer();

	const listener = listenRecentChanges();

	const shutdown = async (signal: string): Promise<void> => {
		info(`Received ${signal}. Shutting down...`);
		listener.stop();
		await disconnectProducer();
		process.exit(0);
	};

	process.on("SIGINT", () => shutdown("SIGINT"));
	process.on("SIGTERM", () => shutdown("SIGTERM"));
}

main().catch((err) => {
	error(`Startup failed: ${err.message}`);
	process.exit(1);
});

