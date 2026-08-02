import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api";
import {
  getActiveProjectId,
  setActiveProjectId,
  setProjectToken,
} from "../project";
import { parseList } from "../utils";
import type {
  Language,
  UploadFormat,
  BusinessBrief,
  CohortBody,
  OfferBody,
} from "../types";
import { Fieldset, ListField, TextAreaField, TextField } from "../components/fields";

// ---------- Local form state types ----------

interface ProjectForm {
  name: string;
  primaryDomain: string;
  defaultLanguage: Language;
  dayOfWeek: number;
  hourUtc: number;
}

interface BriefForm {
  businessModel: string;
  commercialObjective: string;
  currentCommercialPriority: string;
  primaryOffer: string;
  offerMechanism: string;
  desiredCustomerAction: string;
  mainConstraints: string;
  positioning: string;
  approvedClaims: string;
  prohibitedClaims: string;
  availableProof: string;
  knownOperationalLimitations: string;
  markdownNotes: string;
}

interface OfferForm {
  name: string;
  mechanism: string;
  desiredAction: string;
  approvedClaims: string;
  prohibitedClaims: string;
  proof: string;
  constraints: string;
}

interface CohortForm {
  name: string;
  roleIdentity: string;
  commercialSituation: string;
  trigger: string;
  activeProblem: string;
  currentWorkflow: string;
  currentBelief: string;
  desiredOutcome: string;
  objections: string;
  decisionCriteria: string;
  priority: number;
  offerFit: string;
  exclusionCriteria: string;
  exactLanguage: string;
}

interface UrlEntry {
  name: string;
  url: string;
}
interface PasteEntry {
  format: UploadFormat;
  name: string;
  content: string;
}

interface CompetitorSlot {
  urls: UrlEntry[];
  pastes: PasteEntry[];
}

// ---------- Defaults ----------

const emptyCohort = (): CohortForm => ({
  name: "",
  roleIdentity: "",
  commercialSituation: "",
  trigger: "",
  activeProblem: "",
  currentWorkflow: "",
  currentBelief: "",
  desiredOutcome: "",
  objections: "",
  decisionCriteria: "",
  priority: 3,
  offerFit: "",
  exclusionCriteria: "",
  exactLanguage: "",
});

const STEPS = [
  "Project",
  "Business Brief",
  "Primary Offer",
  "Cohorts",
  "Owned Content",
  "Voice of Customer",
  "Competitors",
  "Review",
];

// ---------- Reusable source editors ----------

function UrlEditor({
  entries,
  onChange,
}: {
  entries: UrlEntry[];
  onChange: (e: UrlEntry[]) => void;
}) {
  return (
    <div>
      {entries.map((entry, i) => (
        <div className="grid-2" key={i}>
          <TextField
            label="Name"
            value={entry.name}
            onChange={(v) =>
              onChange(entries.map((e, j) => (j === i ? { ...e, name: v } : e)))
            }
          />
          <TextField
            label="URL"
            type="url"
            value={entry.url}
            onChange={(v) =>
              onChange(entries.map((e, j) => (j === i ? { ...e, url: v } : e)))
            }
          />
          <div>
            <button
              type="button"
              className="secondary small"
              style={{ marginTop: 8 }}
              onClick={() => onChange(entries.filter((_, j) => j !== i))}
            >
              Remove URL
            </button>
          </div>
        </div>
      ))}
      <button
        type="button"
        className="secondary small"
        style={{ marginTop: 8 }}
        onClick={() => onChange([...entries, { name: "", url: "" }])}
      >
        + Add URL source
      </button>
    </div>
  );
}

