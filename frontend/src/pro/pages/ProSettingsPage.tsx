import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  deleteSession,
  getStatus,
  resetSession,
  updateSettings,
  type StatusResponse,
} from "../../api/client";
import styles from "./ProSettingsPage.module.css";

const MODEL_OPTIONS = [
  { value: "rf", label: "Random Forest" },
  { value: "gbm", label: "Gradient Boosting" },
  { value: "lr", label: "Logistic Regression" },
  { value: "svm", label: "SVM" },
];

const CALIBRATION_OPTIONS = [
  { value: "sigmoid", label: "Sigmoid" },
  { value: "isotonic", label: "Isotonic" },
];

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: StatusResponse };

export default function ProSettingsPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const [patience, setPatience] = useState("3");
  const [minDelta, setMinDelta] = useState("0.005");
  const [costPerSample, setCostPerSample] = useState("");
  const [diversityWeight, setDiversityWeight] = useState("0");
  const [model, setModel] = useState("rf");
  const [calibrate, setCalibrate] = useState(false);
  const [calibrationMethod, setCalibrationMethod] = useState("sigmoid");

  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [dangerBusy, setDangerBusy] = useState(false);
  const [dangerError, setDangerError] = useState<string | null>(null);

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    getStatus(name)
      .then((data) => {
        if (cancelled) return;
        setState({ status: "loaded", data });
        setPatience(String(data.patience));
        setMinDelta(String(data.min_delta));
        setCostPerSample(data.cost_per_sample !== null ? String(data.cost_per_sample) : "");
        setDiversityWeight(String(data.diversity_weight));
        setModel(data.model);
        setCalibrate(data.calibrate);
        setCalibrationMethod(data.calibration_method);
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    if (!name) return;
    setSaveError(null);
    setSaveMessage(null);
    setSaving(true);
    try {
      const updated = await updateSettings(name, {
        patience: Number(patience),
        minDelta: Number(minDelta),
        costPerSample: costPerSample === "" ? undefined : Number(costPerSample),
        diversityWeight: Number(diversityWeight),
        model,
        calibrate,
        calibrationMethod,
      });
      setState({ status: "loaded", data: updated });
      setSaveMessage("Settings saved.");
    } catch (err) {
      setSaveError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    if (!name) return;
    if (!window.confirm(`Reset ${name}? This clears all round history but keeps known/pool samples.`)) {
      return;
    }
    setDangerError(null);
    setDangerBusy(true);
    try {
      await resetSession(name);
      const refreshed = await getStatus(name);
      setState({ status: "loaded", data: refreshed });
    } catch (err) {
      setDangerError((err as Error).message);
    } finally {
      setDangerBusy(false);
    }
  }

  async function handleDelete() {
    if (!name) return;
    if (!window.confirm(`Delete ${name}? This permanently removes the session and its data.`)) {
      return;
    }
    setDangerError(null);
    setDangerBusy(true);
    try {
      await deleteSession(name);
      navigate("/pro");
    } catch (err) {
      setDangerError((err as Error).message);
      setDangerBusy(false);
    }
  }

  if (state.status === "loading") return <p className={styles.loading}>Loading…</p>;
  if (state.status === "error") return <p className={styles.error}>{state.message}</p>;

  return (
    <div>
      <h2 className={styles.title}>Settings</h2>
      <form onSubmit={handleSave} className={styles.form}>
        <div className={styles.field}>
          <label htmlFor="patience">Patience (rounds)</label>
          <input id="patience" type="number" min="1" value={patience} onChange={(e) => setPatience(e.target.value)} />
        </div>
        <div className={styles.field}>
          <label htmlFor="minDelta">Min delta</label>
          <input id="minDelta" type="number" step="0.001" min="0" value={minDelta} onChange={(e) => setMinDelta(e.target.value)} />
        </div>
        <div className={styles.field}>
          <label htmlFor="costPerSample">Cost per sample (blank = not tracked)</label>
          <input id="costPerSample" type="number" step="0.01" min="0" value={costPerSample} onChange={(e) => setCostPerSample(e.target.value)} />
        </div>
        <div className={styles.field}>
          <label htmlFor="diversityWeight">Diversity weight</label>
          <input id="diversityWeight" type="number" step="0.05" min="0" max="1" value={diversityWeight} onChange={(e) => setDiversityWeight(e.target.value)} />
        </div>
        <div className={styles.field}>
          <label htmlFor="model">Model</label>
          <select id="model" value={model} onChange={(e) => setModel(e.target.value)}>
            {MODEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div className={styles.checkboxField}>
          <label htmlFor="calibrate">
            <input id="calibrate" type="checkbox" checked={calibrate} onChange={(e) => setCalibrate(e.target.checked)} />
            {" "}Calibrate predictions
          </label>
        </div>
        {calibrate && (
          <div className={styles.field}>
            <label htmlFor="calibrationMethod">Calibration method</label>
            <select id="calibrationMethod" value={calibrationMethod} onChange={(e) => setCalibrationMethod(e.target.value)}>
              {CALIBRATION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        )}

        <button type="submit" className={styles.submit} disabled={saving}>
          {saving ? "Saving…" : "Save changes"}
        </button>
        {saveMessage && <p className={styles.saveMessage}>{saveMessage}</p>}
        {saveError && <p className={styles.error}>{saveError}</p>}
      </form>

      <div className={styles.dangerZone}>
        <h3>Danger zone</h3>
        <button type="button" onClick={handleReset} disabled={dangerBusy} className={styles.dangerButton}>
          Reset session
        </button>
        <button type="button" onClick={handleDelete} disabled={dangerBusy} className={styles.dangerButton}>
          Delete session
        </button>
        {dangerError && <p className={styles.error}>{dangerError}</p>}
      </div>
    </div>
  );
}
