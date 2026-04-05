/**
 * Content Verification Service Configuration
 *
 * All scoring thresholds, weights, and tunables are loaded from
 * environment variables with sensible defaults. Nothing is hard-coded
 * in the pipeline logic itself.
 */

const float = (v: string | undefined, fallback: number) =>
  v !== undefined ? parseFloat(v) : fallback;

const csv = (v: string | undefined, fallback: string[]) =>
  v ? v.split(",").map((s) => s.trim()).filter(Boolean) : fallback;

export const thresholds = {
  verified: float(process.env.THRESHOLD_VERIFIED, 0.7),
  suspicious: float(process.env.THRESHOLD_SUSPICIOUS, 0.4),
  concernCutoff: float(process.env.THRESHOLD_CONCERN, 0.5),
};

export const axisWeights = {
  contentAuthenticity: float(process.env.WEIGHT_CONTENT_AUTHENTICITY, 0.35),
  contextualConsistency: float(process.env.WEIGHT_CONTEXTUAL_CONSISTENCY, 0.3),
  sourceCredibility: float(process.env.WEIGHT_SOURCE_CREDIBILITY, 0.35),
};

export const scoring = {
  authenticityBase: float(process.env.SCORE_AUTHENTICITY_BASE, 0.7),
  authenticityTrustedBoost: float(process.env.SCORE_AUTHENTICITY_TRUSTED_BOOST, 0.2),
  authenticitySuspiciousTldPenalty: float(process.env.SCORE_AUTHENTICITY_SUSPICIOUS_TLD_PENALTY, 0.25),
  authenticityHomoglyphPenalty: float(process.env.SCORE_AUTHENTICITY_HOMOGLYPH_PENALTY, 0.3),
  authenticityMediaPenalty: float(process.env.SCORE_AUTHENTICITY_MEDIA_PENALTY, 0.05),
  consistencyBase: float(process.env.SCORE_CONSISTENCY_BASE, 0.65),
  consistencyNoNarrative: float(process.env.SCORE_CONSISTENCY_NO_NARRATIVE, 0.5),
  consistencyMisinfoPenaltyPerPhrase: float(process.env.SCORE_CONSISTENCY_MISINFO_PENALTY, 0.15),
  consistencyShortNarrativePenalty: float(process.env.SCORE_CONSISTENCY_SHORT_PENALTY, 0.1),
  consistencyDetailedBoost: float(process.env.SCORE_CONSISTENCY_DETAILED_BOOST, 0.05),
  consistencyTrustedSourceBoost: float(process.env.SCORE_CONSISTENCY_TRUSTED_BOOST, 0.15),
  consistencyCapsThreshold: float(process.env.SCORE_CONSISTENCY_CAPS_THRESHOLD, 0.5),
  consistencyCapsPenalty: float(process.env.SCORE_CONSISTENCY_CAPS_PENALTY, 0.1),
  consistencyPunctuationPenalty: float(process.env.SCORE_CONSISTENCY_PUNCTUATION_PENALTY, 0.05),
  credibilityBase: float(process.env.SCORE_CREDIBILITY_BASE, 0.55),
  credibilityTrustedScore: float(process.env.SCORE_CREDIBILITY_TRUSTED, 0.92),
  credibilitySuspiciousTldPenalty: float(process.env.SCORE_CREDIBILITY_SUSPICIOUS_TLD_PENALTY, 0.2),
  credibilitySubdomainPenalty: float(process.env.SCORE_CREDIBILITY_SUBDOMAIN_PENALTY, 0.1),
  credibilityHomoglyphPenalty: float(process.env.SCORE_CREDIBILITY_HOMOGLYPH_PENALTY, 0.3),
  credibilitySocialMediaCap: float(process.env.SCORE_CREDIBILITY_SOCIAL_MEDIA_CAP, 0.4),
  credibilityIpPenalty: float(process.env.SCORE_CREDIBILITY_IP_PENALTY, 0.25),
  credibilityLongUrlPenalty: float(process.env.SCORE_CREDIBILITY_LONG_URL_PENALTY, 0.05),
  historicalContextWeight: float(process.env.SCORE_HISTORICAL_CONTEXT_WEIGHT, 0.85),
  historicalSourceWeight: float(process.env.SCORE_HISTORICAL_SOURCE_WEIGHT, 0.15),
  syntheticFactor: float(process.env.SCORE_SYNTHETIC_FACTOR, 0.9),
  narrativeMinLength: float(process.env.NARRATIVE_MIN_LENGTH, 20),
  narrativeGoodLength: float(process.env.NARRATIVE_GOOD_LENGTH, 50),
  urlMaxLength: float(process.env.URL_MAX_LENGTH, 200),
};

export const domainLists = {
  trustedDomains: csv(process.env.TRUSTED_DOMAINS, [
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
    "nytimes.com", "washingtonpost.com", "theguardian.com",
    "aljazeera.com", "france24.com", "dw.com",
    "gov.uk", "gov.sa", "who.int", "un.org",
    "nature.com", "sciencedirect.com", "pubmed.ncbi.nlm.nih.gov",
  ]),
  suspiciousTlds: csv(process.env.SUSPICIOUS_TLDS, [
    ".xyz", ".click", ".top", ".buzz", ".loan", ".work",
    ".gq", ".ml", ".tk", ".cf", ".ga", ".cc",
  ]),
  misinformationKeywords: csv(process.env.MISINFO_KEYWORDS, [
    "breaking exclusive", "they don't want you to know",
    "exposed", "cover-up", "leaked classified", "shocking truth",
    "mainstream media won't show", "banned video", "censored",
    "wake up sheeple", "100% proof",
  ]),
};

export const serviceConfig = {
  serviceName: "content-verification-service",
  port: Number(process.env.PORT ?? 8082),
  kafkaBrokers: csv(process.env.KAFKA_BROKERS, [
    "localhost:9094", "localhost:9095", "localhost:9096",
  ]),
  inputTopic: process.env.INPUT_TOPIC ?? "content-verification.requested",
  outputTopic: process.env.OUTPUT_TOPIC ?? "content-verification.completed",
};