function PasteEditor({
  entries,
  onChange,
}: {
  entries: PasteEntry[];
  onChange: (e: PasteEntry[]) => void;
}) {
  return (
    <div>
      {entries.map((entry, i) => (
        <div className="card" key={i} style={{ background: "var(--panel-2)" }}>
          <div className="grid-2">
            <TextField
              label="Name"
              value={entry.name}
              onChange={(v) =>
                onChange(
                  entries.map((e, j) => (j === i ? { ...e, name: v } : e)),
                )
              }
            />
            <div>
              <label>Format</label>
              <select
                value={entry.format}
                onChange={(v) =>
                  onChange(
                    entries.map((e, j) =>
                      j === i
                        ? { ...e, format: v.target.value as UploadFormat }
                        : e,
                    ),
                  )
                }
              >
                <option value="csv">csv</option>
                <option value="json">json</option>
                <option value="txt">txt</option>
                <option value="md">md</option>
              </select>
            </div>
          </div>
          <TextAreaField
            label="Pasted content"
            rows={4}
            value={entry.content}
            onChange={(v) =>
              onChange(
                entries.map((e, j) => (j === i ? { ...e, content: v } : e)),
              )
            }
          />
          <button
            type="button"
            className="secondary small"
            onClick={() => onChange(entries.filter((_, j) => j !== i))}
          >
            Remove paste
          </button>
        </div>
      ))}
      <button
        type="button"
        className="secondary small"
        style={{ marginTop: 8 }}
        onClick={() =>
          onChange([...entries, { format: "csv", name: "", content: "" }])
        }
      >
        + Add paste / upload
      </button>
    </div>
  );
}

// ---------- Connect existing / token panel ----------

