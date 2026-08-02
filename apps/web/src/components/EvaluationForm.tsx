import { useState } from "react";
import type { FormEvent } from "react";
import type { EvaluationBody } from "../types";

const DIMENSIONS: { key: keyof EvaluationBody; label: string }[] = [
  { key: "validityRating", label: "Validity" },
  { key: "commercialRelevanceRating", label: "Commercial relevance" },
  { key: "noveltyRating", label: "Novelty" },
  { key: "evidenceQualityRating", label: "Evidence quality" },
  { key: "actionabilityRating", label: "Actionability" },
];

export function EvaluationForm({
  onSubmit,
  isPending,
  isDone,
  showMissedValidGap = false,
}: {
  onSubmit: (body: EvaluationBody) => void;
  isPending: boolean;
  isDone: boolean;
  showMissedValidGap?: boolean;
}) {
  const [evaluatorName, setEvaluatorName] = useState("");
  const [ratings, setRatings] = useState<Record<string, number>>({
    validityRating: 3,
    commercialRelevanceRating: 3,
    noveltyRating: 3,
    evidenceQualityRating: 3,
    actionabilityRating: 3,
  });
  const [acceptedIntoPlan, setAcceptedIntoPlan] = useState(false);
  const [markedMissedValidGap, setMarkedMissedValidGap] = useState(false);
  const [notes, setNotes] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const body: EvaluationBody = {
      evaluatorName: evaluatorName.trim() || "anonymous",
      validityRating: ratings.validityRating ?? 3,
      commercialRelevanceRating: ratings.commercialRelevanceRating ?? 3,
      noveltyRating: ratings.noveltyRating ?? 3,
      evidenceQualityRating: ratings.evidenceQualityRating ?? 3,
      actionabilityRating: ratings.actionabilityRating ?? 3,
      acceptedIntoPlan,
      notes: notes.trim(),
    };
    if (showMissedValidGap) {
      body.markedMissedValidGap = markedMissedValidGap;
    }
    onSubmit(body);
  };

  if (isDone) {
    return (
      <div className="callout callout-info" role="status">
        Evaluation submitted. Thank you.
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <label>Evaluator name</label>
      <input
        type="text"
        value={evaluatorName}
        onChange={(e) => setEvaluatorName(e.target.value)}
        placeholder="your name"
      />
      <div className="grid-2">
        {DIMENSIONS.map((d) => (
          <div key={d.key}>
            <label htmlFor={`${d.key}`}>
              {d.label} ({ratings[d.key] ?? 3})
            </label>
            <input
              id={`${d.key}`}
              type="range"
              min={1}
              max={5}
              step={1}
              value={ratings[d.key] ?? 3}
              onChange={(e) =>
                setRatings((r) => ({
                  ...r,
                  [d.key]: Number(e.target.value),
                }))
              }
            />
          </div>
        ))}
      </div>
      <div className="checkbox-row">
        <input
          id="acceptedIntoPlan"
          type="checkbox"
          checked={acceptedIntoPlan}
          onChange={(e) => setAcceptedIntoPlan(e.target.checked)}
        />
        <label htmlFor="acceptedIntoPlan">Accepted into plan</label>
      </div>
      {showMissedValidGap && (
        <div className="checkbox-row">
          <input
            id="markedMissedValidGap"
            type="checkbox"
            checked={markedMissedValidGap}
            onChange={(e) => setMarkedMissedValidGap(e.target.checked)}
          />
          <label htmlFor="markedMissedValidGap">
            Mark as missed valid gap (should not have been rejected)
          </label>
        </div>
      )}
      <label htmlFor="notes">Notes</label>
      <textarea
        id="notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      <div className="btn-row">
        <button type="submit" disabled={isPending}>
          {isPending ? "Submitting…" : "Submit evaluation"}
        </button>
      </div>
    </form>
  );
}
