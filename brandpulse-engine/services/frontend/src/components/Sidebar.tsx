"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCompanies } from "@/hooks/useCompanies";

export default function Sidebar() {
  const { data: companies = [], isLoading } = useCompanies();
  const pathname = usePathname();

  return (
    <aside className="sidebar glass-panel">
      <div className="sidebar-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ display: 'flex', alignItems: 'center' }}>
          <span className="health-dot"></span>
          BrandPulse
        </h2>
      </div>

      <nav className="sidebar-nav">
        <div className="section-label">Global</div>
        <Link href="/" className={`nav-item ${pathname === '/' ? 'active' : ''}`}>
          Command Center
        </Link>
        <Link href="/library" className={`nav-item ${pathname === '/library' ? 'active' : ''}`}>
          Library
        </Link>

        {/* B1 Fix: removed dead /add-company link — AddCompanyModal lives on the home page */}
        <div className="section-label">Companies</div>

        <div className="company-list">
          {isLoading ? (
            <div style={{ padding: '0 16px', color: 'var(--text-muted)' }}>Loading...</div>
          ) : companies.length === 0 ? (
            <div style={{ padding: '0 16px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              No companies yet.<br />
              <Link href="/" style={{ color: 'var(--accent-base)', textDecoration: 'none' }}>
                ＋ Add one from home
              </Link>
            </div>
          ) : (
            companies.map((company) => (
              <Link
                key={company.id}
                href={`/companies/${company.id}/inbox`}
                className={`company-item ${pathname?.includes(`/companies/${company.id}`) ? 'active' : ''}`}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {company.is_processing && <span className="processing-pulse"></span>}
                  {!company.is_processing && company.status === 'paused' && (
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 600, lineHeight: 1, flexShrink: 0 }}>⏸</span>
                  )}
                  <span style={{
                    maxWidth: company.pending_ideas_count ? '120px' : '160px',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {company.name}
                  </span>
                </div>
                {company.pending_ideas_count ? (
                  <span className="pending-badge">{company.pending_ideas_count}</span>
                ) : null}
              </Link>
            ))
          )}
        </div>
      </nav>
    </aside>
  );
}
