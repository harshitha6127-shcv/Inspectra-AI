export type DefectCategory =
  | "normal"
  | "crack"
  | "scratch"
  | "dent"
  | "stain"
  | "discoloration"
  | "dimensional_irregularity";

export type InspectionDecision = "PASS" | "DEFECTIVE" | "REVIEW_REQUIRED";
export type SeverityLevel = "Minor" | "Major" | "Critical" | "None";

export interface DefectRegionData {
  id: number;
  x: number;
  y: number;
  width: number;
  height: number;
  areaPx: number;
  areaMm2: number;
  aspectRatio: number;
  confidence: number;
}

export interface TTAVote {
  viewName: string;
  predictedClass: DefectCategory;
  confidence: number;
  anomalyScore: number;
}

export interface PartSample {
  id: string;
  name: string;
  material: "Brushed Aluminum" | "Ceramic Tile" | "Machined Steel" | "Molded Polymer";
  groundTruth: DefectCategory;
  description: string;
  lightingCondition: "Uniform Studio" | "Directional Spotlight" | "Shadowed Conveyor" | "High-Glare Flash";
  orientationDeg: number;
  baseColor: string;
  defectParams: {
    type: DefectCategory;
    cx: number;
    cy: number;
    radius?: number;
    length?: number;
    angleDeg?: number;
    severity: number;
  };
}

export interface InspectionResultData {
  decision: InspectionDecision;
  detectedType: DefectCategory;
  overallConfidence: number;
  anomalyScore: number;
  anomalyThreshold: number;
  classifierProbabilities: Record<DefectCategory, number>;
  dualModelAgreed: boolean;
  isBorderline: boolean;
  borderlineReason?: string;
  regions: DefectRegionData[];
  ttaVotes: TTAVote[];
  processingTimeMs: number;
  // Prompt 9 Severity Extensions
  severityScore: number;
  severityCategory: SeverityLevel;
  recommendedAction: string;
  severityColor: string;
}
