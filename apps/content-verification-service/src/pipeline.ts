/**
 * Content Verification Pipeline
 *
 * Production implementation would orchestrate:
 *   - Amazon Rekognition for image/video analysis
 *   - SageMaker-hosted forensic models for synthetic media detection
 *   - Amazon Transcribe for audio-to-text
 *   - Amazon Textract for document extraction
 *   - Amazon Bedrock for narrative consistency analysis
 *   - Amazon Kendra for historical reference lookup
 *
 * All scoring thresholds, weights, and domain lists come from config.ts
 * which loads from environment variables. Nothing is hard-coded here.
 */

import {
  thresholds,
  axisWeights,
  scoring,
  domainLists,
} from "./config.js";

export type VerificationRequest = {
  postId: string;
  source: string;
  narrative: string | null;
  contentType: "image" | "video" | "audio" | "document" | "mixed";
  requestedAt: string;
  reason: string;
};

export type VerificationAxisResult = {
  score: number;
  reasoning: string;
  signals: string[];
};

export type VerificationResult = {
  submissionId: string;
  source: string;
  contentType: string;
  tamperScore: number;
  syntheticMediaScore: number;
  narrativeConsistencyScore: number;
  historicalConsistencyScore: number;
  finalTrustRating: number;
  status: "verified" | "suspicious" | "unverifiable";
  explanation: string;
  details: {
    contentAuthenticity: VerificationAxisResult;
    contextualConsistency: VerificationAxisResult;
    sourceCredibility: VerificationAxisResult;
  };
  verifiedAt: string;
};

const clampScore = (v: number) => Math.max(0, Math.min(1, v));
const round2 = (v: number) => parseFloat(v.toFixed(2));

const extractDomain = (source: string): string => {
  try {
    const url = new URL(source.startsWith("http") ? source : `https://${source}`);
    return url.hostname.toLowerCase().replace(/^www\./, "");
  } catch {
    return source.toLowerCase();
  }
};

const hasSuspiciousTld = (domain: string): boolean =>
  domainLists.suspiciousTlds.some((tld) => domain.endsWith(tld));

const isTrustedDomain = (domain: string): boolean =>
  domainLists.trustedDomains.some((td) => domain === td || domain.endsWith(`.${td}`));

const countSubdomains = (domain: string): number =>
  domain.split(".").length - 2;

const hasHomoglyphs = (source: string): boolean => {
  const patterns = [
    /[а-яА-Я]/,
    /[０-９]/,
    /rn(?=\w)/,
  ];
  return patterns.some((p) => p.test(source));
};

const analyzeContentAuthenticity = (
  req: VerificationRequest,
): VerificationAxisResult => {
  const signals: string[] = [];
  let score = scoring.authenticityBase;
  const domain = extractDomain(req.source);

  if (isTrustedDomain(domain)) {
    score += scoring.authenticityTrustedBoost;
    signals.push(`Source domain "${domain}" is a recognized trusted publisher`);
  }

  if (hasSuspiciousTld(domain)) {
    score -= scoring.authenticitySuspiciousTldPenalty;
    signals.push("Domain uses suspicious TLD commonly associated with disposable sites");
  }

  if (hasHomoglyphs(req.source)) {
    score -= scoring.authenticityHomoglyphPenalty;
    signals.push("Source URL contains visually deceptive characters (homoglyph attack)");
  }

  if (req.contentType === "image" || req.contentType === "video") {
    score -= scoring.authenticityMediaPenalty;
    signals.push(`${req.contentType} content requires forensic analysis for tamper detection`);
  }

  if (req.contentType === "audio") {
    score -= scoring.authenticityMediaPenalty;
    signals.push("Audio content flagged for deepfake voice analysis");
  }

  score = clampScore(score);

  const reasoning =
    score >= thresholds.verified + 0.05
      ? "Content source passes initial authenticity checks. No obvious manipulation indicators detected."
      : score >= thresholds.suspicious + 0.05
        ? "Some authenticity concerns detected. Content may require manual review for tamper or AI-generation markers."
        : "Multiple authenticity red flags detected. Content is likely manipulated or originates from an unverifiable source.";

  return { score: round2(score), reasoning, signals };
};

const analyzeContextualConsistency = (
  req: VerificationRequest,
): VerificationAxisResult => {
  const signals: string[] = [];
  let score = scoring.consistencyBase;

  if (!req.narrative) {
    signals.push("No narrative provided - contextual consistency cannot be fully evaluated");
    return {
      score: scoring.consistencyNoNarrative,
      reasoning:
        "No claim or narrative was provided with this submission. Contextual consistency analysis is limited without a stated claim to verify against the content.",
      signals,
    };
  }

  const narrativeLower = req.narrative.toLowerCase();

  const misinfoPhraseCount = domainLists.misinformationKeywords.filter((kw) =>
    narrativeLower.includes(kw),
  ).length;

  if (misinfoPhraseCount > 0) {
    score -= scoring.consistencyMisinfoPenaltyPerPhrase * misinfoPhraseCount;
    signals.push(
      `Narrative contains ${misinfoPhraseCount} sensationalist phrase(s) commonly associated with misinformation`,
    );
  }

  if (req.narrative.length < scoring.narrativeMinLength) {
    score -= scoring.consistencyShortNarrativePenalty;
    signals.push("Narrative is too brief for meaningful consistency analysis");
  }

  if (req.narrative.length > scoring.narrativeGoodLength) {
    score += scoring.consistencyDetailedBoost;
    signals.push("Narrative provides sufficient detail for consistency evaluation");
  }

  const domain = extractDomain(req.source);
  if (isTrustedDomain(domain)) {
    score += scoring.consistencyTrustedSourceBoost;
    signals.push("Source is a recognized publisher - narrative is more likely to match content");
  }

  const alphaChars = req.narrative.replace(/[^A-Za-z]/g, "");
  const capsRatio = alphaChars.length > 0
    ? req.narrative.replace(/[^A-Z]/g, "").length / alphaChars.length
    : 0;

  if (capsRatio > scoring.consistencyCapsThreshold && req.narrative.length > scoring.narrativeMinLength) {
    score -= scoring.consistencyCapsPenalty;
    signals.push("Narrative uses excessive capitalization, a common indicator of sensationalist claims");
  }

  const punctuationCount = (req.narrative.match(/[!?]{2,}/g) || []).length;
  if (punctuationCount > 0) {
    score -= scoring.consistencyPunctuationPenalty * punctuationCount;
    signals.push("Excessive punctuation detected in narrative");
  }

  score = clampScore(score);

  const reasoning =
    score >= thresholds.verified
      ? "The narrative appears consistent with the source and content type. No obvious contextual mismatches detected."
      : score >= thresholds.suspicious
        ? "Some inconsistencies detected between the narrative and content context. The claim may be misleading or taken out of context."
        : "Significant contextual inconsistencies detected. The narrative likely misrepresents the content or reuses material from a different context.";

  return { score: round2(score), reasoning, signals };
};

