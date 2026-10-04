"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
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

  const { data: angles = [], isLoading: loading, isError } = useQuery<AngleCoverage[]>({
    queryKey: ["company", id, "angles"],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/companies/${id}/angles`);
      if (!res.ok) throw new Error("Failed to fetch angle memory");
      return res.json();
    },
    enabled: !!id,
    staleTime: 5000,
  });

  const usedAngles = angles.filter((a) => a.status === "used" && !a.is_wildcard);
  const unusedAngles = angles.filter((a) => a.status === "unused");
  const wildcards = angles.filter((a) => a.is_wildcard);
  const totalUsed = usedAngles.length + wildcards.length;
  const totalAngles = angles.length;
  const coverage = totalAngles > 0 ? Math.round((totalUsed / totalAngles) * 100) : 0;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>Content Strategy</h2>
          <p className={styles.subtitle}>Track which content themes have been explored — and which are untapped opportunities.</p>
        </div>
        <div className={styles.coverageSummary}>
          <div className={styles.coverageNum}>{coverage}%</div>
          <div className={styles.coverageLabel}>Coverage</div>
          <div className={styles.coverageSub}>{totalUsed} / {totalAngles} themes explored</div>
        </div>
      </header>

      {/* Coverage bar */}
      <div className={styles.coverageBar}>
        <div className={styles.coverageFill} style={{ width: `${coverage}%` }} />
      </div>

      {loading ? (
        <div className={styles.loading}>Loading strategy data…</div>
      ) : isError ? (
        <div className={styles.empty}>Could not load strategy data. Please try refreshing the page.</div>
      ) : (
        <>
          {/* Untapped Themes: unused angles */}
          {unusedAngles.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                <span className={styles.sectionDot} style={{ background: "var(--accent-base)" }} />
                Untapped Themes ({unusedAngles.length})
              </h3>
              <div className={styles.angleGrid}>
                {unusedAngles.map((angle) => (
                  <div key={angle.id} className={`${styles.angleCard} ${styles.angleUnused}`}>
                    <div className={styles.angleCategory}>{angle.category}</div>
                    <div className={styles.angleStatus}>Not yet explored</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Explored Themes */}
          {usedAngles.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                <span className={styles.sectionDot} style={{ background: "var(--status-success)" }} />
                Explored Themes ({usedAngles.length})
              </h3>
              <div className={styles.angleGrid}>
                {usedAngles.map((angle) => {
                  const approvalRate =
                    angle.idea_count > 0
                      ? Math.round((angle.approved_count / angle.idea_count) * 100)
                      : 0;
                  return (
                    <div key={angle.id} className={`${styles.angleCard} ${styles.angleUsed}`}>
                      <div className={styles.angleCategory}>{angle.category}</div>
                      {angle.sub_angle && angle.sub_angle !== angle.category && (
                        <div className={styles.angleDetail}>{angle.sub_angle}</div>
                      )}
                      <div className={styles.angleStats}>
                        <span>{angle.idea_count} ideas</span>
                        <span className={styles.winRate}>{approvalRate}% approval rate</span>
                      </div>
                      <div className={styles.miniBar}>
                        <div className={styles.miniBarFill} style={{ width: `${approvalRate}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* Experimental Themes (wildcards) */}
          {wildcards.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                <span className={styles.sectionDot} style={{ background: "#a78bfa" }} />
                Experimental Themes ({wildcards.length})
              </h3>
              <div className={styles.angleGrid}>
                {wildcards.map((angle) => {
                  const approvalRate =
                    angle.idea_count > 0
                      ? Math.round((angle.approved_count / angle.idea_count) * 100)
                      : 0;
                  return (
                    <div key={angle.id} className={`${styles.angleCard} ${styles.angleWild}`}>
                      <div className={styles.angleCategory}>{angle.category}</div>
                      {angle.sub_angle && angle.sub_angle !== angle.category && (
                        <div className={styles.angleDetail}>{angle.sub_angle}</div>
                      )}
                      <div className={styles.angleStats}>
                        <span>{angle.idea_count} ideas</span>
                        <span className={styles.winRate}>{approvalRate}% approval rate</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {angles.length === 0 && (
            <div className={styles.empty}>No strategy data yet — generate your first batch of ideas to start tracking theme coverage.</div>
          )}
        </>
      )}
    </div>
  );
}
