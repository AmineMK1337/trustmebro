import express from "express";
import { createAdmin, createKafkaClient } from "@repo/kafka";

const serviceName = "kafka-service";
const port = Number(process.env.PORT ?? 8081);
const requiredTopics = [
  "content-verification.requested",
  "content-verification.completed",
  "source-verification.audit",
];

const kafka = createKafkaClient(serviceName);
const admin = createAdmin(kafka);
const app = express();

app.get("/health", (_req, res) => {
  res.status(200).json({
    service: serviceName,
    status: "ok",
    topics: requiredTopics,
    timestamp: Date.now(),
  });
});

const start = async () => {
  await admin.connect();
  await admin.ensureTopics(requiredTopics);

  app.listen(port, () => {
    console.log(`${serviceName} is running on port ${port} for TrustMeBro`);
  });
};

start().catch((error) => {
  console.error(error);
  process.exit(1);
});