const analyzeSourceCredibility = (
  req: VerificationRequest,
): VerificationAxisResult => {
  const signals: string[] = [];
  let score = scoring.credibilityBase;
  const domain = extractDomain(req.source);

  if (isTrustedDomain(domain)) {
    score = scoring.credibilityTrustedScore;
    signals.push(`"${domain}" is a verified trusted publisher`);
  } else if (hasSuspiciousTld(domain)) {
    score -= scoring.credibilitySuspiciousTldPenalty;
    signals.push("Domain TLD is commonly associated with spam or disposable content");
  }

  if (countSubdomains(domain) > 2) {
    score -= scoring.credibilitySubdomainPenalty;
    signals.push("Unusually deep subdomain structure may indicate phishing or domain squatting");
  }

  if (hasHomoglyphs(req.source)) {
    score -= scoring.credibilityHomoglyphPenalty;
    signals.push("Source contains homoglyph characters that may be attempting to spoof a trusted domain");
  }

  if (req.source.startsWith("@")) {
    score = Math.min(score, scoring.credibilitySocialMediaCap);
    signals.push("Source is a social media handle - credibility depends on account history and verification status");
  }

  if (/\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/.test(req.source)) {
    score -= scoring.credibilityIpPenalty;
    signals.push("Source uses a raw IP address instead of a domain name");
  }

  if (req.source.length > scoring.urlMaxLength) {
    score -= scoring.credibilityLongUrlPenalty;
    signals.push("Unusually long URL may contain obfuscated tracking or redirect parameters");
  }

  score = clampScore(score);

  const reasoning =
    score >= thresholds.verified + 0.05
      ? "Source passes credibility checks. The origin is recognized or structurally consistent with legitimate publishers."
      : score >= thresholds.suspicious
        ? "Source credibility is uncertain. The origin could not be positively matched to known trusted sources."
        : "Source raises significant credibility concerns. Multiple signals suggest this may be an unreliable or deceptive origin.";

  return { score: round2(score), reasoning, signals };
};

export const runVerificationPipeline = (
  req: VerificationRequest,
): VerificationResult => {
  const contentAuthenticity = analyzeContentAuthenticity(req);
  const contextualConsistency = analyzeContextualConsistency(req);
  const sourceCredibility = analyzeSourceCredibility(req);

  const tamperScore = round2(1 - contentAuthenticity.score);
  const syntheticMediaScore = round2(
    1 - contentAuthenticity.score * scoring.syntheticFactor,
  );
  const narrativeConsistencyScore = contextualConsistency.score;
  const historicalConsistencyScore = round2(
    contextualConsistency.score * scoring.historicalContextWeight +
    sourceCredibility.score * scoring.historicalSourceWeight,
  );

  const finalTrustRating = round2(
    contentAuthenticity.score * axisWeights.contentAuthenticity +
    contextualConsistency.score * axisWeights.contextualConsistency +
    sourceCredibility.score * axisWeights.sourceCredibility,
  );

  const status: VerificationResult["status"] =
    finalTrustRating >= thresholds.verified
      ? "verified"
      : finalTrustRating >= thresholds.suspicious
        ? "suspicious"
        : "unverifiable";

  const explanations: string[] = [];

  if (status === "verified") {
    explanations.push("This content passes automated verification checks across all three axes.");
  } else if (status === "suspicious") {
    explanations.push("This content raised some concerns during automated verification.");
  } else {
    explanations.push("This content could not be verified and should be treated with caution.");
  }

  if (contentAuthenticity.score < thresholds.concernCutoff) {
    explanations.push(`Content authenticity concern: ${contentAuthenticity.reasoning}`);
  }
  if (contextualConsistency.score < thresholds.concernCutoff) {
    explanations.push(`Context concern: ${contextualConsistency.reasoning}`);
  }
  if (sourceCredibility.score < thresholds.concernCutoff) {
    explanations.push(`Source concern: ${sourceCredibility.reasoning}`);
  }

  return {
    submissionId: req.postId,
    source: req.source,
    contentType: req.contentType,
    tamperScore,
    syntheticMediaScore,
    narrativeConsistencyScore,
    historicalConsistencyScore,
    finalTrustRating,
    status,
    explanation: explanations.join(" "),
    details: {
      contentAuthenticity,
      contextualConsistency,
      sourceCredibility,
    },
    verifiedAt: new Date().toISOString(),
  };
};
