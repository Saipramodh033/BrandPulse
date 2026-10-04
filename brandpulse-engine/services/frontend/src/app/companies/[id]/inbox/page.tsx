"use client";

import { useState, useRef, useEffect, use, useMemo, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { API_URL } from "@/lib/api";
import { useLiveTrace, TraceNode } from "@/hooks/useLiveTrace";
import { useCompany } from "@/hooks/useCompanies";
import styles from "./inbox.module.css";
import { Check, X, RefreshCw, ChevronDown, ChevronUp, Zap, Leaf, Play, Loader2 } from "lucide-react";
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

const TAB_DISPLAY: Record<string, string> = {
  pending: "Review",
  approved: "Approved",
  rejected: "Rejected",
  refining: "Rewriting",
};

const NODE_LABELS: Record<string, string> = {
  recall_company_memory: "Recalling past content angles",
  profile_company: "Profiling company",
  search_web: "Searching market news",
  extract_signal: "Extracting key signal",
  generate_ideas: "Generating content ideas",
  validate_and_critique_ideas: "Validating ideas",
  finish: "Saving ideas",
  complete: "Run complete",
  error: "Error encountered",
  retry: "Retrying…",
  fatal: "Run failed",
};

const NODE_PHASE: Record<string, string> = {
  recall_company_memory: "Recalling past content angles…",
  profile_company: "Profiling company…",
  search_web: "Searching market news…",
  extract_signal: "Extracting key signal…",
  generate_ideas: "Generating content ideas…",
  validate_and_critique_ideas: "Validating ideas…",
  finish: "Saving ideas…",
  complete: "Run complete",
  error: "Error encountered",
  retry: "Retrying…",
  fatal: "Run failed",
};

interface Toast {
  message: string;
  type: "success" | "error" | "info";
}

export default function IdeaInbox({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const companyId = Number(id);
  const queryClient = useQueryClient();

  const { data: company } = useCompany(companyId);

  const [activeTab, setActiveTab] = useState<IdeaStatus>("pending");
  const [selectedIdeaId, setSelectedIdeaId] = useState<number | null>(null);

  // Trace / runs state
  const [showTrace, setShowTrace] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);

  // Actions state
  const [refiningId, setRefiningId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState("");
  const [triggerLoading, setTriggerLoading] = useState(false);

  // Toast
  const [toast, setToast] = useState<Toast | null>(null);
  const toastTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Refs for scrolling
  const cardRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const traceEndRef = useRef<HTMLDivElement>(null);

  const showToast = useCallback((message: string, type: Toast["type"] = "success") => {
    if (toastTimeout.current) clearTimeout(toastTimeout.current);
    setToast({ message, type });
    toastTimeout.current = setTimeout(() => setToast(null), 3000);
  }, []);

  // Fetch Ideas
  const {
    data: allIdeas = [],
    isLoading: ideasLoading,
    error: ideasError,
  } = useQuery<Idea[]>({
    queryKey: ["ideas", companyId],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/companies/${companyId}/ideas?limit=100`);
      if (!res.ok) throw new Error("Failed to fetch ideas");
      return res.json();
    },
    enabled: !!companyId,
    staleTime: 2000,
  });

  // Fetch Runs
  const { data: runs = [] } = useQuery<RunLog[]>({
    queryKey: ["runs", companyId],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/companies/${companyId}/runs?limit=10`);
      if (!res.ok) throw new Error("Failed to fetch runs");
      return res.json();
    },
    enabled: !!companyId,
  });

  // Callback when live trace finishes
  const handleRunFinish = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["ideas", companyId] });
    queryClient.invalidateQueries({ queryKey: ["runs", companyId] });
    queryClient.invalidateQueries({ queryKey: ["companies"] });
    queryClient.invalidateQueries({ queryKey: ["company", String(companyId)] });
  }, [queryClient, companyId]);

  // Live trace hook with auto-reconnect
  const {
    liveTrace,
    wsConnected,
    isQueued,
    setIsQueued,
    isAgentRunning,
    clearTrace,
    runSummary,
    retryInfo,
  } = useLiveTrace(companyId, handleRunFinish);

  useEffect(() => {
    traceEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [liveTrace]);

  // Filter ideas by tab
  const filteredIdeas = useMemo(() => {
    return allIdeas.filter((i) => i.status === activeTab);
  }, [allIdeas, activeTab]);

  // Determine currently focused idea
  const focusedIdea = useMemo(() => {
    if (filteredIdeas.length === 0) return null;
    if (selectedIdeaId !== null) {
      const found = filteredIdeas.find((i) => i.id === selectedIdeaId);
      if (found) return found;
    }
    return filteredIdeas[0] ?? null;
  }, [filteredIdeas, selectedIdeaId]);

  const focusedIndex = useMemo(() => {
    if (!focusedIdea) return -1;
    return filteredIdeas.findIndex((i) => i.id === focusedIdea.id);
  }, [filteredIdeas, focusedIdea]);

  // Tab counts
  const tabCounts = useMemo(() => {
    return {
      pending: allIdeas.filter((i) => i.status === "pending").length,
      approved: allIdeas.filter((i) => i.status === "approved").length,
      rejected: allIdeas.filter((i) => i.status === "rejected").length,
      refining: allIdeas.filter((i) => i.status === "refining").length,
    };
  }, [allIdeas]);

  // Auto-scroll selected idea card into view
  useEffect(() => {
    if (focusedIdea && cardRefs.current[focusedIdea.id]) {
      cardRefs.current[focusedIdea.id]?.scrollIntoView({
        block: "nearest",
        behavior: "smooth",
      });
    }
  }, [focusedIdea]);

  // Mutations with non-blocking optimistic updates
  const actionMutation = useMutation({
    mutationFn: async ({ ideaId, action }: { ideaId: number; action: "approve" | "reject" }) => {
      const res = await fetch(`${API_URL}/ideas/${ideaId}/${action}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: action === "reject" ? JSON.stringify({ feedback: "" }) : undefined,
      });
      if (!res.ok) throw new Error(`Action failed with status ${res.status}`);
      return { ideaId, action };
    },
    onMutate: async ({ ideaId, action }) => {
      await queryClient.cancelQueries({ queryKey: ["ideas", companyId] });
      const previousIdeas = queryClient.getQueryData<Idea[]>(["ideas", companyId]);

      // Optimistically update
      queryClient.setQueryData<Idea[]>(["ideas", companyId], (old = []) =>
        old.map((i) => (i.id === ideaId ? { ...i, status: action === "approve" ? "approved" : "rejected" } : i))
      );

      // Advance focus to next item if on pending tab
      const currentFiltered = (previousIdeas || []).filter((i) => i.status === activeTab);
      const currentIndex = currentFiltered.findIndex((i) => i.id === ideaId);
      if (currentIndex !== -1 && currentFiltered.length > 1) {
        const nextIdea = currentFiltered[currentIndex + 1] || currentFiltered[currentIndex - 1];
        if (nextIdea) setSelectedIdeaId(nextIdea.id);
      }

      showToast(action === "approve" ? "✓ Idea approved" : "✓ Idea rejected");
      return { previousIdeas };
    },
    onError: (err: any, _variables, context) => {
      if (context?.previousIdeas) {
        queryClient.setQueryData(["ideas", companyId], context.previousIdeas);
      }
      showToast(`Action failed: ${err.message}`, "error");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["ideas", companyId] });
      queryClient.invalidateQueries({ queryKey: ["companies"] });
    },
  });

  const refineMutation = useMutation({
    mutationFn: async ({ ideaId, feedbackText }: { ideaId: number; feedbackText: string }) => {
      const res = await fetch(`${API_URL}/ideas/${ideaId}/refine`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feedback: feedbackText }),
      });
      if (!res.ok) throw new Error(`Refine failed with status ${res.status}`);
      return res.json();
    },
    onMutate: async ({ ideaId }) => {
      await queryClient.cancelQueries({ queryKey: ["ideas", companyId] });
      const previousIdeas = queryClient.getQueryData<Idea[]>(["ideas", companyId]);

      queryClient.setQueryData<Idea[]>(["ideas", companyId], (old = []) =>
        old.map((i) => (i.id === ideaId ? { ...i, status: "refining" } : i))
      );

      showToast("↻ Refinement queued — idea will return to Pending when ready", "info");
      return { previousIdeas };
    },
    onError: (err: any, _variables, context) => {
      if (context?.previousIdeas) {
        queryClient.setQueryData(["ideas", companyId], context.previousIdeas);
      }
      showToast(`Refinement failed: ${err.message}`, "error");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["ideas", companyId] });
      queryClient.invalidateQueries({ queryKey: ["companies"] });
    },
  });

  const handleAction = (ideaId: number, action: "approve" | "reject") => {
    actionMutation.mutate({ ideaId, action });
  };

  const handleRefine = (ideaId: number) => {
    if (!feedback.trim()) return;
    refineMutation.mutate({ ideaId, feedbackText: feedback });
    setRefiningId(null);
    setFeedback("");
  };

  /**
   * Manually dispatches a content generation run for this company.
   * If the agent is already running or ideas are pending, the API returns a 409 Conflict.
   */
  const triggerRun = async () => {
    if (triggerLoading || isQueued || isAgentRunning) return;
    setTriggerLoading(true);
    clearTrace();

    try {
      const res = await fetch(`${API_URL}/companies/${companyId}/run`, { method: "POST" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        if (res.status === 409) {
          showToast(body.detail || "Clear your inbox before triggering a new run.", "error");
        } else {
          showToast(`Failed to trigger run: ${res.status}`, "error");
        }
        return;
      }
      setIsQueued(true);
      showToast("✓ Run queued — the AI pipeline will start within 60 seconds", "success");
    } catch (e: any) {
      showToast(`Trigger failed: ${e.message}`, "error");
    } finally {
      setTriggerLoading(false);
    }
  };

  /**
   * Emergency recovery: releases a stuck is_processing database lock.
   * Also triggers cooperative cancellation if an agent worker is actively executing.
   */
  const handleResetLock = async () => {
    try {
      const res = await fetch(`${API_URL}/companies/${companyId}/reset-lock`, { method: "POST" });
      if (res.ok) {
        showToast("✓ Lock cleared — agent reset", "success");
        queryClient.invalidateQueries({ queryKey: ["company", String(companyId)] });
        queryClient.invalidateQueries({ queryKey: ["companies"] });
      } else {
        showToast("Failed to reset lock", "error");
      }
    } catch (e: any) {
      showToast(`Reset failed: ${e.message}`, "error");
    }
  };

  // High-speed non-blocking keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (document.activeElement?.tagName === "TEXTAREA" || document.activeElement?.tagName === "INPUT") return;
      if (!focusedIdea || refiningId !== null || e.repeat) return;

      if (activeTab === "pending") {
        if (e.key.toLowerCase() === "a") {
          e.preventDefault();
          handleAction(focusedIdea.id, "approve");
          return;
        }
        if (e.key.toLowerCase() === "r") {
          e.preventDefault();
          handleAction(focusedIdea.id, "reject");
          return;
        }
        if (e.key.toLowerCase() === "f") {
          e.preventDefault();
          setRefiningId(focusedIdea.id);
          return;
        }
      }

      if (e.key === "ArrowDown") {
        e.preventDefault();
        const nextIndex = Math.min(focusedIndex + 1, filteredIdeas.length - 1);
        if (filteredIdeas[nextIndex]) {
          setSelectedIdeaId(filteredIdeas[nextIndex].id);
        }
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        const prevIndex = Math.max(focusedIndex - 1, 0);
        if (filteredIdeas[prevIndex]) {
          setSelectedIdeaId(filteredIdeas[prevIndex].id);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [focusedIdea, focusedIndex, filteredIdeas, activeTab, refiningId]);

  const selectedRun = selectedRunId ? runs.find((r) => r.id === selectedRunId) : runs[0];

  const isCompanyProcessing = Boolean(company?.is_processing);
  const isRunning = isAgentRunning || isCompanyProcessing;
  const showLivePanel = isQueued || isRunning || liveTrace.length > 0;

  // Show stuck banner if is_processing but no WS activity and no trace
  const isStuck = isCompanyProcessing && !isAgentRunning && !isQueued && liveTrace.length === 0;

  const currentPhase = (() => {
    const lastNode = liveTrace[liveTrace.length - 1];
    if (runSummary) {
      if (runSummary.status === "success")
        return `✓ ${runSummary.ideasCount} idea${runSummary.ideasCount !== 1 ? "s" : ""} added to Review`;
      if (runSummary.status === "empty")
        return "⚠ Run complete — no ideas generated";
      return "⚠ Run failed";
    }
    if (retryInfo)
      return `Retrying… (attempt ${retryInfo.attempt} of ${retryInfo.max})`;
    if (lastNode?.node === "fatal") return "⚠ Run failed after multiple attempts";
    if (lastNode?.node === "error") return "⚠ AI encountered an error";
    if (lastNode?.node === "complete") return lastNode.ideas_count ? `✓ ${lastNode.ideas_count} ideas added` : "⚠ No ideas generated";
    if (liveTrace.length > 0) return NODE_PHASE[lastNode.node] ?? "Processing…";
    if (isAgentRunning) return `Generating ideas for ${company?.name ?? "company"}…`;
    if (isQueued) return "Scheduled — AI agent will start shortly";
    if (isCompanyProcessing) return "Starting up…";
    return null;
  })();

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
          {TAB_ORDER.map((tab) => (
            <button
              key={tab}
              className={`${styles.tab} ${activeTab === tab ? styles.activeTab : ""}`}
              onClick={() => {
                setActiveTab(tab);
                setSelectedIdeaId(null);
              }}
            >
              {TAB_DISPLAY[tab] ?? (tab.charAt(0).toUpperCase() + tab.slice(1))}
              {tabCounts[tab] > 0 && <span className={styles.tabBadge}>{tabCounts[tab]}</span>}
            </button>
          ))}
        </div>

        {activeTab === "refining" && tabCounts.refining > 0 && (
          <div className={styles.refiningBanner}>
            <RefreshCw size={13} />
            <span>These ideas are being rewritten by AI. They'll return to <strong>Review</strong> when ready.</span>
          </div>
        )}

        {/* Idea List */}
        <div className={styles.ideaList}>
          {ideasLoading ? (
            <div className={styles.emptyIdeas}>Loading ideas...</div>
          ) : ideasError ? (
            <div className={styles.errorBanner}>Failed to load ideas.</div>
          ) : filteredIdeas.length === 0 ? (
            <div className={styles.emptyIdeas}>
              {activeTab === "pending"
                ? "All caught up — no ideas awaiting review. Generate a new batch below."
                : activeTab === "refining"
                ? "No ideas are currently being rewritten."
                : activeTab === "rejected"
                ? "No rejected ideas."
                : `No ${TAB_DISPLAY[activeTab] ?? activeTab} ideas yet.`}
            </div>
          ) : (
            filteredIdeas.map((idea) => {
              const isFocused = focusedIdea?.id === idea.id;
              return (
                <div
                  key={idea.id}
                  ref={(el) => {
                    cardRefs.current[idea.id] = el;
                  }}
                  className={`${styles.ideaCard} ${isFocused ? styles.ideaCardFocused : ""}`}
                  onClick={() => setSelectedIdeaId(idea.id)}
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
                    {idea.status === "refining" && (
                      <span className={styles.refiningTag}><Loader2 size={10} className={styles.spinIcon} /> Rewriting…</span>
                    )}
                  </div>
                  <p className={styles.ideaHook}>{idea.hook}</p>
                </div>
              );
            })
          )}
        </div>

        {/* Trigger Run button */}
        <button
          className={`btn-primary ${styles.triggerBtn} ${triggerLoading ? styles.triggerBtnLoading : ""}`}
          onClick={triggerRun}
          disabled={triggerLoading || isQueued || isRunning}
        >
          {triggerLoading ? (
            <><Loader2 size={15} className={styles.spinIcon} /> Queuing…</>
          ) : isQueued ? (
            <><Loader2 size={15} className={styles.spinIcon} /> In queue…</>
          ) : isRunning ? (
            <><Loader2 size={15} className={styles.spinIcon} /> {isAgentRunning && liveTrace.length > 0 ? "Generating…" : "Starting up…"}</>
          ) : (
            <><Play size={15} /> Generate Ideas</>
          )}
        </button>
      </div>

      {/* Right: Focus View + Always-visible status panel */}
      <div className={styles.focusColumn}>
        {/* Stuck Agent Banner */}
        {isStuck && (
          <div className={styles.stuckBanner}>
            <span>⚠ Agent appears to be stuck — no activity detected.</span>
            <button onClick={handleResetLock} className={styles.resetBtn}>
              Force Reset
            </button>
          </div>
        )}

        {/* Live Status Panel */}
        <AnimatePresence>
          {showLivePanel && (
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
                    : isRunning
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
                      className={`${styles.liveStep} ${t.status === "error" ? styles.liveStepError : styles.liveStepOk}`}
                    >
                      <span className={styles.liveStepDot} />
                      <span className={styles.liveStepLabel}>{NODE_LABELS[t.node] || t.node}</span>
                      {i === liveTrace.length - 1 && isRunning && (
                        <Loader2 size={11} className={styles.spinIcon} style={{ marginLeft: 4, opacity: 0.6 }} />
                      )}
                    </motion.div>
                  ))}
                  <div ref={traceEndRef} />
                </div>
              )}

              {/* Run summary after completion */}
              {runSummary && (
                <div className={runSummary.status === "success" ? styles.summarySuccess : styles.summaryWarning}>
                  {runSummary.status === "success" && `✓ ${runSummary.ideasCount} idea${runSummary.ideasCount !== 1 ? "s" : ""} added to your Review tab — check them out!`}
                  {runSummary.status === "empty" && "⚠ Run completed but no ideas passed quality checks. Try again or update the company description."}
                  {runSummary.status === "error" && "⚠ The run encountered an error and could not complete. You can try triggering a new run."}
                </div>
              )}

              {/* Retry info */}
              {retryInfo && (
                <div className={styles.queuedHint}>
                  AI encountered an error — automatically retrying (attempt {retryInfo.attempt} of {retryInfo.max})…
                </div>
              )}

              {/* Queued waiting state */}
              {isQueued && liveTrace.length === 0 && !runSummary && (
                <div className={styles.queuedHint}>
                  Scheduled — the AI agent will pick this up shortly.
                </div>
              )}
              {isCompanyProcessing && !isQueued && liveTrace.length === 0 && !runSummary && (
                <div className={styles.queuedHint}>
                  Starting up…
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Idea Focus View */}
        {ideasLoading ? (
          <div className={styles.noFocus}>
            <p>Loading idea details...</p>
          </div>
        ) : focusedIdea ? (
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

              {activeTab === "rejected" && focusedIdea.admin_feedback && !focusedIdea.admin_feedback.startsWith("[Rewrite failed") && (
                <div className={styles.feedbackDisplay}>
                  <span className={styles.feedbackLabel}>Rejection note:</span>
                  <span>{focusedIdea.admin_feedback}</span>
                </div>
              )}
              {activeTab === "refining" && focusedIdea.admin_feedback && (
                <div className={styles.feedbackDisplay}>
                  <span className={styles.feedbackLabel}>Your rewrite note:</span>
                  <span>{focusedIdea.admin_feedback}</span>
                </div>
              )}
              {focusedIdea.admin_feedback?.startsWith("[Rewrite failed") && (
                <div className={styles.feedbackDisplay} style={{ borderColor: "rgba(245,158,11,0.3)", background: "rgba(245,158,11,0.06)" }}>
                  <span className={styles.feedbackLabel} style={{ color: "var(--accent-base)" }}>Rewrite failed:</span>
                  <span style={{ color: "var(--text-muted)" }}>The AI could not rewrite this idea. Please try again with different feedback.</span>
                </div>
              )}
            </div>

            {/* Actions — only on pending tab */}
            {activeTab === "pending" && (
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
                  <button onClick={() => handleAction(focusedIdea.id, "approve")} className={styles.btnApprove}>
                    <Check size={16} /> Approve
                  </button>
                  <button onClick={() => handleAction(focusedIdea.id, "reject")} className={styles.btnReject}>
                    <X size={16} /> Reject
                  </button>
                  <button onClick={() => setRefiningId(focusedIdea.id)} className={styles.btnRefine}>
                    <RefreshCw size={16} /> Refine
                  </button>
                </div>
              )
            )}

            {activeTab === "pending" && (
              <div className={styles.shortcuts}>
                <kbd>A</kbd> Approve&nbsp;&nbsp;<kbd>R</kbd> Reject&nbsp;&nbsp;<kbd>F</kbd> Refine&nbsp;&nbsp;<kbd>↑↓</kbd> Navigate
              </div>
            )}

            {/* Collapsible past run trace */}
            {selectedRun && (
              <div className={styles.traceSection}>
                <button className={styles.traceToggle} onClick={() => setShowTrace((v) => !v)}>
                  <span>Last Run Trace — #{selectedRun.id}</span>
                  {showTrace ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>

                <AnimatePresence>
                  {showTrace && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
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
                            <span className={`${styles.strengthPill} ${styles["strength_" + (selectedRun.signal_strength || "low")]}`}>
                              {selectedRun.signal_strength}
                            </span>
                            <span className={styles.signalText}>{selectedRun.signal?.signal_description || ""}</span>
                          </div>
                        </div>
                      )}

                      <div className={styles.traceSection2}>
                        <div className={styles.traceSectionLabel}>
                          Node Pipeline
                          <span className={`${styles.runStatusPill} ${selectedRun.status === "success" ? styles.pillSuccess : styles.pillError}`}>
                            {selectedRun.status}
                          </span>
                        </div>
                        <div className={styles.nodeList}>
                          {(selectedRun.nodes || []).map((n, i) => (
                            <div key={i} className={`${styles.nodeRow} ${n.status === "error" ? styles.nodeError : styles.nodeOk}`}>
                              <span className={styles.nodeIndicator} />
                              <span className={styles.nodeName}>{NODE_LABELS[n.node] || n.node}</span>
                              <span className={styles.nodeTime}>
                                {n.timestamp ? new Date((!n.timestamp.endsWith("Z") && !n.timestamp.includes("+") && !n.timestamp.includes("-", 10)) ? n.timestamp + "Z" : n.timestamp).toLocaleTimeString() : ""}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {runs.length > 1 && (
                        <div className={styles.runSelector}>
                          {runs.slice(0, 5).map((run) => (
                            <button
                              key={run.id}
                              className={`${styles.runChip} ${selectedRunId === run.id || (!selectedRunId && run === runs[0]) ? styles.runChipActive : ""}`}
                              onClick={() => setSelectedRunId(run.id)}
                            >
                              #{run.id} {run.status === "error" ? "⚠" : ""}
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
            {filteredIdeas.length === 0 && activeTab === "pending" ? (
              <div className={styles.emptyFocusState}>
                <p>Your inbox is clear.</p>
                <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "6px" }}>
                  Trigger a run below to generate new ideas.
                </p>
              </div>
            ) : (
              <p>{filteredIdeas.length === 0 ? `No ${activeTab} ideas.` : "Select an idea to review."}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
