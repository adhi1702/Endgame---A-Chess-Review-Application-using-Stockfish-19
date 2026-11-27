import { useState } from "react";
import { ArrowRight, Plus, Trash2, Upload } from "lucide-react";
import { Game } from "../api";

export function Games({
  games,
  onImport,
  onSelect,
  onDelete,
}: {
  games: Game[];
  onImport: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [resultFilter, setResultFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const filtered = games.filter((game) => {
    const matchesText = !query || `${game.white_player} ${game.black_player} ${game.event} ${game.opening_name || ""}`.toLowerCase().includes(query.toLowerCase());
    const userResult = game.result === "1/2-1/2" ? "draw" : ((game.user_color === "white" && game.result === "1-0") || (game.user_color === "black" && game.result === "0-1")) ? "win" : ((game.user_color === "white" && game.result === "0-1") || (game.user_color === "black" && game.result === "1-0")) ? "loss" : "unknown";
    return matchesText && (!resultFilter || userResult === resultFilter) && (!sourceFilter || (game.source || "pgn") === sourceFilter);
  });
  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">GAME LIBRARY</div>
          <h1>Your games</h1>
          <p>Every game is a chance to see something new.</p>
        </div>
        <button className="primary" onClick={onImport}>
          <Plus size={17} /> Import game
        </button>
      </div>
      <section className="panel recent-panel">
  <div className="game-filters"><input aria-label="Search games" placeholder="Search player, opening, event" value={query} onChange={e => setQuery(e.target.value)} /><select value={resultFilter} onChange={e => setResultFilter(e.target.value)}><option value="">All results</option><option value="win">Wins</option><option value="draw">Draws</option><option value="loss">Losses</option></select><select value={sourceFilter} onChange={e => setSourceFilter(e.target.value)}><option value="">All sources</option><option value="pgn">PGN import</option><option value="chesscom">Chess.com</option></select></div>
  <div className="panel-head">
    <div>
      <div className="eyebrow">ARCHIVE</div>
      <h2>{filtered.length} games</h2>
    </div>
  </div>
  {filtered.length ? (
    <div className="game-table">
      <div className="table-row table-labels">
        <span>GAME</span>
        <span>RESULT</span>
        <span>MOVES</span>
        <span>DATE</span>
        <span />
      </div>
      {filtered.map((g) => (
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
          <button
            className="icon-btn delete"
            title="Delete game"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(g.id);
            }}
          >
            <Trash2 size={15} />
          </button>
        </div>
      ))}
    </div>
  ) : (
    <div className="empty">
      <h3>No games yet</h3>
      <p>Import your first PGN game to begin.</p>
      <button className="secondary" onClick={onImport}>
        <Upload size={16} /> Import PGN
      </button>
    </div>
  )}
</section>
    </div>
  );
}
