export interface AppConfig {
  awsRegion: string;
  kinesisStreamName: string;
  wikipediaSseUrl: string;
  logEveryNEvents: number;
}

export function getConfig(): AppConfig {
  const awsRegion = process.env.AWS_REGION;
  const kinesisStreamName = process.env.KINESIS_STREAM_NAME;

  if (!awsRegion) {
    throw new Error("Missing required env var: AWS_REGION");
  }

  if (!kinesisStreamName) {
    throw new Error("Missing required env var: KINESIS_STREAM_NAME");
  }

  const logEveryNEventsRaw = process.env.LOG_EVERY_N_EVENTS ?? "100";
  const logEveryNEvents = Number.parseInt(logEveryNEventsRaw, 10);

  if (!Number.isFinite(logEveryNEvents) || logEveryNEvents <= 0) {
    throw new Error("LOG_EVERY_N_EVENTS must be a positive integer");
  }

  return {
    awsRegion,
    kinesisStreamName,
    wikipediaSseUrl:
      process.env.WIKIPEDIA_SSE_URL ??
      "https://stream.wikimedia.org/v2/stream/recentchange",
    logEveryNEvents,
  };
}
