"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { API_URL } from "@/lib/api";
import { useCompanies, Company } from "@/hooks/useCompanies";
import AddCompanyModal from "@/components/AddCompanyModal";
import styles from "./page.module.css";

interface Stats {
  total_ideas_generated: number;
  total_approved: number;
  total_pending: number;
  overall_win_rate: number;
}

interface ActivityEvent {
  type: string;
  company_id: number;
  company_name: string;
  status: string;
  ideas_generated: number;
  evergreen: boolean;
  created_at: string;
  run_id: number;
}

function formatRelativeTime(isoDate: string): string {
  if (!isoDate) return "—";
  const dateStr = (!isoDate.endsWith('Z') && !isoDate.includes('+') && !isoDate.includes('-', 10)) ? isoDate + 'Z' : isoDate;
  const diff = Date.now() - new Date(dateStr).getTime();
  
  if (diff < 0) {
    const mins = Math.floor(Math.abs(diff) / 60000);
    if (mins < 1) return "in a moment";
    if (mins < 60) return `in ${mins}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `in ${hrs}h`;
    return `in ${Math.floor(hrs / 24)}d`;
  }

  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function DashboardHome() {
  const {
    data: companies = [],
    isLoading: companiesLoading,
    error: companiesError,
  } = useCompanies();

  const {
    data: stats,
    isLoading: statsLoading,
  } = useQuery<Stats>({
    queryKey: ["dashboard", "stats"],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/dashboard/stats`);
      if (!res.ok) throw new Error("Failed to fetch dashboard stats");
      return res.json();
    },
    refetchInterval: 8000,
  });

  const {
    data: activity = [],
    isLoading: activityLoading,
  } = useQuery<ActivityEvent[]>({
    queryKey: ["dashboard", "activity"],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/dashboard/activity?limit=10`);
      if (!res.ok) throw new Error("Failed to fetch activity feed");
      return res.json();
    },
    refetchInterval: 8000,
  });

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Command Center</h1>
          <p className={styles.subtitle}>Your brands, all signal-driven content intelligence in one place.</p>
        </div>
        <AddCompanyModal />
      </header>

      {/* Stats Row */}
      {statsLoading ? (
        <div className={styles.statsRow}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className={styles.statCard} style={{ opacity: 0.6 }}>
              <div className={styles.statValue}>...</div>
              <div className={styles.statLabel}>Loading</div>
            </div>
          ))}
        </div>
      ) : stats ? (
        <div className={styles.statsRow}>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{stats.total_ideas_generated}</div>
            <div className={styles.statLabel}>Total Ideas</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{stats.total_approved}</div>
            <div className={styles.statLabel}>Approved</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{stats.total_pending}</div>
            <div className={styles.statLabel}>Pending Review</div>
          </div>
          <div className={`${styles.statCard} ${styles.statHighlight}`}>
            <div className={styles.statValue}>{stats.overall_win_rate}%</div>
            <div className={styles.statLabel}>Approval Rate</div>
          </div>
        </div>
      ) : null}

      {/* Main content: Company table + Activity feed */}
      <div className={styles.mainGrid}>
        {/* Company Command Table */}
        <div className={styles.tableSection}>
          <h2 className={styles.sectionTitle}>Companies</h2>
          {companiesLoading ? (
            <div className={styles.loadingState}>Loading companies...</div>
          ) : companiesError ? (
            <div className={styles.emptyState}>
              <p style={{ color: "var(--status-error)" }}>Failed to load companies.</p>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "8px" }}>
                Please ensure the backend engine is running.
              </p>
            </div>
          ) : companies.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No companies yet.</p>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "8px" }}>
                Click <strong>+ Add Company</strong> in the top right to get started.
              </p>
            </div>
          ) : (
            <div className={styles.table} role="table" aria-label="Companies List">
              <div className={styles.tableHeader} role="row">
                <span role="columnheader">Company</span>
                <span role="columnheader">Status</span>
                <span role="columnheader">Pending</span>
                <span role="columnheader">Next Run</span>
                <span role="columnheader">Action</span>
              </div>
              <div role="rowgroup">
                {companies.map((company: Company) => (
                  <div key={company.id} className={styles.tableRow} role="row">
                    <div className={styles.companyCell} role="cell">
                      <Link href={`/companies/${company.id}/inbox`} className={styles.companyLink}>
                        {company.is_processing && <span className="processing-pulse" style={{ marginRight: "8px" }} />}
                        <span>{company.name}</span>
                      </Link>
                      {company.description && (
                        <span className={styles.companyDesc}>
                          {company.description.substring(0, 50)}{company.description.length > 50 ? "..." : ""}
                        </span>
                      )}
                    </div>
                    <div role="cell">
                      <span className={`${styles.statusBadge} ${company.status === "active" ? styles.statusActive : styles.statusPaused}`}>
                        {company.is_processing ? "Generating" :
                         company.status === "active" ? "Scheduled" :
                         "Paused"}
                      </span>
                    </div>
                    <div role="cell">
                      {company.pending_ideas_count ? (
                        <Link href={`/companies/${company.id}/inbox`} className={styles.pendingBadge}>
                          {company.pending_ideas_count} pending
                        </Link>
                      ) : (
                        <span style={{ color: "var(--text-muted)" }}>—</span>
                      )}
                    </div>
                    <div className={styles.nextRun} role="cell">
                      {company.next_run_time
                        ? formatRelativeTime(company.next_run_time)
                        : "—"}
                    </div>
                    <div className={styles.rowActions} role="cell">
                      <Link href={`/companies/${company.id}/inbox`} className={styles.actionBtn}>
                        Inbox
                      </Link>
                      <Link href={`/companies/${company.id}/settings`} className={styles.actionBtnSecondary}>
                        Settings
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Activity Feed */}
        <div className={styles.activitySection}>
          <h2 className={styles.sectionTitle}>Recent Runs</h2>
          {activityLoading ? (
            <div className={styles.emptyActivity}>Loading activity...</div>
          ) : activity.length === 0 ? (
            <div className={styles.emptyActivity}>No runs yet.</div>
          ) : (
            <div className={styles.activityFeed}>
              {activity.map((event, i) => (
                <Link key={i} href={`/companies/${event.company_id}/inbox`} className={styles.activityItem} style={{ textDecoration: 'none' }}>
                  <div className={`${styles.activityDot} ${
                    event.status === "success" ? styles.dotSuccess :
                    event.status === "empty" ? styles.dotEmpty :
                    styles.dotError
                  }`} />
                  <div className={styles.activityContent}>
                    <span className={styles.activityCompany}>{event.company_name}</span>
                    <span className={styles.activityMeta}>
                      {event.status === "empty" ? "0 ideas — no results" :
                       event.status === "error" ? "Run failed" :
                       `${event.ideas_generated} idea${event.ideas_generated !== 1 ? "s" : ""} generated`}
                    </span>
                    <span className={styles.activityTime}>{formatRelativeTime(event.created_at)}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
