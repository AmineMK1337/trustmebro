/**
 * Content Verification Microservice for TrustMeBro
 *
 * Consumes content-verification.requested Kafka events,
 * runs the verification pipeline, and publishes results
 * on content-verification.completed.
 */

import express from "express";
import { createKafkaClient, createConsumer, createProducer } from "@repo/kafka";
import { serviceConfig } from "./config.js";
import {
  runVerificationPipeline,
  type VerificationRequest,
} from "./pipeline.js";

const kafka = createKafkaClient(serviceConfig.serviceName);
const consumer = createConsumer(kafka, `${serviceConfig.serviceName}-group`);
const producer = createProducer(kafka);

const app = express();

app.get("/health", (_req, res) => {
  res.status(200).json({
    service: serviceConfig.serviceName,
    status: "ok",
    mode: "kafka-consumer-worker",
    timestamp: Date.now(),
  });
});

const processVerificationRequest = async (message: unknown) => {
  const request = message as VerificationRequest;

  console.log(
    `[${serviceConfig.serviceName}] Processing verification for ${request.postId} (source: ${request.source})`,
  );

  const result = runVerificationPipeline(request);

  console.log(
    `[${serviceConfig.serviceName}] Verification complete: ${result.status} (trust: ${result.finalTrustRating})`,
  );

  await producer.send(serviceConfig.outputTopic, result);

  console.log(
    `[${serviceConfig.serviceName}] Published result on ${serviceConfig.outputTopic}`,
  );
};

const start = async () => {
  await producer.connect();
  console.log(`[${serviceConfig.serviceName}] Kafka producer connected`);

  await consumer.connect();
  console.log(`[${serviceConfig.serviceName}] Kafka consumer connected`);

  await consumer.subscribe([
    {
      topicName: serviceConfig.inputTopic,
      topicHandler: processVerificationRequest,
    },
  ]);

  console.log(
    `[${serviceConfig.serviceName}] Subscribed to ${serviceConfig.inputTopic}`,
  );

  app.listen(serviceConfig.port, () => {
    console.log(
      `${serviceConfig.serviceName} is running on port ${serviceConfig.port} for TrustMeBro`,
    );
  });
};

start().catch((error) => {
  console.error(`[${serviceConfig.serviceName}] Failed to start:`, error);
  process.exit(1);
});
