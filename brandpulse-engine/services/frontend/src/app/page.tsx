"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { API_URL } from "@/lib/api";
import AddCompanyModal from "@/components/AddCompanyModal";
import styles from "./page.module.css";

interface Company {
  id: number;
  name: string;
  description: string | null;
  status: string;
  frequency_hours: number;
  next_run_time: string | null;
  is_processing: boolean;
  pending_ideas_count: number | null;
}

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
  // Ensure the date string is treated as UTC if backend omits the 'Z'
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
  const [companies, setCompanies] = useState<Company[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [companiesRes, statsRes, activityRes] = await Promise.all([
        fetch(`${API_URL}/companies/`),
        fetch(`${API_URL}/dashboard/stats`),
        fetch(`${API_URL}/dashboard/activity?limit=10`),
      ]);
      const [companiesData, statsData, activityData] = await Promise.all([
        companiesRes.json(),
        statsRes.json(),
        activityRes.json(),
      ]);
      setCompanies(companiesData);
      setStats(statsData);
      setActivity(activityData);
    } catch (err) {
      console.error("Dashboard fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 8000);
    return () => clearInterval(interval);
  }, []);

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
      {stats && (
        <div className={styles.statsRow}>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{stats.total_ideas_generated}</div>
            <div className={styles.statLabel}>Ideas Generated</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{stats.total_approved}</div>
            <div className={styles.statLabel}>Approved</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{stats.total_pending}</div>
            <div className={styles.statLabel}>Awaiting Review</div>
          </div>
          <div className={`${styles.statCard} ${styles.statHighlight}`}>
            <div className={styles.statValue}>{stats.overall_win_rate}%</div>
            <div className={styles.statLabel}>Win Rate</div>
          </div>
        </div>
      )}

      {/* Main content: Company table + Activity feed */}
      <div className={styles.mainGrid}>
        {/* Company Command Table */}
        <div className={styles.tableSection}>
          <h2 className={styles.sectionTitle}>Companies</h2>
          {loading ? (
            <div className={styles.loadingState}>Loading...</div>
          ) : companies.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No companies yet.</p>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '8px' }}>
                Click <strong>+ Add Company</strong> in the top right to get started.
              </p>
            </div>
          ) : (
            <div className={styles.table}>
              <div className={styles.tableHeader}>
                <span>Company</span>
                <span>Status</span>
                <span>Pending</span>
                <span>Next Run</span>
                <span>Action</span>
              </div>
              {companies.map((company) => (
                <div key={company.id} className={styles.tableRow}>
                  <div className={styles.companyCell}>
                    <Link href={`/companies/${company.id}/inbox`} className={styles.companyLink}>
                      {company.is_processing && <span className="processing-pulse" style={{ marginRight: '8px' }} />}
                      <span>{company.name}</span>
                    </Link>
                    {company.description && (
                      <span className={styles.companyDesc}>
                        {company.description.substring(0, 50)}{company.description.length > 50 ? '...' : ''}
                      </span>
                    )}
                  </div>
                  <div>
                    <span className={`${styles.statusBadge} ${company.status === 'active' ? styles.statusActive : styles.statusPaused}`}>
                      {company.is_processing ? 'Running' : company.status}
                    </span>
                  </div>
                  <div>
                    {company.pending_ideas_count ? (
                      <Link href={`/companies/${company.id}/inbox`} className={styles.pendingBadge}>
                        {company.pending_ideas_count} pending
                      </Link>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>—</span>
                    )}
                  </div>
                  <div className={styles.nextRun}>
                    {company.next_run_time
                      ? formatRelativeTime(company.next_run_time)
                      : '—'}
                  </div>
                  <div className={styles.rowActions}>
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
          )}
        </div>

        {/* Activity Feed */}
        <div className={styles.activitySection}>
          <h2 className={styles.sectionTitle}>Recent Runs</h2>
          {activity.length === 0 ? (
            <div className={styles.emptyActivity}>No runs yet.</div>
          ) : (
            <div className={styles.activityFeed}>
              {activity.map((event, i) => (
                <div key={i} className={styles.activityItem}>
                  <div className={`${styles.activityDot} ${event.status === 'success' ? styles.dotSuccess : styles.dotError}`} />
                  <div className={styles.activityContent}>
                    <span className={styles.activityCompany}>{event.company_name}</span>
                    <span className={styles.activityMeta}>
                      {event.ideas_generated} idea{event.ideas_generated !== 1 ? 's' : ''}
                      {event.evergreen ? ' · evergreen' : ' · signal-driven'}
                    </span>
                    <span className={styles.activityTime}>{formatRelativeTime(event.created_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
