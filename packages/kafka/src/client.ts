import { Kafka } from "kafkajs";

export const createKafkaClient = (service: string) => {
  const brokers =
    process.env.KAFKA_BROKERS?.split(",")
      .map((broker) => broker.trim())
      .filter(Boolean) ?? ["localhost:9094", "localhost:9095", "localhost:9096"];

  return new Kafka({
    clientId: service,
    brokers,
  });
};
