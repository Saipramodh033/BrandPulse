"use client";

import { useEffect, useState, use } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { API_URL } from "@/lib/api";
import { useRouter } from "next/navigation";
import styles from "./settings.module.css";
import { Loader2 } from "lucide-react";

export default function CompanySettings({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [confirmPause, setConfirmPause] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [frequencyHours, setFrequencyHours] = useState(24);
  const [status, setStatus] = useState<"active" | "paused">("active");

  useEffect(() => {
    fetch(`${API_URL}/companies/${id}`)
      .then((r) => r.json())
      .then((data) => {
        setName(data.name || "");
        setDescription(data.description || "");
        setFrequencyHours(data.frequency_hours || 24);
        setStatus(data.status || "active");
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  const handleSave = async () => {
    if (saving) return;
    setSaving(true);
    setSaveMsg(null);
    setErrorMsg(null);
    try {
      const res = await fetch(`${API_URL}/companies/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, description, frequency_hours: frequencyHours, status }),
      });
      if (!res.ok) throw new Error(`Server ${res.status}`);
      setSaveMsg("Changes saved successfully.");
      setTimeout(() => setSaveMsg(null), 4000);
      queryClient.invalidateQueries({ queryKey: ["company", String(id)] });
      queryClient.invalidateQueries({ queryKey: ["companies"] });
    } catch (err: any) {
      setErrorMsg(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (deleting) return;
    setDeleting(true);
    try {
      const res = await fetch(`${API_URL}/companies/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`Server ${res.status}`);
      setDeleteConfirmText("");
      queryClient.invalidateQueries({ queryKey: ["companies"] });
      router.push("/");
    } catch (err: any) {
      setErrorMsg(`Delete failed: ${err.message}`);
      setDeleting(false);
    }
  };

  const handleToggleStatus = async () => {
    const newStatus = status === "active" ? "paused" : "active";
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/companies/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!res.ok) throw new Error(`Server ${res.status}`);
      setStatus(newStatus);
      queryClient.invalidateQueries({ queryKey: ["company", String(id)] });
      queryClient.invalidateQueries({ queryKey: ["companies"] });
    } catch (err: any) {
      setErrorMsg(`Failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className={styles.loading}>Loading settings...</div>;

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Company Settings</h2>

      {saveMsg && <div className={styles.successBanner}>{saveMsg}</div>}
      {errorMsg && <div className={styles.errorBanner}>{errorMsg}</div>}

      {/* General */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>General</h3>
        <div className={styles.field}>
          <label className={styles.label}>Company Name</label>
          <input
            className={styles.input}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Company name"
          />
        </div>
        <div className={styles.field}>
          <label className={styles.label}>Description / Focus</label>
          <textarea
            className={styles.textarea}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the company and target audience..."
            rows={4}
          />
        </div>
        <div className={styles.field}>
          <label className={styles.label}>Ideation Frequency</label>
          <select
            className={styles.input}
            value={[6, 12, 24, 48].includes(frequencyHours) ? frequencyHours : "custom"}
            onChange={(e) => {
              if (e.target.value !== "custom") {
                setFrequencyHours(Number(e.target.value));
              }
            }}
          >
            <option value={6}>Every 6 hours (0.25d)</option>
            <option value={12}>Every 12 hours (0.5d)</option>
            <option value={24}>Every 24 hours (1d)</option>
            <option value={48}>Every 48 hours (2d)</option>
            <option value="custom">Custom...</option>
          </select>
          {![6, 12, 24, 48].includes(frequencyHours) && (
            <input
              className={styles.input}
              type="number"
              min={1}
              max={168}
              value={frequencyHours}
              onChange={(e) => setFrequencyHours(Number(e.target.value))}
              style={{ marginTop: "8px" }}
              placeholder="Enter custom hours"
            />
          )}
          {frequencyHours < 4 && (
            <span style={{ color: "#f59e0b", fontSize: "0.8rem", display: "block", marginTop: "4px" }}>
              ⚠️ Very frequent generation may exhaust AI model rate limits. Recommended: 24h or more.
            </span>
          )}
        </div>
        <button className="btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </section>

      {/* Run Schedule */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Auto-Generation Schedule</h3>
        <div className={styles.statusRow}>
          <div>
            <div className={styles.statusName}>
              Schedule:{" "}
              <span className={status === "active" ? styles.statusActive : styles.statusPaused}>
                {status === "active" ? "Active" : "Paused"}
              </span>
            </div>
            <div className={styles.statusDesc}>
              {status === "active"
                ? "The AI engine will automatically generate ideas on the schedule above."
                : "Automated generation is paused. Head to the Inbox to trigger a manual run."}
            </div>
          </div>
          {!confirmPause ? (
            <button className="btn-secondary" onClick={() => status === "active" ? setConfirmPause(true) : handleToggleStatus()} disabled={saving}>
              {status === "active" ? "Pause Schedule" : "Resume Schedule"}
            </button>
          ) : (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Are you sure?</span>
              <button className="btn-secondary" onClick={() => setConfirmPause(false)}>Cancel</button>
              <button className="btn-primary" onClick={() => { setConfirmPause(false); handleToggleStatus(); }} disabled={saving}>
                Yes, Pause
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Danger Zone */}
      <section className={`${styles.section} ${styles.dangerSection}`}>
        <h3 className={styles.sectionTitle} style={{ color: "#ef4444" }}>Danger Zone</h3>
        {!confirmDelete ? (
          <div className={styles.dangerRow}>
            <div>
              <div className={styles.dangerTitle}>Delete Company</div>
              <div className={styles.dangerDesc}>This permanently removes the company and all its ideas, runs, and strategy memory. This cannot be undone.</div>
            </div>
            <button className={styles.btnDanger} onClick={() => setConfirmDelete(true)}>
              Delete Company
            </button>
          </div>
        ) : (
          <div className={styles.confirmBox}>
            <p>Type <strong>delete</strong> to confirm permanent deletion:</p>
            <input
              type="text"
              className={styles.input}
              placeholder="type delete"
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              style={{ marginBottom: "12px" }}
            />
            <div className={styles.confirmActions}>
              <button className="btn-secondary" onClick={() => { setConfirmDelete(false); setDeleteConfirmText(""); }}>Cancel</button>
              <button
                className={styles.btnDanger}
                onClick={handleDelete}
                disabled={deleting || deleteConfirmText !== "delete"}
              >
                {deleting ? "Deleting..." : "Yes, Delete"}
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
