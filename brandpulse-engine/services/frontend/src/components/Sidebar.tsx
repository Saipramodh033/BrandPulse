"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface Company {
  id: number;
  name: string;
  is_processing: boolean;
  pending_ideas_count: number | null;
}

export default function Sidebar() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const pathname = usePathname();

  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
        const res = await fetch(`${apiUrl}/companies/`);
        if (res.ok) {
          const data = await res.json();
          setCompanies(data);
        }
      } catch (err) {
        console.error("Failed to fetch companies:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchCompanies();
    const interval = setInterval(fetchCompanies, 5000);
    return () => clearInterval(interval);
  }, []);

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
          {loading ? (
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
