"use client";

import { useEffect, useState, use } from "react";
import { API_URL } from "@/lib/api";
import { useRouter } from "next/navigation";
import styles from "./settings.module.css";
import { Play, Loader2 } from "lucide-react";

export default function CompanySettings({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();

  const [company, setCompany] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  // B6 Fix: run trigger state
  const [triggerLoading, setTriggerLoading] = useState(false);
  const [triggerMsg, setTriggerMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [frequencyHours, setFrequencyHours] = useState(24);
  const [status, setStatus] = useState<"active" | "paused">("active");

  useEffect(() => {
    fetch(`${API_URL}/companies/${id}`)
      .then(r => r.json())
      .then(data => {
        setCompany(data);
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
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, frequency_hours: frequencyHours, status })
      });
      if (!res.ok) throw new Error(`Server ${res.status}`);
      setSaveMsg("Changes saved successfully.");
    } catch (err: any) {
      setErrorMsg(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  // B6 Fix: manual run trigger handler
  const handleTriggerRun = async () => {
    if (triggerLoading) return;
    setTriggerLoading(true);
    setTriggerMsg(null);
    try {
      const res = await fetch(`${API_URL}/companies/${id}/run`, { method: 'POST' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        if (res.status === 409) {
          setTriggerMsg({
            text: body.detail || 'Clear the inbox (approve/reject pending ideas) before triggering a new run.',
            type: 'error'
          });
        } else {
          setTriggerMsg({ text: `Failed: ${res.status}`, type: 'error' });
        }
        return;
      }
      setTriggerMsg({
        text: '✓ Run queued — the AI pipeline will start within 60 seconds. Check the Inbox for results.',
        type: 'success'
      });
    } finally {
      setTriggerLoading(false);
    }
  };

  const handleDelete = async () => {
    if (deleting) return;
    setDeleting(true);
    try {
      const res = await fetch(`${API_URL}/companies/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`Server ${res.status}`);
      setDeleteConfirmText("");
      router.push('/');
    } catch (err: any) {
      setErrorMsg(`Delete failed: ${err.message}`);
      setDeleting(false);
    }
  };

  const handleToggleStatus = async () => {
    const newStatus = status === 'active' ? 'paused' : 'active';
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/companies/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      if (!res.ok) throw new Error(`Server ${res.status}`);
      setStatus(newStatus);
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
          <label className={styles.label}>Ideation Frequency (hours)</label>
          <input
            className={styles.input}
            type="number"
            min={1}
            max={168}
            value={frequencyHours}
            onChange={(e) => setFrequencyHours(Number(e.target.value))}
          />
          <span className={styles.hint}>Runs every {frequencyHours}h ({(frequencyHours / 24).toFixed(1)}d)</span>
          {frequencyHours < 4 && (
            <span style={{ color: '#f59e0b', fontSize: '0.8rem', display: 'block', marginTop: '4px' }}>
              ⚠️ At this rate you may hit Gemini free-tier rate limits. Recommended: 24h.
            </span>
          )}
        </div>
        <button className="btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </section>

      {/* Run Schedule */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Run Schedule</h3>
        <div className={styles.statusRow}>
          <div>
            <div className={styles.statusName}>
              Schedule: <span className={status === 'active' ? styles.statusActive : styles.statusPaused}>{status}</span>
            </div>
            <div className={styles.statusDesc}>
              {status === 'active'
                ? 'The engine will automatically run ideation on schedule.'
                : 'Automated runs are paused. You can still trigger runs manually below.'}
            </div>
          </div>
          <button className="btn-secondary" onClick={handleToggleStatus} disabled={saving}>
            {status === 'active' ? 'Pause Schedule' : 'Resume Schedule'}
          </button>
        </div>
      </section>

      {/* B6 Fix: Manual Run Trigger */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Manual Run</h3>
        <div className={styles.statusRow}>
          <div>
            <div className={styles.statusName}>Trigger Ideation Now</div>
            <div className={styles.statusDesc}>
              Run the AI pipeline immediately, regardless of the schedule.
              Requires the inbox to be empty (no pending ideas).
            </div>
          </div>
          <button
            className="btn-primary"
            onClick={handleTriggerRun}
            disabled={triggerLoading}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', whiteSpace: 'nowrap' }}
          >
            {triggerLoading
              ? <><Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> Queuing…</>
              : <><Play size={15} /> Trigger Now</>
            }
          </button>
        </div>
        {triggerMsg && (
          <div style={{
            marginTop: '10px',
            padding: '10px 14px',
            borderRadius: '6px',
            fontSize: '0.85rem',
            background: triggerMsg.type === 'success' ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
            border: `1px solid ${triggerMsg.type === 'success' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`,
            color: triggerMsg.type === 'success' ? 'var(--status-success)' : '#ef4444',
          }}>
            {triggerMsg.text}
          </div>
        )}
      </section>

      {/* Danger Zone */}
      <section className={`${styles.section} ${styles.dangerSection}`}>
        <h3 className={styles.sectionTitle} style={{ color: '#ef4444' }}>Danger Zone</h3>
        {!confirmDelete ? (
          <div className={styles.dangerRow}>
            <div>
              <div className={styles.dangerTitle}>Delete Company</div>
              <div className={styles.dangerDesc}>This permanently removes the company and all its ideas, runs, and angle memory. This cannot be undone.</div>
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
              style={{ marginBottom: '12px' }}
            />
            <div className={styles.confirmActions}>
              <button className="btn-secondary" onClick={() => { setConfirmDelete(false); setDeleteConfirmText(""); }}>Cancel</button>
              <button
                className={styles.btnDanger}
                onClick={handleDelete}
                disabled={deleting || deleteConfirmText !== 'delete'}
              >
                {deleting ? 'Deleting...' : 'Yes, Delete'}
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
