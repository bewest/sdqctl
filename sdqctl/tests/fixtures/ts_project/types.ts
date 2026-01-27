/**
 * Treatment represents a diabetes treatment action.
 */
export interface Treatment {
  id: string;
  timestamp: Date;
  type: "bolus" | "basal" | "correction";
  units: number;
  notes?: string;
}

export type TreatmentStatus = "pending" | "delivered" | "failed";

export class TreatmentProcessor {
  private treatments: Treatment[] = [];

  async process(treatment: Treatment): Promise<void> {
    this.treatments.push(treatment);
  }

  count(): number {
    return this.treatments.length;
  }
}

export enum TreatmentType {
  BOLUS = "bolus",
  BASAL = "basal",
  CORRECTION = "correction",
}
