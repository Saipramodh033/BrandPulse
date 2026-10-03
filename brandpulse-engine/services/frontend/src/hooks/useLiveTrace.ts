import { useEffect, useRef, useState, useCallback } from "react";
import { API_URL } from "@/lib/api";

/**
 * Individual execution step emitted by the backend agent (e.g. recall_memory, search_web).
 */
export interface TraceNode {
  node: string;
  status: string;
  timestamp: string;
  message?: string;
  ideas_count?: number;
  attempt?: number;
  max_retries?: number;
}

/**
 * Final execution status summary displayed in the UI banner upon run completion.
 */
export interface RunSummary {
  ideasCount: number;
  status: "success" | "empty" | "error";
  message: string;
}

/**
 * React hook that maintains a real-time WebSocket connection to the API trace gateway.
 * Streams agent tool invocations, handles automatic reconnection, and updates run summaries.
 */
export function useLiveTrace(companyId: string | number, onFinish?: () => void) {
  const [liveTrace, setLiveTrace] = useState<TraceNode[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [isQueued, setIsQueued] = useState(false);
  const [isAgentRunning, setIsAgentRunning] = useState(false);
  const [runSummary, setRunSummary] = useState<RunSummary | null>(null);
  const [retryInfo, setRetryInfo] = useState<{ attempt: number; max: number } | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isUnmountingRef = useRef(false);
  const lastMessageTimeRef = useRef<number>(Date.now());

  const clearTrace = useCallback(() => {
    setLiveTrace([]);
    setIsAgentRunning(false);
    setRunSummary(null);
    setRetryInfo(null);
  }, []);

  const connect = useCallback(() => {
    if (!companyId || isUnmountingRef.current) return;

    try {
      // Convert HTTP API URL to WebSocket protocol (http -> ws, https -> wss)
      const apiBase = API_URL.replace(/^http/, "ws");
      const wsUrl = `${apiBase}/ws/trace/${companyId}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onclose = () => {
        setWsConnected(false);
        setIsAgentRunning(false);

        // Auto-reconnect with 3-second backoff if the component is still mounted
        if (!isUnmountingRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 3000);
        }
      };

      ws.onerror = (err) => {
        console.warn("WebSocket error in trace hook:", err);
      };

      ws.onmessage = (event) => {
        try {
          const data: TraceNode = JSON.parse(event.data);
          lastMessageTimeRef.current = Date.now();
          setIsQueued(false);
          setIsAgentRunning(true);
          setLiveTrace((prev) => [...prev, data]);

          // Handle automatic Celery retry notifications (don't terminate the running UI state)
          if (data.node === "retry") {
            setRetryInfo({ attempt: data.attempt ?? 1, max: data.max_retries ?? 3 });
            return;
          }

          if (data.node === "complete" || data.node === "fatal" || data.node === "error") {
            const summary: RunSummary = {
              ideasCount: data.ideas_count ?? 0,
              status:
                data.node === "complete" && (data.ideas_count ?? 0) > 0
                  ? "success"
                  : data.node === "complete"
                  ? "empty"
                  : "error",
              message:
                data.message ??
                (data.node === "complete"
                  ? data.ideas_count
                    ? `${data.ideas_count} ideas added to Review`
                    : "Run complete — no ideas generated"
                  : "Run failed"),
            };
            setRunSummary(summary);
            setRetryInfo(null);
            setTimeout(() => {
              setIsAgentRunning(false);
              onFinish?.();
            }, 3000); // 3s so user can read the summary
          }
        } catch (e) {
          console.error("Error parsing WebSocket message:", e);
        }
      };
    } catch (e) {
      console.error("Failed to establish WebSocket:", e);
    }
  }, [companyId, onFinish]);

  useEffect(() => {
    isUnmountingRef.current = false;
    connect();

    return () => {
      isUnmountingRef.current = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    liveTrace,
    wsConnected,
    isQueued,
    setIsQueued,
    isAgentRunning,
    clearTrace,
    runSummary,
    retryInfo,
  };
}
