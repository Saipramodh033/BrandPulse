"use client";

import { useEffect, useState, useRef, use } from "react";
import { API_URL } from "@/lib/api";
import styles from "./inbox.module.css";
import { Check, X, RefreshCw, ChevronDown, ChevronUp, Zap, Leaf, Play, Loader2, Radio } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

type IdeaStatus = "pending" | "approved" | "rejected" | "refining";

interface Idea {
  id: number;
  hook: string;
  body: string;
  cta: string;
  platform: string;
  implication_type: string;
  angle_category: string;
  angle_detail: string;
  is_wildcard: boolean;
  signal_used: string;
  status: string;
  admin_feedback: string | null;
  created_at: string;
  run_log_id: number | null;
  evergreen: boolean;
}

interface TraceNode {
  node: string;
  status: string;
  timestamp: string;
}

interface RunLog {
  id: number;
  status: string;
  nodes: TraceNode[];
  search_query: string;
  search_results: string[];
  signal: any;
  signal_strength: string;
  chosen_angle: any;
  evergreen: boolean;
  ideas_generated: number;
  ideas_approved: number;
  created_at: string;
}

const TAB_ORDER: IdeaStatus[] = ["pending", "approved", "rejected", "refining"];

const NODE_LABELS: Record<string, string> = {
  recall_company_memory: "Recalling past angles",
  profile_company: "Profiling company",
  search_web: "Searching market news",
  extract_signal: "Extracting signal",
  generate_ideas: "Generating ideas",
  validate_and_critique_ideas: "Validating ideas",
  finish: "Finalizing ideas",
};

// Maps node name → a human-readable "current phase" status string
const NODE_PHASE: Record<string, string> = {
  recall_company_memory: "Recalling past angles…",
  profile_company: "Profiling company…",
  search_web: "Searching market news…",
  extract_signal: "Extracting signal…",
  generate_ideas: "Generating ideas…",
  validate_and_critique_ideas: "Validating ideas…",
  finish: "Finalizing ideas…",
};

interface Toast {
  message: string;
  type: "success" | "error" | "info";
}

