"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./layout.module.css";
import { useEffect, useState, use } from "react";
import { API_URL } from "@/lib/api";

export default function CompanyLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const pathname = usePathname();
  const { id } = use(params);
  const [company, setCompany] = useState<any>(null);

  useEffect(() => {
    fetch(`${API_URL}/companies/${id}`)
      .then(r => r.json())
      .then(data => setCompany(data))
      .catch(console.error);
    // Refresh every 15s to update is_processing + next_run_time
    const interval = setInterval(() => {
      fetch(`${API_URL}/companies/${id}`)
        .then(r => r.json())
        .then(data => setCompany(data))
        .catch(console.error);
    }, 15000);
    return () => clearInterval(interval);
  }, [id]);

  // U4 Fix: show relative time ("in 3h", "in 1d 4h") not bare clock
  const formatNextRun = (isoDate: string): string => {
    const dateStr = (!isoDate.endsWith('Z') && !isoDate.includes('+') && !isoDate.includes('-', 10))
      ? isoDate + 'Z' : isoDate;
    const diffMs = new Date(dateStr).getTime() - Date.now();
    if (diffMs <= 0) return 'overdue';
    const totalMins = Math.floor(diffMs / 60000);
    const days = Math.floor(totalMins / 1440);
    const hrs = Math.floor((totalMins % 1440) / 60);
    const mins = totalMins % 60;
    if (days > 0) return `in ${days}d ${hrs}h`;
    if (hrs > 0) return `in ${hrs}h ${mins}m`;
    return `in ${mins}m`;
  };

  return (
    <div className={styles.workspace}>
      <header className={styles.header}>
        <div className={styles.companyInfo}>
          <div className={styles.companyNameRow}>
            {company?.is_processing && <span className="processing-pulse" />}
            <h2>{company ? company.name : "Loading..."}</h2>
          </div>
          <div className={styles.companyMeta}>
            <span className={`${styles.statusDot} ${company?.status === 'active' ? styles.dotActive : styles.dotPaused}`} />
            <span className={styles.statusText}>{company?.status || '—'}</span>
            {company?.next_run_time && (
              <span className={styles.nextRun}>
                · Next run {formatNextRun(company.next_run_time)}
              </span>
            )}
          </div>
        </div>
        <nav className={styles.tabs}>
          <Link
            href={`/companies/${id}/inbox`}
            className={`${styles.tab} ${pathname.includes('/inbox') ? styles.activeTab : ''}`}
          >
            Inbox
            {company?.pending_ideas_count ? (
              <span className={styles.tabBadge}>{company.pending_ideas_count}</span>
            ) : null}
          </Link>
          <Link
            href={`/companies/${id}/memory`}
            className={`${styles.tab} ${pathname.includes('/memory') ? styles.activeTab : ''}`}
          >
            Memory
          </Link>
          <Link
            href={`/companies/${id}/settings`}
            className={`${styles.tab} ${pathname.includes('/settings') ? styles.activeTab : ''}`}
          >
            Settings
          </Link>
        </nav>
      </header>
      <div className={styles.content}>
        {children}
      </div>
    </div>
  );
}
