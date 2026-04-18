import dotenv from "dotenv";

dotenv.config();

const config = {
	kafka: {
		brokers: (process.env.KAFKA_BROKERS || "localhost:9092").split(","),
	},
	wikipedia: {
		sseUrl: process.env.WIKIPEDIA_SSE_URL || "https://stream.wikimedia.org/v2/stream/recentchange",
	},
	logEveryNEvents: parseInt(process.env.LOG_EVERY_N_EVENTS || "10", 10),
};

export default config;