export default function IdeaInbox({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const companyId = Number(id);

  const [allIdeas, setAllIdeas] = useState<Idea[]>([]);
  const [activeTab, setActiveTab] = useState<IdeaStatus>("pending");
  const [focusIndex, setFocusIndex] = useState(0);

  // Trace / runs state
  const [runs, setRuns] = useState<RunLog[]>([]);
  const [liveTrace, setLiveTrace] = useState<TraceNode[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);

  // "queued" state: set to true immediately when user clicks trigger, cleared when first node arrives
  const [isQueued, setIsQueued] = useState(false);
  // True while the agent is actively running (liveTrace has items but run hasn't finished yet)
  const [isAgentRunning, setIsAgentRunning] = useState(false);

  // Actions state
  const [refiningId, setRefiningId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [triggerLoading, setTriggerLoading] = useState(false);

  const [toast, setToast] = useState<Toast | null>(null);
  const toastTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const traceEndRef = useRef<HTMLDivElement>(null);

  const showToast = (message: string, type: Toast["type"] = "success") => {
    if (toastTimeout.current) clearTimeout(toastTimeout.current);
    setToast({ message, type });
    toastTimeout.current = setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    fetchIdeas();
    fetchRuns();

    const apiBase = API_URL.replace(/^http/, 'ws');
    const wsUrl = `${apiBase}/ws/trace/${id}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => {
      setWsConnected(false);
      setIsAgentRunning(false);
    };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // First message arriving: clear "queued" state, set "running"
      setIsQueued(false);
      setIsAgentRunning(true);
      setLiveTrace(prev => [...prev, data]);
      // When validation completes, the run is done — fetch fresh data
      if (data.node === "finish" || data.status === "error") {
        setTimeout(() => {
          fetchIdeas();
          fetchRuns();
          setIsAgentRunning(false);
        }, 1500);
      }
    };

    return () => ws.close();
  }, [id]);

  useEffect(() => {
    traceEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [liveTrace]);

  const fetchIdeas = () => {
    fetch(`${API_URL}/companies/${companyId}/ideas?limit=100`)
      .then(r => r.json())
      .then((data) => { if (Array.isArray(data)) setAllIdeas(data); })
      .catch(console.error);
  };

  const fetchRuns = () => {
    fetch(`${API_URL}/companies/${companyId}/runs?limit=10`)
      .then(r => r.json())
      .then((data) => { if (Array.isArray(data)) setRuns(data); })
      .catch(console.error);
  };

  const filteredIdeas = allIdeas.filter(i => i.status === activeTab);
  const focusedIdea = filteredIdeas[focusIndex] ?? null;

  const tabCounts: Record<IdeaStatus, number> = {
    pending: allIdeas.filter(i => i.status === 'pending').length,
    approved: allIdeas.filter(i => i.status === 'approved').length,
    rejected: allIdeas.filter(i => i.status === 'rejected').length,
    refining: allIdeas.filter(i => i.status === 'refining').length,
  };

  useEffect(() => { setFocusIndex(0); }, [activeTab]);

  useEffect(() => {
    if (filteredIdeas.length > 0 && focusIndex >= filteredIdeas.length) {
      setFocusIndex(filteredIdeas.length - 1);
    }
  }, [filteredIdeas.length, focusIndex]);

  const handleAction = async (ideaId: number, action: 'approve' | 'reject') => {
    if (isProcessing) return;
    setIsProcessing(true);

    const previousIdeas = [...allIdeas];
    setAllIdeas(prev => prev.map(i => i.id === ideaId
      ? { ...i, status: action === 'approve' ? 'approved' : 'rejected' }
      : i));

    try {
      const res = await fetch(`${API_URL}/ideas/${ideaId}/${action}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: action === 'reject' ? JSON.stringify({ feedback: "" }) : undefined
      });
      if (!res.ok) throw new Error(`Server ${res.status}`);
      showToast(action === 'approve' ? '✓ Idea approved' : '✓ Idea rejected');
    } catch (err: any) {
      setAllIdeas(previousIdeas);
      showToast(`Failed: ${err.message}`, "error");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRefine = async (ideaId: number) => {
    if (isProcessing || !feedback.trim()) return;
    setIsProcessing(true);

    const previousIdeas = [...allIdeas];
    setAllIdeas(prev => prev.map(i => i.id === ideaId ? { ...i, status: 'refining' } : i));
    setRefiningId(null);
    setFeedback("");

    try {
      const res = await fetch(`${API_URL}/ideas/${ideaId}/refine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback })
      });
      if (!res.ok) throw new Error(`Server ${res.status}`);
      showToast('↻ Refinement queued — idea will return to Pending when ready', 'info');
    } catch (err: any) {
      setAllIdeas(previousIdeas);
      showToast(`Refinement failed: ${err.message}`, "error");
    } finally {
      setIsProcessing(false);
    }
  };

  const triggerRun = async () => {
    if (triggerLoading) return;
    setTriggerLoading(true);
    setLiveTrace([]);
    setIsAgentRunning(false);

    try {
      const res = await fetch(`${API_URL}/companies/${companyId}/run`, { method: 'POST' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        if (res.status === 409) {
          showToast(body.detail || 'Clear your inbox before triggering a new run.', 'error');
        } else {
          showToast(`Failed to trigger run: ${res.status}`, 'error');
        }
        return;
      }
      // Show "queued" immediately — the Celery beat picks it up within 60s
      setIsQueued(true);
      showToast('✓ Run queued — the AI pipeline will start within 60 seconds', 'success');
    } finally {
      setTriggerLoading(false);
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (document.activeElement?.tagName === 'TEXTAREA' || document.activeElement?.tagName === 'INPUT') return;
      if (!focusedIdea || refiningId !== null || isProcessing || e.repeat) return;
      if (activeTab !== 'pending') return;

      if (e.key.toLowerCase() === 'a') { e.preventDefault(); handleAction(focusedIdea.id, 'approve'); }
      else if (e.key.toLowerCase() === 'r') { e.preventDefault(); handleAction(focusedIdea.id, 'reject'); }
      else if (e.key.toLowerCase() === 'f') { e.preventDefault(); setRefiningId(focusedIdea.id); }
      else if (e.key === 'ArrowDown') { e.preventDefault(); setFocusIndex(prev => Math.min(prev + 1, filteredIdeas.length - 1)); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setFocusIndex(prev => Math.max(prev - 1, 0)); }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [focusedIdea, refiningId, isProcessing, activeTab, filteredIdeas]);

  const selectedRun = selectedRunId ? runs.find(r => r.id === selectedRunId) : runs[0];

  // The current phase label shown during live run
  const currentPhase = liveTrace.length > 0
    ? NODE_PHASE[liveTrace[liveTrace.length - 1].node] ?? "Processing…"
    : null;

  return (
    <div className={styles.container}>
      {/* Toast notification */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            className={`${styles.toast} ${styles[`toast_${toast.type}`]}`}
          >
            {toast.message}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Left: Idea Navigator */}
      <div className={styles.ideaColumn}>
        {/* Tabs */}
        <div className={styles.tabs}>
          {TAB_ORDER.map(tab => (
            <button
              key={tab}
              className={`${styles.tab} ${activeTab === tab ? styles.activeTab : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
              {tabCounts[tab] > 0 && <span className={styles.tabBadge}>{tabCounts[tab]}</span>}
            </button>
          ))}
        </div>

        {activeTab === 'refining' && tabCounts.refining > 0 && (
          <div className={styles.refiningBanner}>
            <RefreshCw size={13} />
            <span>These ideas are being rewritten by AI. They'll return to <strong>Pending</strong> when ready.</span>
          </div>
        )}

        {/* Idea List */}
        <div className={styles.ideaList}>
          <AnimatePresence>
            {filteredIdeas.length === 0 ? (
              <div className={styles.emptyIdeas}>
                {activeTab === 'pending'
                  ? 'Inbox is clear. Trigger a run below to generate new ideas.'
                  : activeTab === 'refining'
                  ? 'No ideas currently being refined.'
                  : `No ${activeTab} ideas yet.`}
              </div>
            ) : (
              filteredIdeas.map((idea, index) => (
                <motion.div
                  key={idea.id}
                  layout
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  className={`${styles.ideaCard} ${index === focusIndex ? styles.ideaCardFocused : ''}`}
                  onClick={() => setFocusIndex(index)}
                >
                  <div className={styles.ideaCardMeta}>
                    <span className={styles.tag}>{idea.platform}</span>
                    {idea.angle_category && <span className={styles.tagAngle}>{idea.angle_category}</span>}
                    {idea.is_wildcard && <span className={`${styles.tag} ${styles.tagWild}`}>Wildcard</span>}
                    {idea.evergreen ? (
                      <span className={styles.evergreenTag}><Leaf size={10} /> Evergreen</span>
                    ) : (
                      <span className={styles.signalTag}><Zap size={10} /> Signal</span>
                    )}
                    {idea.status === 'refining' && (
                      <span className={styles.refiningTag}><Loader2 size={10} className={styles.spinIcon} /> Rewriting…</span>
                    )}
                  </div>
                  <p className={styles.ideaHook}>{idea.hook}</p>
                </motion.div>
              ))
            )}
          </AnimatePresence>
        </div>

        {/* Trigger Run button */}
        <button
          className={`btn-primary ${styles.triggerBtn} ${triggerLoading ? styles.triggerBtnLoading : ''}`}
          onClick={triggerRun}
          disabled={triggerLoading || isQueued || isAgentRunning}
        >
          {triggerLoading
            ? <><Loader2 size={15} className={styles.spinIcon} /> Queuing…</>
            : isQueued
            ? <><Loader2 size={15} className={styles.spinIcon} /> In queue…</>
            : isAgentRunning
            ? <><Loader2 size={15} className={styles.spinIcon} /> Agent running…</>
            : <><Play size={15} /> Trigger Ideation Run</>
          }
        </button>
      </div>

      {/* Right: Focus View + Always-visible status panel */}
      <div className={styles.focusColumn}>

        {/* ── ALWAYS VISIBLE: Live Status Panel ───────────────── */}
        <AnimatePresence>
          {(isQueued || isAgentRunning || liveTrace.length > 0) && (
            <motion.div
              className={styles.livePanel}
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
            >
              <div className={styles.livePanelHeader}>
                <span className={styles.liveDot} />
                <span className={styles.livePanelTitle}>
                  {isQueued
                    ? "Waiting in queue…"
                    : isAgentRunning
                    ? currentPhase ?? "Agent running…"
                    : "Run complete"}
                </span>
                {wsConnected && <span className={styles.wsConnected}>● connected</span>}
              </div>

              {/* Step-by-step progress */}
              {liveTrace.length > 0 && (
                <div className={styles.livePanelSteps}>
                  {liveTrace.map((t, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      className={`${styles.liveStep} ${t.status === 'error' ? styles.liveStepError : styles.liveStepOk}`}
                    >
                      <span className={styles.liveStepDot} />
                      <span className={styles.liveStepLabel}>{NODE_LABELS[t.node] || t.node}</span>
                      {i === liveTrace.length - 1 && isAgentRunning && (
                        <Loader2 size={11} className={styles.spinIcon} style={{ marginLeft: 4, opacity: 0.6 }} />
                      )}
                    </motion.div>
                  ))}
                  <div ref={traceEndRef} />
                </div>
              )}

              {/* Queued waiting state with pulse */}
              {isQueued && liveTrace.length === 0 && (
                <div className={styles.queuedHint}>
                  Celery beat checks every 60s. Agent will start automatically.
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── IDEA FOCUS VIEW ──────────────────────────────────── */}
        {focusedIdea ? (
          <div className={styles.focusCard}>
            {/* Signal Box */}
            {focusedIdea.signal_used && (
              <div className={styles.signalBox}>
                <div className={styles.signalHeader}>
                  {focusedIdea.evergreen ? <><Leaf size={13} /> Evergreen</> : <><Zap size={13} /> Market Signal</>}
                </div>
                <p className={styles.signalText}>{focusedIdea.signal_used}</p>
              </div>
            )}

            {/* Idea Content */}
            <div className={styles.focusContent}>
              <div className={styles.focusMeta}>
                <span className={styles.tag}>{focusedIdea.platform}</span>
                {focusedIdea.implication_type && <span className={styles.tag}>{focusedIdea.implication_type}</span>}
                {focusedIdea.angle_category && <span className={styles.tagAngle}>{focusedIdea.angle_category}</span>}
              </div>

              <h3 className={styles.focusHook}>{focusedIdea.hook}</h3>
              <p className={styles.focusBody}>{focusedIdea.body}</p>
              <p className={styles.focusCta}>{focusedIdea.cta}</p>

              {activeTab === 'rejected' && focusedIdea.admin_feedback && (
                <div className={styles.feedbackDisplay}>
                  <span className={styles.feedbackLabel}>Rejection note:</span>
                  <span>{focusedIdea.admin_feedback}</span>
                </div>
              )}
            </div>

            {/* Actions — only on pending tab */}
            {activeTab === 'pending' && (
              refiningId === focusedIdea.id ? (
                <div className={styles.refineBox}>
                  <textarea
                    autoFocus
                    placeholder="What should change? Be specific — the AI will rewrite accordingly."
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    className={styles.feedbackArea}
                    rows={4}
                  />
                  <div className={styles.refineActions}>
                    <button onClick={() => { setRefiningId(null); setFeedback(""); }} className="btn-secondary">Cancel</button>
                    <button onClick={() => handleRefine(focusedIdea.id)} disabled={!feedback.trim()} className="btn-primary">
                      Submit Feedback
                    </button>
                  </div>
                </div>
              ) : (
                <div className={styles.actions}>
                  <button onClick={() => handleAction(focusedIdea.id, 'approve')} disabled={isProcessing} className={styles.btnApprove}>
                    <Check size={16} /> Approve
                  </button>
                  <button onClick={() => handleAction(focusedIdea.id, 'reject')} disabled={isProcessing} className={styles.btnReject}>
                    <X size={16} /> Reject
                  </button>
                  <button onClick={() => setRefiningId(focusedIdea.id)} disabled={isProcessing} className={styles.btnRefine}>
                    <RefreshCw size={16} /> Refine
                  </button>
                </div>
              )
            )}

            {activeTab === 'pending' && (
              <div className={styles.shortcuts}>
                <kbd>A</kbd> Approve&nbsp;&nbsp;<kbd>R</kbd> Reject&nbsp;&nbsp;<kbd>F</kbd> Refine&nbsp;&nbsp;<kbd>↑↓</kbd> Navigate
              </div>
            )}

            {/* Collapsible past run trace */}
            {selectedRun && (
              <div className={styles.traceSection}>
                <button className={styles.traceToggle} onClick={() => setShowTrace(v => !v)}>
                  <span>Last Run Trace — #{selectedRun.id}</span>
                  {showTrace ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>

                <AnimatePresence>
                  {showTrace && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className={styles.traceBody}
                    >
                      {selectedRun.search_query && (
                        <div className={styles.traceSection2}>
                          <div className={styles.traceSectionLabel}>Search Query</div>
                          <code className={styles.traceQuery}>{selectedRun.search_query}</code>
                        </div>
                      )}

                      {selectedRun.signal && (
                        <div className={styles.traceSection2}>
                          <div className={styles.traceSectionLabel}>Signal</div>
                          <div className={styles.traceSignalRow}>
                            <span className={`${styles.strengthPill} ${styles['strength_' + (selectedRun.signal_strength || 'low')]}`}>
                              {selectedRun.signal_strength}
                            </span>
                            <span className={styles.signalText}>{selectedRun.signal?.signal_description || ''}</span>
                          </div>
                        </div>
                      )}

                      <div className={styles.traceSection2}>
                        <div className={styles.traceSectionLabel}>
                          Node Pipeline
                          <span className={`${styles.runStatusPill} ${selectedRun.status === 'success' ? styles.pillSuccess : styles.pillError}`}>
                            {selectedRun.status}
                          </span>
                        </div>
                        <div className={styles.nodeList}>
                          {(selectedRun.nodes || []).map((n, i) => (
                            <div key={i} className={`${styles.nodeRow} ${n.status === 'error' ? styles.nodeError : styles.nodeOk}`}>
                              <span className={styles.nodeIndicator} />
                              <span className={styles.nodeName}>{NODE_LABELS[n.node] || n.node}</span>
                              <span className={styles.nodeTime}>
                                {n.timestamp ? new Date((!n.timestamp.endsWith('Z') && !n.timestamp.includes('+') && !n.timestamp.includes('-', 10)) ? n.timestamp + 'Z' : n.timestamp).toLocaleTimeString() : ''}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {runs.length > 1 && (
                        <div className={styles.runSelector}>
                          {runs.slice(0, 5).map(run => (
                            <button
                              key={run.id}
                              className={`${styles.runChip} ${selectedRunId === run.id || (!selectedRunId && run === runs[0]) ? styles.runChipActive : ''}`}
                              onClick={() => setSelectedRunId(run.id)}
                            >
                              #{run.id} {run.status === 'error' ? '⚠' : ''}
                            </button>
                          ))}
                        </div>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </div>
        ) : (
          <div className={styles.noFocus}>
            {filteredIdeas.length === 0 && activeTab === 'pending' ? (
              <div className={styles.emptyFocusState}>
                <p>Your inbox is clear.</p>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '6px' }}>
                  Trigger a run below to generate new ideas.
                </p>
              </div>
            ) : (
              <p>{filteredIdeas.length === 0 ? `No ${activeTab} ideas.` : 'Select an idea to review.'}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
