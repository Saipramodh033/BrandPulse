"use client";

import { useState } from "react";
import { Plus, X, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { API_URL } from "@/lib/api";

export default function AddCompanyModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    description: "",
    frequency_hours: 24,
  });

  // Resets validation errors and form state upon modal dismissal
  const closeModal = () => {
    setIsOpen(false);
    setError(null);
    setFormData({ name: "", email: "", description: "", frequency_hours: 24 });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/companies/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to add company");
      }

      const newCompany = await res.json();
      closeModal();
      queryClient.invalidateQueries({ queryKey: ["companies"] });
      router.push(`/companies/${newCompany.id}/inbox`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <button className="btn-primary" onClick={() => setIsOpen(true)}>
        <Plus size={16} style={{ display: "inline", marginRight: "8px", verticalAlign: "middle" }} />
        Add Company
      </button>

      {isOpen && (
        <div style={overlayStyle} onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}>
          <div style={modalStyle} className="glass-panel">
            <div style={headerStyle}>
              <h3>Add New Company</h3>
              {/* U7 Fix: use closeModal() which resets error */}
              <button onClick={closeModal} style={closeBtnStyle}>
                <X size={20} />
              </button>
            </div>

            {error && <div style={errorStyle}>{error}</div>}

            <form onSubmit={handleSubmit} style={formStyle}>
              <div className="form-group">
                <label>Company Name *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Acme Corp"
                  style={inputStyle}
                />
              </div>

              <div className="form-group">
                <label>Contact Email *</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="e.g. team@acmecorp.com"
                  style={inputStyle}
                />
              </div>

              <div className="form-group">
                <label>Description / Focus Area</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="What does the company do? Who is the target audience? The more detail, the better the AI output."
                  rows={3}
                  style={textareaStyle}
                />
              </div>

              <div className="form-group">
                <label>Run Frequency (Hours)</label>
                <input
                  type="number"
                  min={1}
                  value={formData.frequency_hours}
                  onChange={(e) => setFormData({ ...formData, frequency_hours: parseInt(e.target.value) || 24 })}
                  style={inputStyle}
                />
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Every {formData.frequency_hours}h · Recommended: 24h
                </div>
              </div>

              <div style={footerStyle}>
                <button type="button" onClick={closeModal} style={cancelBtnStyle}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={isSubmitting} style={submitBtnStyle}>
                  {isSubmitting ? <Loader2 size={16} className="animate-spin" /> : "Add Company"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  top: 0, left: 0, right: 0, bottom: 0,
  backgroundColor: "rgba(0, 0, 0, 0.7)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
  backdropFilter: "blur(4px)",
};

const modalStyle: React.CSSProperties = {
  width: "100%",
  maxWidth: "500px",
  padding: "24px",
  borderRadius: "12px",
  display: "flex",
  flexDirection: "column",
  gap: "20px",
  backgroundColor: "var(--bg-secondary)",
  border: "1px solid var(--border-light)",
  boxShadow: "0 20px 25px -5px rgba(0,0,0,0.5), 0 10px 10px -5px rgba(0,0,0,0.2)",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const closeBtnStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "var(--text-secondary)",
  cursor: "pointer",
  padding: "4px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const errorStyle: React.CSSProperties = {
  backgroundColor: "rgba(239, 68, 68, 0.1)",
  color: "#ef4444",
  padding: "12px",
  borderRadius: "6px",
  fontSize: "0.9rem",
  border: "1px solid rgba(239, 68, 68, 0.2)",
};

const formStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "16px",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  borderRadius: "6px",
  border: "1px solid var(--border-light)",
  backgroundColor: "rgba(0, 0, 0, 0.2)",
  color: "var(--text-primary)",
  marginTop: "6px",
};

const textareaStyle: React.CSSProperties = {
  ...inputStyle,
  resize: "vertical",
};

const footerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "flex-end",
  gap: "12px",
  marginTop: "8px",
};

const cancelBtnStyle: React.CSSProperties = {
  background: "transparent",
  border: "1px solid var(--border-light)",
  color: "var(--text-secondary)",
  padding: "8px 16px",
  borderRadius: "6px",
  cursor: "pointer",
};

const submitBtnStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
};
