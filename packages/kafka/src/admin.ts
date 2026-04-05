import type { Admin, Kafka } from "kafkajs";

export const createAdmin = (kafka: Kafka) => {
  const admin: Admin = kafka.admin();

  const connect = async () => {
    await admin.connect();
  };

  const ensureTopics = async (topics: string[]) => {
    if (topics.length === 0) {
      return false;
    }

    return admin.createTopics({
      waitForLeaders: true,
      topics: topics.map((topic) => ({
        topic,
        numPartitions: 3,
        replicationFactor: 3,
      })),
    });
  };

  const disconnect = async () => {
    await admin.disconnect();
  };

  return { connect, ensureTopics, disconnect };
};
