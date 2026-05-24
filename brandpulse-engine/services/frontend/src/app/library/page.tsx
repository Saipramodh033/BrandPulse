"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";
import styles from "./library.module.css";
import { Copy, Check, Search } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface Idea {
  id: number;
  hook: string;
  body: string;
  cta: string;
  platform: string;
  implication_type: string;
  angle_category: string;
  angle_detail: string;
  signal_used: string;
  status: string;
  created_at: string;
  company_id?: number;
}

interface Company {
  id: number;
  name: string;
}

const PLATFORMS = ["all", "linkedin", "twitter", "instagram"];

export default function LibraryView() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [platformFilter, setPlatformFilter] = useState("all");
  const [companyFilter, setCompanyFilter] = useState<number | null>(null);

  useEffect(() => {
    // B2 Fix: trailing slash required by FastAPI router prefix
    fetch(`${API_URL}/ideas/?status=approved`)
      .then(r => r.json())
      .then(data => { if (Array.isArray(data)) setIdeas(data); })
      .catch(console.error);

    fetch(`${API_URL}/companies/`)
      .then(r => r.json())
      .then(data => { if (Array.isArray(data)) setCompanies(data); })
      .catch(console.error);
  }, []);

  const copyToClipboard = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filtered = ideas.filter(idea => {
    const matchSearch = !search || `${idea.hook} ${idea.body} ${idea.cta}`.toLowerCase().includes(search.toLowerCase());
    const matchPlatform = platformFilter === 'all' || idea.platform === platformFilter;
    const matchCompany = companyFilter === null || idea.company_id === companyFilter;
    return matchSearch && matchPlatform && matchCompany;
  });

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Approved Library</h1>
          <p className={styles.subtitle}>
            {ideas.length} approved idea{ideas.length !== 1 ? 's' : ''} ready to publish.
          </p>
        </div>
      </header>

      {/* Filter bar */}
      <div className={styles.filterBar}>
        <div className={styles.searchBox}>
          <Search size={14} className={styles.searchIcon} />
          <input
            className={styles.searchInput}
            placeholder="Search ideas..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className={styles.filterGroup}>
          {PLATFORMS.map(p => (
            <button
              key={p}
              className={`${styles.filterChip} ${platformFilter === p ? styles.chipActive : ''}`}
              onClick={() => setPlatformFilter(p)}
            >
              {p === 'all' ? 'All Platforms' : p}
            </button>
          ))}
        </div>

        {companies.length > 1 && (
          <div className={styles.filterGroup}>
            <button
              className={`${styles.filterChip} ${companyFilter === null ? styles.chipActive : ''}`}
              onClick={() => setCompanyFilter(null)}
            >
              All Companies
            </button>
            {companies.map(c => (
              <button
                key={c.id}
                className={`${styles.filterChip} ${companyFilter === c.id ? styles.chipActive : ''}`}
                onClick={() => setCompanyFilter(c.id)}
              >
                {c.name}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className={styles.grid}>
        <AnimatePresence>
          {filtered.length === 0 ? (
            <div className={styles.emptyState}>
              {ideas.length === 0 ? 'No approved ideas yet. Approve ideas from the Inbox.' : 'No results match your filters.'}
            </div>
          ) : (
            filtered.map(idea => (
              <motion.div
                key={idea.id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.97 }}
                className={`${styles.card} glass-panel`}
              >
                <div className={styles.cardHeader}>
                  <div className={styles.metaRow}>
                    <span className={styles.tag}>{idea.platform}</span>
                    {idea.implication_type && <span className={styles.tag}>{idea.implication_type}</span>}
                    {idea.angle_category && <span className={styles.tagAngle}>{idea.angle_category}</span>}
                  </div>
                  <button
                    className={styles.copyBtn}
                    onClick={() => copyToClipboard(`${idea.hook}\n\n${idea.body}\n\n${idea.cta}`, idea.id)}
                    title="Copy to clipboard"
                  >
                    {copiedId === idea.id ? <Check size={14} color="var(--status-success)" /> : <Copy size={14} />}
                  </button>
                </div>

                <div className={styles.content}>
                  <p className={styles.hook}>{idea.hook}</p>
                  <p className={styles.body}>{idea.body}</p>
                  <p className={styles.cta}>{idea.cta}</p>
                </div>

                {idea.signal_used && idea.signal_used !== 'evergreen' && (
                  <div className={styles.signalPill}>
                    Signal: {idea.signal_used.length > 80 ? idea.signal_used.substring(0, 80) + '…' : idea.signal_used}
                  </div>
                )}
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