function ConnectPanel() {
  const navigate = useNavigate();
  const [pid, setPid] = useState(getActiveProjectId() ?? "");
  const [token, setToken] = useState("");
  const [tokenLabel, setTokenLabel] = useState("browser-extension");
  const [generated, setGenerated] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const connect = () => {
    if (!pid.trim()) {
      setError("Enter a project id.");
      return;
    }
    setActiveProjectId(pid.trim());
    if (token.trim()) setProjectToken(token.trim());
    navigate("/");
  };

  const genToken = async () => {
    setError(null);
    setGenerated(null);
    if (!pid.trim()) {
      setError("Enter a project id first.");
      return;
    }
    setBusy(true);
    try {
      const res = await api.createToken({
        projectId: pid.trim(),
        label: tokenLabel.trim() || "extension",
      });
      setGenerated(res.token);
      setProjectToken(res.token);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to create token.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>Connect an existing / demo project</h2>
      <p className="field-hint">
        The worker&apos;s <code>pnpm demo</code> seeds a project. Paste its id
        (and optionally a token) to connect the dashboard to it.
      </p>
      <TextField
        label="Project id"
        value={pid}
        onChange={setPid}
        placeholder="uuid…"
      />
      <TextField
        label="Extension token (optional)"
        value={token}
        onChange={setToken}
      />
      <div className="btn-row">
        <button type="button" onClick={connect}>
          Connect &amp; open dashboard
        </button>
      </div>

      <h3 style={{ marginTop: 20 }}>Generate extension token</h3>
      <TextField label="Token label" value={tokenLabel} onChange={setTokenLabel} />
      <div className="btn-row">
        <button
          type="button"
          className="secondary"
          onClick={() => void genToken()}
          disabled={busy}
        >
          {busy ? "Generating…" : "Generate token"}
        </button>
      </div>
      {generated && (
        <div className="token-box">
          <strong>Copy now — shown once:</strong>
          <div className="mono">{generated}</div>
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}

// ---------- Main wizard ----------

export function SetupPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);

  const [project, setProject] = useState<ProjectForm>({
    name: "",
    primaryDomain: "",
    defaultLanguage: "en",
    dayOfWeek: 1,
    hourUtc: 3,
  });
  const [brief, setBrief] = useState<BriefForm>({
    businessModel: "",
    commercialObjective: "",
    currentCommercialPriority: "",
    primaryOffer: "",
    offerMechanism: "",
    desiredCustomerAction: "",
    mainConstraints: "",
    positioning: "",
    approvedClaims: "",
    prohibitedClaims: "",
    availableProof: "",
    knownOperationalLimitations: "",
    markdownNotes: "",
  });
  const [offer, setOffer] = useState<OfferForm>({
    name: "",
    mechanism: "",
    desiredAction: "",
    approvedClaims: "",
    prohibitedClaims: "",
    proof: "",
    constraints: "",
  });
  const [cohorts, setCohorts] = useState<CohortForm[]>([emptyCohort()]);
  const [ownedUrls, setOwnedUrls] = useState<UrlEntry[]>([]);
  const [ownedPastes, setOwnedPastes] = useState<PasteEntry[]>([]);
  const [vocPastes, setVocPastes] = useState<PasteEntry[]>([]);
  const [competitors, setCompetitors] = useState<CompetitorSlot[]>([
    { urls: [], pastes: [] },
    { urls: [], pastes: [] },
    { urls: [], pastes: [] },
  ]);

  const [submitting, setSubmitting] = useState(false);
  const [log, setLog] = useState<string[]>([]);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const patchProject = (p: Partial<ProjectForm>) =>
    setProject((s) => ({ ...s, ...p }));
  const patchBrief = (p: Partial<BriefForm>) => setBrief((s) => ({ ...s, ...p }));
  const patchOffer = (p: Partial<OfferForm>) => setOffer((s) => ({ ...s, ...p }));
  const patchCohort = (i: number, p: Partial<CohortForm>) =>
    setCohorts((list) => list.map((c, j) => (j === i ? { ...c, ...p } : c)));
  const patchCompetitor = (i: number, p: Partial<CompetitorSlot>) =>
    setCompetitors((list) => list.map((c, j) => (j === i ? { ...c, ...p } : c)));

  const addLog = (line: string) => setLog((l) => [...l, line]);

  async function finish() {
    setSubmitting(true);
    setSubmitError(null);
    setLog([]);
    try {
      addLog("Creating project…");
      const created = await api.createProject({
        name: project.name.trim(),
        primaryDomain: project.primaryDomain.trim(),
        defaultLanguage: project.defaultLanguage,
        refreshSchedule: {
          dayOfWeek: project.dayOfWeek,
          hourUtc: project.hourUtc,
        },
      });
      const projectId = created.id;
      addLog(`Project created: ${projectId}`);

      addLog("Saving business brief…");
      const briefBody: BusinessBrief = {
        businessModel: brief.businessModel,
        commercialObjective: brief.commercialObjective,
        currentCommercialPriority: brief.currentCommercialPriority,
        primaryOffer: brief.primaryOffer,
        offerMechanism: brief.offerMechanism,
        desiredCustomerAction: brief.desiredCustomerAction,
        mainConstraints: brief.mainConstraints,
        positioning: brief.positioning,
        approvedClaims: parseList(brief.approvedClaims),
        prohibitedClaims: parseList(brief.prohibitedClaims),
        availableProof: parseList(brief.availableProof),
        knownOperationalLimitations: parseList(
          brief.knownOperationalLimitations,
        ),
        markdownNotes: brief.markdownNotes,
      };
      await api.putBusinessBrief(projectId, briefBody);

      if (offer.name.trim()) {
        addLog("Creating primary offer…");
        const offerBody: OfferBody = {
          name: offer.name,
          mechanism: offer.mechanism,
          desiredAction: offer.desiredAction,
          approvedClaims: parseList(offer.approvedClaims),
          prohibitedClaims: parseList(offer.prohibitedClaims),
          proof: parseList(offer.proof),
          constraints: parseList(offer.constraints),
        };
        await api.createOffer(projectId, offerBody);
      }

      for (const [i, c] of cohorts.entries()) {
        if (!c.name.trim()) continue;
        addLog(`Creating cohort ${i + 1}: ${c.name}…`);
        const body: CohortBody = {
          name: c.name,
          roleIdentity: c.roleIdentity,
          commercialSituation: c.commercialSituation,
          trigger: c.trigger,
          activeProblem: c.activeProblem,
          currentWorkflow: c.currentWorkflow,
          currentBelief: c.currentBelief,
          desiredOutcome: c.desiredOutcome,
          objections: parseList(c.objections),
          decisionCriteria: parseList(c.decisionCriteria),
          priority: c.priority,
          offerFit: c.offerFit,
          exclusionCriteria: parseList(c.exclusionCriteria),
          exactLanguage: parseList(c.exactLanguage),
        };
        await api.createCohort(projectId, body);
      }

      for (const u of ownedUrls) {
        if (!u.url.trim()) continue;
        addLog(`Adding owned URL: ${u.url}…`);
        await api.createSource(projectId, {
          ownerType: "OWNED",
          competitorSlot: null,
          sourceType: "URL",
          name: u.name.trim() || u.url,
          url: u.url.trim(),
          refreshEnabled: true,
        });
      }
      for (const p of ownedPastes) {
        if (!p.content.trim()) continue;
        addLog(`Uploading owned ${p.format} content…`);
        await api.uploadSource(projectId, {
          ownerType: "OWNED",
          format: p.format,
          name: p.name.trim() || `owned.${p.format}`,
          content: p.content,
        });
      }
      for (const p of vocPastes) {
        if (!p.content.trim()) continue;
        addLog(`Uploading VoC ${p.format} content…`);
        await api.uploadSource(projectId, {
          ownerType: "VOC",
          format: p.format,
          name: p.name.trim() || `voc.${p.format}`,
          content: p.content,
        });
      }
      for (const [idx, slot] of competitors.entries()) {
        const competitorSlot = idx + 1;
        for (const u of slot.urls) {
          if (!u.url.trim()) continue;
          addLog(`Adding competitor ${competitorSlot} URL: ${u.url}…`);
          await api.createSource(projectId, {
            ownerType: "COMPETITOR",
            competitorSlot,
            sourceType: "URL",
            name: u.name.trim() || u.url,
            url: u.url.trim(),
            refreshEnabled: true,
          });
        }
        for (const p of slot.pastes) {
          if (!p.content.trim()) continue;
          addLog(`Uploading competitor ${competitorSlot} ${p.format}…`);
          await api.uploadSource(projectId, {
            ownerType: "COMPETITOR",
            competitorSlot,
            format: p.format,
            name: p.name.trim() || `competitor${competitorSlot}.${p.format}`,
            content: p.content,
          });
        }
      }

      addLog("Done. Analysis will run automatically on ingestion.");
      setActiveProjectId(projectId);
      navigate("/");
    } catch (e) {
      setSubmitError(
        e instanceof ApiError
          ? `${e.message} (status ${e.status})`
          : e instanceof Error
            ? e.message
            : "Setup failed.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const next = () => setStep((s) => Math.min(STEPS.length - 1, s + 1));
  const back = () => setStep((s) => Math.max(0, s - 1));

  return (
    <div>
      <h1>Set up your project</h1>
      <p className="subtitle">
        Configure the project, then add sources. Analysis runs automatically on
        ingestion — there is no manual &quot;Run Analysis&quot; button.
      </p>

      <div className="callout callout-warn">
        You must have the right to process any customer data (VoC) you upload.
      </div>

      <div className="wizard-steps">
        {STEPS.map((label, i) => (
          <button
            type="button"
            key={label}
            className={`wizard-step ${
              i === step ? "active" : i < step ? "done" : ""
            }`}
            onClick={() => setStep(i)}
          >
            {i + 1}. {label}
          </button>
        ))}
      </div>

      {/* Step 0: Project */}
      {step === 0 && (
        <Fieldset legend="Project">
          <TextField
            label="Project name"
            value={project.name}
            onChange={(v) => patchProject({ name: v })}
          />
          <TextField
            label="Primary domain"
            value={project.primaryDomain}
            placeholder="example.com"
            onChange={(v) => patchProject({ primaryDomain: v })}
          />
          <div className="grid-2">
            <div>
              <label>Default language</label>
              <select
                value={project.defaultLanguage}
                onChange={(e) =>
                  patchProject({
                    defaultLanguage: e.target.value as Language,
                  })
                }
              >
                <option value="en">en</option>
                <option value="ar">ar</option>
                <option value="mixed">mixed</option>
              </select>
            </div>
            <div />
            <TextField
              label="Refresh day of week (0=Sun … 6=Sat)"
              type="number"
              value={String(project.dayOfWeek)}
              onChange={(v) =>
                patchProject({
                  dayOfWeek: Math.max(0, Math.min(6, Number(v) || 0)),
                })
              }
            />
            <TextField
              label="Refresh hour (UTC, 0–23)"
              type="number"
              value={String(project.hourUtc)}
              onChange={(v) =>
                patchProject({
                  hourUtc: Math.max(0, Math.min(23, Number(v) || 0)),
                })
              }
            />
          </div>
        </Fieldset>
      )}

      {/* Step 1: Business Brief */}
      {step === 1 && (
        <Fieldset legend="Business brief">
          <TextField
            label="Business model"
            value={brief.businessModel}
            onChange={(v) => patchBrief({ businessModel: v })}
          />
          <TextField
            label="Commercial objective"
            value={brief.commercialObjective}
            onChange={(v) => patchBrief({ commercialObjective: v })}
          />
          <TextField
            label="Current commercial priority"
            value={brief.currentCommercialPriority}
            onChange={(v) => patchBrief({ currentCommercialPriority: v })}
          />
          <TextField
            label="Primary offer"
            value={brief.primaryOffer}
            onChange={(v) => patchBrief({ primaryOffer: v })}
          />
          <TextField
            label="Offer mechanism"
            value={brief.offerMechanism}
            onChange={(v) => patchBrief({ offerMechanism: v })}
          />
          <TextField
            label="Desired customer action"
            value={brief.desiredCustomerAction}
            onChange={(v) => patchBrief({ desiredCustomerAction: v })}
          />
          <TextField
            label="Main constraints"
            value={brief.mainConstraints}
            onChange={(v) => patchBrief({ mainConstraints: v })}
          />
          <TextField
            label="Positioning"
            value={brief.positioning}
            onChange={(v) => patchBrief({ positioning: v })}
          />
          <ListField
            label="Approved claims"
            value={brief.approvedClaims}
            onChange={(v) => patchBrief({ approvedClaims: v })}
          />
          <ListField
            label="Prohibited claims"
            value={brief.prohibitedClaims}
            onChange={(v) => patchBrief({ prohibitedClaims: v })}
          />
          <ListField
            label="Available proof"
            value={brief.availableProof}
            onChange={(v) => patchBrief({ availableProof: v })}
          />
          <ListField
            label="Known operational limitations"
            value={brief.knownOperationalLimitations}
            onChange={(v) => patchBrief({ knownOperationalLimitations: v })}
          />
          <TextAreaField
            label="Markdown notes"
            rows={5}
            value={brief.markdownNotes}
            onChange={(v) => patchBrief({ markdownNotes: v })}
          />
        </Fieldset>
      )}

      {/* Step 2: Primary Offer */}
      {step === 2 && (
        <Fieldset legend="Primary offer">
          <TextField
            label="Offer name"
            value={offer.name}
            onChange={(v) => patchOffer({ name: v })}
          />
          <TextField
            label="Mechanism"
            value={offer.mechanism}
            onChange={(v) => patchOffer({ mechanism: v })}
          />
          <TextField
            label="Desired action"
            value={offer.desiredAction}
            onChange={(v) => patchOffer({ desiredAction: v })}
          />
          <ListField
            label="Approved claims"
            value={offer.approvedClaims}
            onChange={(v) => patchOffer({ approvedClaims: v })}
          />
          <ListField
            label="Prohibited claims"
            value={offer.prohibitedClaims}
            onChange={(v) => patchOffer({ prohibitedClaims: v })}
          />
          <ListField
            label="Proof"
            value={offer.proof}
            onChange={(v) => patchOffer({ proof: v })}
          />
          <ListField
            label="Constraints"
            value={offer.constraints}
            onChange={(v) => patchOffer({ constraints: v })}
          />
        </Fieldset>
      )}

      {/* Step 3: Cohorts */}
      {step === 3 && (
        <div>
          <p className="field-hint">Add 1–2 cohorts.</p>
          {cohorts.map((c, i) => (
            <Fieldset legend={`Cohort ${i + 1}`} key={i}>
              <TextField
                label="Name"
                value={c.name}
                onChange={(v) => patchCohort(i, { name: v })}
              />
              <TextField
                label="Role / identity"
                value={c.roleIdentity}
                onChange={(v) => patchCohort(i, { roleIdentity: v })}
              />
              <TextField
                label="Commercial situation"
                value={c.commercialSituation}
                onChange={(v) => patchCohort(i, { commercialSituation: v })}
              />
              <TextField
                label="Trigger"
                value={c.trigger}
                onChange={(v) => patchCohort(i, { trigger: v })}
              />
              <TextField
                label="Active problem"
                value={c.activeProblem}
                onChange={(v) => patchCohort(i, { activeProblem: v })}
              />
              <TextField
                label="Current workflow"
                value={c.currentWorkflow}
                onChange={(v) => patchCohort(i, { currentWorkflow: v })}
              />
              <TextField
                label="Current belief"
                value={c.currentBelief}
                onChange={(v) => patchCohort(i, { currentBelief: v })}
              />
              <TextField
                label="Desired outcome"
                value={c.desiredOutcome}
                onChange={(v) => patchCohort(i, { desiredOutcome: v })}
              />
              <ListField
                label="Objections"
                value={c.objections}
                onChange={(v) => patchCohort(i, { objections: v })}
              />
              <ListField
                label="Decision criteria"
                value={c.decisionCriteria}
                onChange={(v) => patchCohort(i, { decisionCriteria: v })}
              />
              <TextField
                label="Priority (1–5)"
                type="number"
                value={String(c.priority)}
                onChange={(v) =>
                  patchCohort(i, {
                    priority: Math.max(1, Math.min(5, Number(v) || 1)),
                  })
                }
              />
              <TextField
                label="Offer fit"
                value={c.offerFit}
                onChange={(v) => patchCohort(i, { offerFit: v })}
              />
              <ListField
                label="Exclusion criteria"
                value={c.exclusionCriteria}
                onChange={(v) => patchCohort(i, { exclusionCriteria: v })}
              />
              <ListField
                label="Exact language (verbatim phrases)"
                value={c.exactLanguage}
                onChange={(v) => patchCohort(i, { exactLanguage: v })}
              />
              {cohorts.length > 1 && (
                <button
                  type="button"
                  className="secondary small"
                  style={{ marginTop: 10 }}
                  onClick={() =>
                    setCohorts((list) => list.filter((_, j) => j !== i))
                  }
                >
                  Remove cohort
                </button>
              )}
            </Fieldset>
          ))}
          {cohorts.length < 2 && (
            <button
              type="button"
              className="secondary"
              onClick={() => setCohorts((list) => [...list, emptyCohort()])}
            >
              + Add second cohort
            </button>
          )}
        </div>
      )}

      {/* Step 4: Owned Content */}
      {step === 4 && (
        <div>
          <Fieldset legend="Owned content — URL sources">
            <UrlEditor entries={ownedUrls} onChange={setOwnedUrls} />
          </Fieldset>
          <Fieldset legend="Owned content — paste / upload">
            <PasteEditor entries={ownedPastes} onChange={setOwnedPastes} />
          </Fieldset>
        </div>
      )}

      {/* Step 5: Voice of Customer */}
      {step === 5 && (
        <Fieldset legend="Voice of Customer (VoC)">
          <div className="callout callout-warn">
            You must have the right to process any customer data you upload.
          </div>
          <p className="field-hint">
            Paste CSV, JSON, or TXT of customer language (reviews, tickets,
            interview notes).
          </p>
          <PasteEditor entries={vocPastes} onChange={setVocPastes} />
        </Fieldset>
      )}

      {/* Step 6: Competitors */}
      {step === 6 && (
        <div>
          <p className="field-hint">Exactly 3 competitor slots.</p>
          {competitors.map((slot, i) => (
            <Fieldset legend={`Competitor slot ${i + 1}`} key={i}>
              <h4 style={{ margin: "4px 0" }}>URL sources</h4>
              <UrlEditor
                entries={slot.urls}
                onChange={(urls) => patchCompetitor(i, { urls })}
              />
              <h4 style={{ margin: "12px 0 4px" }}>Paste / upload</h4>
              <PasteEditor
                entries={slot.pastes}
                onChange={(pastes) => patchCompetitor(i, { pastes })}
              />
            </Fieldset>
          ))}
        </div>
      )}

      {/* Step 7: Review */}
      {step === 7 && (
        <Fieldset legend="Review & create">
          <p>
            Project <strong>{project.name || "(unnamed)"}</strong> ·{" "}
            {cohorts.filter((c) => c.name.trim()).length} cohort(s) ·{" "}
            {ownedUrls.length + ownedPastes.length} owned source(s) ·{" "}
            {vocPastes.length} VoC upload(s) ·{" "}
            {competitors.reduce(
              (n, s) => n + s.urls.length + s.pastes.length,
              0,
            )}{" "}
            competitor source(s)
          </p>
          <div className="callout callout-info">
            After creation the project id is stored locally and analysis runs
            automatically on ingestion.
          </div>
          {submitError && <div className="callout callout-danger">{submitError}</div>}
          {log.length > 0 && (
            <pre className="log">{log.join("\n")}</pre>
          )}
          <div className="btn-row">
            <button
              type="button"
              onClick={() => void finish()}
              disabled={submitting || !project.name.trim()}
            >
              {submitting ? "Creating…" : "Finish & create project"}
            </button>
          </div>
        </Fieldset>
      )}

      <div className="btn-row">
        <button
          type="button"
          className="secondary"
          onClick={back}
          disabled={step === 0}
        >
          ← Back
        </button>
        {step < STEPS.length - 1 && (
          <button type="button" onClick={next}>
            Next →
          </button>
        )}
      </div>

      <hr style={{ margin: "32px 0", borderColor: "var(--border)" }} />
      <ConnectPanel />
    </div>
  );
}
