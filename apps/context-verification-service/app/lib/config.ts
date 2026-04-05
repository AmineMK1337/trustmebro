const csv = (v: string | undefined, fallback: string[]) =>
  v ? v.split(",").map((s) => s.trim()).filter(Boolean) : fallback;

export const config = {
  serviceName: "context-verification-service",
  port: Number(process.env.PORT ?? 3000),

  // Kafka
  kafkaBrokers: csv(process.env.KAFKA_BROKERS, [
    "localhost:9094",
    "localhost:9095",
    "localhost:9096",
  ]),
  inputTopic: process.env.INPUT_TOPIC ?? "content-verification.requested",
  outputTopic: process.env.OUTPUT_TOPIC ?? "context-verification.completed",
  consumerGroup:
    process.env.CONSUMER_GROUP ?? "context-verification-service-group",

  // API Keys
  geminiApiKey: process.env.GEMINI_API_KEY ?? "",
  imgbbApiKey: process.env.IMGBB_API_KEY ?? "",
  serpApiKey: process.env.SERPAPI_API_KEY ?? "",
};
