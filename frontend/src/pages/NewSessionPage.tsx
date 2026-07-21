import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { createSession } from "../api/client";
import styles from "./NewSessionPage.module.css";

export default function NewSessionPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [labelCol, setLabelCol] = useState("");
  const [labeledFile, setLabeledFile] = useState<File | null>(null);
  const [poolFile, setPoolFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitError(null);

    if (!name.trim()) {
      setValidationError("Session name is required.");
      return;
    }
    if (!labelCol.trim()) {
      setValidationError("Label column is required.");
      return;
    }
    if (!labeledFile) {
      setValidationError("A labeled data file is required.");
      return;
    }
    setValidationError(null);

    setSubmitting(true);
    try {
      await createSession({
        name: name.trim(),
        labelCol: labelCol.trim(),
        labeledFile,
        poolFile: poolFile ?? undefined,
      });
      navigate("/");
    } catch (err) {
      setSubmitError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.container}>
      <h1>New session</h1>
      <form onSubmit={handleSubmit}>
        <div className={styles.field}>
          <label htmlFor="name">Session name</label>
          <input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="labelCol">Label column</label>
          <input
            id="labelCol"
            type="text"
            value={labelCol}
            onChange={(e) => setLabelCol(e.target.value)}
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="labeledFile">Labeled data file</label>
          <input
            id="labeledFile"
            type="file"
            onChange={(e) => setLabeledFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="poolFile">Unlabeled pool file (optional)</label>
          <input
            id="poolFile"
            type="file"
            onChange={(e) => setPoolFile(e.target.files?.[0] ?? null)}
          />
        </div>

        {validationError && <p className={styles.validationError}>{validationError}</p>}

        <button type="submit" className={styles.submit} disabled={submitting}>
          {submitting ? "Creating…" : "Create session"}
        </button>

        {submitError && <p className={styles.submitError}>{submitError}</p>}
      </form>
    </div>
  );
}
