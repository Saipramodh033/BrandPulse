"use client";

import { useEffect, useState, use } from "react";
import { API_URL } from "@/lib/api";
import styles from "./memory.module.css";

interface AngleCoverage {
  id: string;
  category: string;
  sub_angle: string;
  is_wildcard: boolean;
  idea_count: number;
  approved_count: number;
  status: "used" | "unused";
}

export default function CompanyMemory({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [angles, setAngles] = useState<AngleCoverage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/companies/${id}/angles`)
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) setAngles(data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  const usedAngles = angles.filter(a => a.status === 'used' && !a.is_wildcard);
  const unusedAngles = angles.filter(a => a.status === 'unused');
  const wildcards = angles.filter(a => a.is_wildcard);
  const totalUsed = usedAngles.length + wildcards.length;
  const totalAngles = angles.length;
  const coverage = totalAngles > 0 ? Math.round((totalUsed / totalAngles) * 100) : 0;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>Content Angle Memory</h2>
          <p className={styles.subtitle}>Which angles have been explored — and which are still opportunities.</p>
        </div>
        <div className={styles.coverageSummary}>
          <div className={styles.coverageNum}>{coverage}%</div>
          <div className={styles.coverageLabel}>Coverage</div>
          <div className={styles.coverageSub}>{totalUsed} / {totalAngles} angles explored</div>
        </div>
      </header>

      {/* Coverage bar */}
      <div className={styles.coverageBar}>
        <div className={styles.coverageFill} style={{ width: `${coverage}%` }} />
      </div>

      {loading ? (
        <div className={styles.loading}>Loading angle memory...</div>
      ) : (
        <>
          {/* Opportunity section: unused angles */}
          {unusedAngles.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                <span className={styles.sectionDot} style={{ background: 'var(--accent-base)' }} />
                Unexplored Opportunities ({unusedAngles.length})
              </h3>
              <div className={styles.angleGrid}>
                {unusedAngles.map(angle => (
                  <div key={angle.id} className={`${styles.angleCard} ${styles.angleUnused}`}>
                    <div className={styles.angleCategory}>{angle.category}</div>
                    <div className={styles.angleStatus}>Never Used</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Used angles */}
          {usedAngles.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                <span className={styles.sectionDot} style={{ background: 'var(--status-success)' }} />
                Used Angles ({usedAngles.length})
              </h3>
              <div className={styles.angleGrid}>
                {usedAngles.map(angle => {
                  const winRate = angle.idea_count > 0 ? Math.round((angle.approved_count / angle.idea_count) * 100) : 0;
                  return (
                    <div key={angle.id} className={`${styles.angleCard} ${styles.angleUsed}`}>
                      <div className={styles.angleCategory}>{angle.category}</div>
                      {angle.sub_angle && angle.sub_angle !== angle.category && (
                        <div className={styles.angleDetail}>{angle.sub_angle}</div>
                      )}
                      <div className={styles.angleStats}>
                        <span>{angle.idea_count} ideas</span>
                        <span className={styles.winRate}>{winRate}% approved</span>
                      </div>
                      <div className={styles.miniBar}>
                        <div className={styles.miniBarFill} style={{ width: `${winRate}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* Wildcards */}
          {wildcards.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                <span className={styles.sectionDot} style={{ background: '#a78bfa' }} />
                Wildcard Angles ({wildcards.length})
              </h3>
              <div className={styles.angleGrid}>
                {wildcards.map(angle => {
                  const winRate = angle.idea_count > 0 ? Math.round((angle.approved_count / angle.idea_count) * 100) : 0;
                  return (
                    <div key={angle.id} className={`${styles.angleCard} ${styles.angleWild}`}>
                      <div className={styles.angleCategory}>{angle.category}</div>
                      {angle.sub_angle && angle.sub_angle !== angle.category && (
                        <div className={styles.angleDetail}>{angle.sub_angle}</div>
                      )}
                      <div className={styles.angleStats}>
                        <span>{angle.idea_count} ideas</span>
                        <span className={styles.winRate}>{winRate}% approved</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {angles.length === 0 && (
            <div className={styles.empty}>No angle data yet. Run ideation to populate angle memory.</div>
          )}
        </>
      )}
    </div>
  );
}
