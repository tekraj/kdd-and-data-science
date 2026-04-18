import { Kafka, Producer } from "kafkajs";
import config from "../config/index.js";
import { error, info } from "../utils/logger.js";

const kafka = new Kafka({
	clientId: "data-ingestion",
	brokers: config.kafka.brokers,
});

const producer: Producer = kafka.producer();

export async function connectProducer(): Promise<void> {
	await producer.connect();
	info("Kafka producer connected");
}

export async function disconnectProducer(): Promise<void> {
	await producer.disconnect();
	info("Kafka producer disconnected");
}

export default producer;
