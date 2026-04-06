import { KinesisClient, PutRecordCommand } from "@aws-sdk/client-kinesis";

export interface PublishInput {
  partitionKey: string;
  payload: string;
}

export class KinesisPublisher {
  private readonly client: KinesisClient;
  private readonly streamName: string;

  public constructor(region: string, streamName: string) {
    this.client = new KinesisClient({ region });
    this.streamName = streamName;
  }

  public async publish(input: PublishInput): Promise<void> {
    await this.client.send(
      new PutRecordCommand({
        StreamName: this.streamName,
        Data: Buffer.from(input.payload, "utf-8"),
        PartitionKey: input.partitionKey,
      }),
    );
  }
}
