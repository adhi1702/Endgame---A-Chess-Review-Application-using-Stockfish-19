import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  ArrowLeftRight,
  ArrowRight,
  BookOpen,
  FileText,
  Plus,
  ShieldCheck,
  Target,
  Upload,
} from "lucide-react";
import { api, Game } from "../api";
import { StatCard } from "../components/StatCard";

export function Dashboard({
  games,
  onImport,
  onSelect,
}: {
  games: Game[];
  onImport: () => void;
  onSelect: (id: string) => void;
}) {
  const [averageAccuracy, setAverageAccuracy] = useState<number | null>(null);
  useEffect(() => {
    api
      .get("/v1/analytics")
      .then(({ data }) => setAverageAccuracy(data.average_accuracy))
      .catch(() => {});
  }, []);
  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">MONDAY, NOVEMBER 24, 2026</div>
          <h1>
            Your chess, <em>in focus.</em>
          </h1>
          <p>A clear view of your progress, one move at a time.</p>
        </div>
        <button className="primary" onClick={onImport}>
          <Plus size={17} /> Review a game
        </button>
      </div>
      <section className="stats-grid">
        <StatCard
          icon={<BookOpen />}
          label="Games reviewed"
          value={String(games.length).padStart(2, "0")}
          change="Your full archive"
        />
        <StatCard
          icon={<Target />}
          label="Wins"
          value={String(
            games.filter((g) => g.result === "1-0").length,
          ).padStart(2, "0")}
          change="Keep building momentum"
        />
        <StatCard
          icon={<ArrowLeftRight />}
          label="Draws"
          value={String(
            games.filter((g) => g.result === "1/2-1/2").length,
          ).padStart(2, "0")}
          change="Hard fought games"
        />
        <StatCard
          icon={<Activity />}
          label="Average accuracy"
          value={averageAccuracy == null ? "—" : `${averageAccuracy}%`}
          change="Average across analyzed games"
        />
      </section>
      <section className="panel recent-panel">
        <div className="panel-head">
          <div>
            <div className="eyebrow">YOUR LIBRARY</div>
            <h2>Recent games</h2>
          </div>
          <Link className="text-link" to="/games">
            View all games <ArrowRight size={15} />
          </Link>
        </div>
        {games.length ? (
          <div className="game-table">
            <div className="table-row table-labels">
              <span>GAME</span>
              <span>RESULT</span>
              <span>MOVES</span>
              <span>DATE</span>
              <span></span>
            </div>
            {games.slice(0, 6).map((g) => (
              <div
                className="table-row"
                key={g.id}
                onClick={() => onSelect(g.id)}
              >
                <span className="game-names">
                  <i className="piece-dot">♞</i>
                  <span>
                    <b>{g.white_player}</b>
                    <small>vs {g.black_player}</small>
                  </span>
                </span>
                <span className="result-chip">{g.result}</span>
                <span>{g.move_count}</span>
                <span>{g.played_at || "—"}</span>
                <span>
                  <ArrowRight size={16} />
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty">
            <div className="empty-icon">
              <FileText />
            </div>
            <h3>A fresh board awaits</h3>
            <p>
              Import a PGN and start understanding the moments that shaped your
              games.
            </p>
            <button className="secondary" onClick={onImport}>
              <Upload size={16} /> Import your first game
            </button>
          </div>
        )}
      </section>
      <div className="bottom-grid">
        <section className="panel insight">
          <div className="eyebrow">YOUR NEXT STEP</div>
          <h2>Build a clearer picture.</h2>
          <p>
            Analyze a game to see your move quality, key turning points and the
            lines you missed.
          </p>
          <button className="quiet" onClick={onImport}>
            Get started <ArrowRight size={15} />
          </button>
        </section>
        <section className="panel engine-card">
          <span className="engine-icon">
            <ShieldCheck />
          </span>
          <div>
            <div className="eyebrow">LOCAL ENGINE</div>
            <h3>Private by design</h3>
            <p>
              Stockfish analysis runs on your own machine. Your games stay
              yours.
            </p>
          </div>
          <span className="green-dot" />
        </section>
      </div>
    </div>
  );
}
