import { PartSample } from "../types/inspection";

export const SAMPLE_PARTS: PartSample[] = [
  {
    id: "SAMPLE-01-NORM",
    name: "Machined Steel Flange",
    material: "Machined Steel",
    groundTruth: "normal",
    description: "Defect-free precision manufactured surface with uniform concentric toolmarks.",
    lightingCondition: "Uniform Studio",
    orientationDeg: 0,
    baseColor: "#9ca3af",
    defectParams: {
      type: "normal",
      cx: 128,
      cy: 128,
      severity: 0
    }
  },
  {
    id: "SAMPLE-02-CRACK",
    name: "Turbine Blade Root",
    material: "Brushed Aluminum",
    groundTruth: "crack",
    description: "Fatigue micro-crack propagating along stress concentration boundary.",
    lightingCondition: "Directional Spotlight",
    orientationDeg: 12,
    baseColor: "#94a3b8",
    defectParams: {
      type: "crack",
      cx: 135,
      cy: 110,
      length: 75,
      angleDeg: 42,
      severity: 0.85
    }
  },
  {
    id: "SAMPLE-03-SCRATCH",
    name: "Polished Enclosure Panel",
    material: "Molded Polymer",
    groundTruth: "scratch",
    description: "Linear tooling abrasion with adjacent specular reflection ridge.",
    lightingCondition: "High-Glare Flash",
    orientationDeg: 0,
    baseColor: "#cbd5e1",
    defectParams: {
      type: "scratch",
      cx: 105,
      cy: 85,
      length: 110,
      angleDeg: -28,
      severity: 0.78
    }
  },
  {
    id: "SAMPLE-04-DENT",
    name: "Automotive Stamping Sheet",
    material: "Brushed Aluminum",
    groundTruth: "dent",
    description: "Localized 3D mechanical depression with shadow-highlight illumination gradient.",
    lightingCondition: "Shadowed Conveyor",
    orientationDeg: 0,
    baseColor: "#9ca3af",
    defectParams: {
      type: "dent",
      cx: 140,
      cy: 130,
      radius: 26,
      severity: 0.82
    }
  },
  {
    id: "SAMPLE-05-STAIN",
    name: "Glazed Ceramic Substrate",
    material: "Ceramic Tile",
    groundTruth: "stain",
    description: "Irregular organic lubricant puddle with diffuse semi-transparent boundary.",
    lightingCondition: "Uniform Studio",
    orientationDeg: 0,
    baseColor: "#e2e8f0",
    defectParams: {
      type: "stain",
      cx: 120,
      cy: 135,
      radius: 34,
      severity: 0.72
    }
  },
  {
    id: "SAMPLE-06-DISCOLOR",
    name: "Laser-Welded Connector",
    material: "Machined Steel",
    groundTruth: "discoloration",
    description: "Thermal oxidation halo (heat tint) caused by localized laser over-penetration.",
    lightingCondition: "Directional Spotlight",
    orientationDeg: 0,
    baseColor: "#94a3b8",
    defectParams: {
      type: "discoloration",
      cx: 125,
      cy: 125,
      radius: 40,
      severity: 0.68
    }
  },
  {
    id: "SAMPLE-07-DIMENSIONAL",
    name: "Die-Cast Housing Rim",
    material: "Brushed Aluminum",
    groundTruth: "dimensional_irregularity",
    description: "Edge chip fracture and missing material along outer perimeter boundary.",
    lightingCondition: "Shadowed Conveyor",
    orientationDeg: 0,
    baseColor: "#9ca3af",
    defectParams: {
      type: "dimensional_irregularity",
      cx: 230,
      cy: 128,
      radius: 24,
      severity: 0.90
    }
  },
  {
    id: "SAMPLE-08-BORDERLINE",
    name: "Precision Spacer Shim",
    material: "Machined Steel",
    groundTruth: "scratch",
    description: "Low-contrast faint surface mark on specular grain (Borderline Case requiring QA review).",
    lightingCondition: "High-Glare Flash",
    orientationDeg: 45,
    baseColor: "#9ca3af",
    defectParams: {
      type: "scratch",
      cx: 130,
      cy: 140,
      length: 35,
      angleDeg: 60,
      severity: 0.38
    }
  }
];
