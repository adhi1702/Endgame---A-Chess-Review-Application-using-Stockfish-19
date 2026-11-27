import { useEffect, useState } from "react";
import { Activity, ArrowLeftRight, BookOpen, Target } from "lucide-react";
import { api } from "../api";
import { StatCard } from "../components/StatCard";

export function StatisticsPage() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    Promise.all([
      api.get("/v1/analytics"),
      api.get("/v1/analytics/performance"),
    ])
      .then(([summary, performance]) =>
        setData({ ...summary.data, ...performance.data }),
      )
      .catch(() => setData({ error: "Could not load statistics." }));
  }, []);
  return (
    <section className="page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">YOUR PROGRESS</div>
          <h1>Statistics</h1>
          <p>Results, review coverage, and your game patterns.</p>
        </div>
      </div>
      {data?.error ? (
        <div className="auth-error">{data.error}</div>
      ) : (
        <>
          <section className="stats-grid">
            <StatCard
              icon={<BookOpen />}
              label="Total games"
              value={String(data?.total_games ?? "—")}
              change="In your library"
            />
            <StatCard
              icon={<Activity />}
              label="Reviewed games"
              value={String(data?.reviewed_games ?? "—")}
              change="With completed analysis"
            />
            <StatCard
              icon={<Target />}
              label="Average accuracy"
              value={
                data?.average_accuracy == null
                  ? "—"
                  : `${data.average_accuracy}%`
              }
              change="From completed reviews"
            />
            <StatCard
              icon={<ArrowLeftRight />}
              label="Wins / draws / losses"
              value={
                data
                  ? `${data.results.wins} / ${data.results.draws} / ${data.results.losses}`
                  : "—"
              }
              change="Your results"
            />
          </section>
          <section className="panel settings-card">
            <h2>Monthly performance</h2>
            {(data?.monthly || []).length ? (
              data.monthly.map((row: any) => (
                <div className="stat-change" key={row.month}>
                  {row.month}: {row.games} games · {row.wins} wins · {row.draws}{" "}
                  draws · {row.losses} losses
                </div>
              ))
            ) : (
              <p>Monthly performance will appear after you import games.</p>
            )}
            <h2>Most frequent opponents</h2>
            {(data?.opponents || []).length ? (
              data.opponents.map((row: any) => (
                <div className="stat-change" key={row.name}>
                  {row.name} · {row.games} games
                </div>
              ))
            ) : (
              <p>Opponent data will appear with your game history.</p>
            )}
            <h2>Openings</h2>
            {(data?.openings || []).length ? (
              data.openings.map((row: any) => (
                <div className="stat-change" key={row.name}>
                  {row.name} · {row.count}
                </div>
              ))
            ) : (
              <p>
                Opening data will appear when it is available in PGN headers.
              </p>
            )}
          </section>
        </>
      )}
    </section>
  );
}
