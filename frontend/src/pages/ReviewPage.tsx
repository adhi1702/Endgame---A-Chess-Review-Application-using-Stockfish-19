import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Chess } from "chess.js";
import { Chessboard } from "react-chessboard";
import { Activity, ArrowLeft, ArrowLeftRight, ArrowRight, ChevronDown } from "lucide-react";
import { api, Game } from "../api";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function Review({ onLoad }: { onLoad: (id: string) => Promise<Game> }) {
  const { id } = useParams();
  const [game, setGame] = useState<Game | null>(null),
    [idx, setIdx] = useState(0),
    [err, setErr] = useState(""),
    [job, setJob] = useState<any>(null),
    [orientation, setOrientation] = useState<"white" | "black">("white");
  const [explorationBoard, setExplorationBoard] = useState<Chess | null>(null);
  const [explorationAnalysis, setExplorationAnalysis] = useState<any>(null);
  const [explorationPending, setExplorationPending] = useState(false);
  const [explorationError, setExplorationError] = useState("");
  const [boardWidth, setBoardWidth] = useState(620);
  const boardShellRef = useRef<HTMLDivElement>(null);
  const explorationRequest = useRef(0);
  useEffect(() => {
    if (id)
      onLoad(id)
        .then(setGame)
        .catch((e) =>
          setErr(e.response?.data?.detail || "Unable to load this game"),
        );
  }, [id]);
  useEffect(() => {
    const element = boardShellRef.current;
    if (!element) return;
    const measure = () => setBoardWidth(Math.max(200, Math.min(620, element.clientWidth - 45)));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [game]);
  useEffect(() => {
    explorationRequest.current += 1;
    setExplorationBoard(null);
    setExplorationAnalysis(null);
    setExplorationPending(false);
    setExplorationError("");
  }, [idx]);
  useEffect(() => {
    if (!job?.id || ["completed", "failed"].includes(job.status)) return;
    const t = setInterval(
      () =>
        api
          .get(`/analysis-jobs/${job.id}`)
          .then(async (r) => {
            setJob(r.data);
            if (r.data.status === "completed" && id) onLoad(id).then(setGame);
          })
          .catch(() => {}),
      1800,
    );
    return () => clearInterval(t);
  }, [job?.id, job?.status, id]);
  useEffect(() => {
    const onArrow = (event: KeyboardEvent) => {
      if (
        event.altKey ||
        event.ctrlKey ||
        event.metaKey ||
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement
      ) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setIdx((current) => Math.max(0, current - 1));
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        setIdx((current) => Math.min(game?.moves.length ?? 0, current + 1));
      }
    };
    window.addEventListener("keydown", onArrow);
    return () => window.removeEventListener("keydown", onArrow);
  }, [game?.moves.length]);
  const board = useMemo(() => {
    if (!game) return new Chess();
    const c = new Chess(game.initial_fen);
    for (let i = 0; i < idx; i++) {
      try {
        c.move(game.moves[i].san);
      } catch {}
    }
    return c;
  }, [game, idx]);
  if (err)
    return (
      <div className="page">
        <div className="empty">
          <h3>Could not load this game</h3>
          <p>{err}</p>
          <Link to="/games" className="secondary">
            Back to games
          </Link>
        </div>
      </div>
    );
  if (!game)
    return (
      <div className="page">
        <div className="loading">Opening your game…</div>
      </div>
    );
  const selected = game.moves[idx - 1];
  const evaluation = idx === 0
    ? game.moves[0]?.analysis?.evaluation_before ?? null
    : game.moves[idx - 1]?.analysis
      ? (game.moves[idx - 1].color === "white" ? 1 : -1) * game.moves[idx - 1].analysis!.evaluation_after
      : null;
  const evaluationLabel = evaluation === null
    ? "—"
    : `${evaluation >= 0 ? "+" : "−"}${Math.min(Math.abs(evaluation), 99.9).toFixed(1)}`;
  let bestMoveSan = selected?.analysis?.best_move_uci ?? null;
  if (selected?.analysis?.best_move_uci) {
    try {
      const beforeSelected = new Chess(board.fen());
      beforeSelected.undo();
      const uci = selected.analysis.best_move_uci;
      const bestMove = beforeSelected.move({
        from: uci.slice(0, 2),
        to: uci.slice(2, 4),
        promotion: uci[4],
      });
      bestMoveSan = bestMove.san;
    } catch {
      // Keep the UCI move available if it cannot be converted to SAN.
    }
  }
  const playedBestMove = selected?.uci === selected?.analysis?.best_move_uci;
  const shownBoard = explorationBoard ?? board;
  const currentBestMove = explorationBoard
    ? explorationAnalysis?.best_move_uci
    : game.moves[idx]?.analysis?.best_move_uci;
  const customArrows = currentBestMove
    ? [[currentBestMove.slice(0, 2), currentBestMove.slice(2, 4), "#e6b85c"] as [string, string, string]]
    : [];
  const shownEvaluation = explorationBoard
    ? explorationAnalysis?.evaluation ?? null
    : evaluation;
  const shownEvaluationLabel = explorationBoard && explorationPending
    ? "…"
    : shownEvaluation === null
      ? "—"
      : `${shownEvaluation >= 0 ? "+" : "−"}${Math.min(Math.abs(shownEvaluation), 99.9).toFixed(1)}`;
  const shownWhiteAdvantage = shownEvaluation === null
    ? 50
    : 50 + Math.tanh(shownEvaluation / 4) * 50;
  function exploreMove(from: string, to: string) {
    const next = new Chess(shownBoard.fen());
    try {
      const movingPiece = next.get(from as any);
      const promotion = movingPiece?.type === "p" && (to[1] === "1" || to[1] === "8") ? "q" : undefined;
      next.move({ from, to, promotion });
    } catch {
      return false;
    }
    setExplorationBoard(next);
    setExplorationAnalysis(null);
    setExplorationPending(true);
    setExplorationError("");
    const requestId = ++explorationRequest.current;
    api.post(`/games/${id}/position-analysis`, { fen: next.fen() })
      .then(({ data }) => {
        if (requestId !== explorationRequest.current) return;
        setExplorationAnalysis(data);
        setExplorationPending(false);
      })
      .catch((error) => {
        if (requestId !== explorationRequest.current) return;
        setExplorationPending(false);
        setExplorationError(error.response?.data?.detail || "Position analysis failed");
      });
    return true;
  }
  const evalPoints = game.moves
    .filter((m) => m.analysis)
    .map((m) => ({
      ply: m.ply,
      score:
        m.color === "white"
          ? m.analysis!.evaluation_after
          : -m.analysis!.evaluation_after,
    }));
  async function analyze() {
    try {
      const { data } = await api.post(`/games/${id}/analysis`);
      setJob(data);
    } catch (e: any) {
      setJob({
        status: "failed",
        error:
          e.response?.data?.detail ||
          "Unable to start Stockfish. Check the worker and engine setup.",
      });
    }
  }
  return (
    <div className="page review-page">
      <div className="review-top">
        <Link to="/games" className="back-link">
          <ArrowLeft size={15} /> All games
        </Link>
        <div className="review-title">
          <div>
            <div className="eyebrow">GAME REVIEW</div>
            <h1>
              {game.white_player} <span>vs</span> {game.black_player}
            </h1>
            <p>
              {game.event} <span>·</span> {game.played_at || "Date unknown"}{" "}
              <span>·</span> {game.result}
            </p>
          </div>
          <button
            className="primary"
            onClick={analyze}
            disabled={job?.status === "queued" || job?.status === "running"}
          >
            <Activity size={16} />
            {job?.status === "queued" || job?.status === "running"
              ? "Analysis queued"
              : game.analysis_summary || job?.status === "completed"
                ? "Reanalyze game"
                : "Analyze game"}
          </button>
        </div>
      </div>
      <div className="review-layout">
        <section className="board-area">
          <div className="board-meta">
            <span className="side-tag">
              <i className={orientation === "black" ? "white-dot" : ""} />
              {orientation === "white" ? game.black_player : game.white_player}
              <small>({orientation === "white" ? "Black" : "White"})</small>
            </span>
            <button
              className="flip-control"
              onClick={() => setOrientation((current) => current === "white" ? "black" : "white")}
              aria-label="Flip board orientation"
              title="Flip board"
            >
              <ArrowLeftRight size={14} /> Flip board
            </button>
          </div>
          <div className="board-shell" ref={boardShellRef}>
            <div className="eval-track" title="Evaluation from White’s perspective">
              <span className="eval-readout">{shownEvaluationLabel}</span>
              <div className="eval-bar">
                <span style={{ height: `${shownWhiteAdvantage}%` }} />
              </div>
            </div>
            <div className="chessboard">
              <Chessboard
                position={shownBoard.fen()}
                boardOrientation={orientation}
                arePiecesDraggable={true}
                onPieceDrop={exploreMove}
                boardWidth={boardWidth}
                promotionDialogVariant="vertical"
                customArrows={customArrows as any}
                customDarkSquareStyle={{ backgroundColor: "#718b76" }}
                customLightSquareStyle={{ backgroundColor: "#e8e3d5" }}
              />
            </div>
          </div>
          {explorationBoard && (
            <div className="explore-status" aria-live="polite">
              {explorationPending ? "Analyzing this position…" : explorationError || "Exploration position · drag another piece to continue"}
              <button className="text-link" onClick={() => {
                explorationRequest.current += 1;
                setExplorationBoard(null);
                setExplorationAnalysis(null);
                setExplorationPending(false);
                setExplorationError("");
              }}>Return to game</button>
            </div>
          )}
          <div className="board-meta">
            <span className="side-tag">
              <i className={orientation === "white" ? "white-dot" : ""} />
              {orientation === "white" ? game.white_player : game.black_player}{" "}
              <small>({orientation === "white" ? "White" : "Black"})</small>
            </span>
            <span className="rating-placeholder">—</span>
          </div>
          <div className="board-controls">
            <button
              className="control-btn"
              onClick={() => setIdx(0)}
              title="Start"
            >
              |◀
            </button>
            <button
              className="control-btn"
              onClick={() => setIdx((current) => Math.max(0, current - 1))}
              disabled={idx === 0}
              title="Previous move (←)"
              aria-label="Previous move"
            >
              ◀
            </button>
            <span>
              {idx === 0
                ? "Starting position"
                : `After ${game.moves[idx - 1].san} · ${Math.ceil(idx / 2)}.${idx % 2 ? " Black" : " White"} to move`}
            </span>
            <button
              className="control-btn"
              onClick={() => setIdx((current) => Math.min(game.moves.length, current + 1))}
              disabled={idx === game.moves.length}
              title="Next move (→)"
              aria-label="Next move"
            >
              ▶
            </button>
            <button
              className="control-btn"
              onClick={() => setIdx(game.moves.length)}
              title="End"
            >
              ▶|
            </button>
          </div>
          <div className="panel eval-panel">
            <div className="panel-head">
              <div>
                <div className="eyebrow">POSITION EVALUATION</div>
                <h3>Evaluation over time</h3>
              </div>
              <span className="depth-tag">
                {selected?.analysis
                  ? `Depth ${job?.depth || "—"}`
                  : evalPoints.length
                    ? "Analysis complete"
                    : "Analysis needed"}
              </span>
            </div>
            {evalPoints.length ? (
              <ResponsiveContainer width="100%" height={120}>
                <LineChart
                  data={evalPoints}
                  margin={{ top: 10, right: 8, left: -22, bottom: 0 }}
                >
                  <CartesianGrid stroke="#29332f" strokeDasharray="3 4" />
                  <XAxis
                    dataKey="ply"
                    tick={{ fill: "#75827c", fontSize: 9 }}
                    tickLine={false}
                    axisLine={{ stroke: "#39443e" }}
                  />
                  <YAxis
                    tick={{ fill: "#75827c", fontSize: 9 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#151e19",
                      border: "1px solid #38483d",
                      borderRadius: 5,
                      fontSize: 10,
                    }}
                    formatter={(v: number) => [
                      `${v > 0 ? "+" : ""}${v.toFixed(2)}`,
                      "White eval",
                    ]}
                  />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#9cbea2"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="chart-empty">
                Evaluation chart appears after a game is analyzed.
              </div>
            )}
          </div>
        </section>
        <aside className="review-side">
          <div className="panel moves-panel">
            <div className="panel-head">
              <div>
                <div className="eyebrow">MOVES</div>
                <h3>
                  Move list{" "}
                  <span className="muted">({game.moves.length} plies)</span>
                </h3>
              </div>
              <button className="icon-btn">
                <ChevronDown size={16} />
              </button>
            </div>
            <div className="moves-list">
              {Array.from(
                { length: Math.ceil(game.moves.length / 2) },
                (_, row) => {
                  const w = game.moves[row * 2],
                    b = game.moves[row * 2 + 1];
                  return (
                    <div className="move-row" key={row}>
                      <span className="move-no">{row + 1}.</span>
                      <button
                        className={idx === w.ply ? "move-san active" : ""}
                        title={w.analysis ? `${w.san} · ${w.analysis.classification}` : w.san}
                        onClick={() => setIdx(w.ply)}
                      >
                        {w.san}
                        {w.analysis && (
                          <span className={`move-quality-label ${w.analysis.classification.toLowerCase()}`}>
                            {w.analysis.classification}
                          </span>
                        )}
                      </button>
                      {b && (
                        <button
                          className={idx === b.ply ? "move-san active" : ""}
                          title={b.analysis ? `${b.san} · ${b.analysis.classification}` : b.san}
                          onClick={() => setIdx(b.ply)}
                        >
                          {b.san}
                          {b.analysis && (
                            <span className={`move-quality-label ${b.analysis.classification.toLowerCase()}`}>
                              {b.analysis.classification}
                            </span>
                          )}
                        </button>
                      )}
                    </div>
                  );
                },
              )}
            </div>
            <div className="move-legend">
              {["Book", "Brilliant", "Great", "Best", "Excellent", "Good", "Miss", "Inaccuracy", "Mistake", "Blunder"].map((label) => (
                <span key={label}>
                  <i className={`quality ${label.toLowerCase()}`} /> {label}
                </span>
              ))}
            </div>
          </div>
          <div className="panel engine-analysis">
            <div className="engine-head">
              <span className="engine-icon small-engine">
                <Activity size={16} />
              </span>
              <div>
                <div className="eyebrow">STOCKFISH</div>
                <h3>Engine analysis</h3>
              </div>
              <span className="green-dot" />
            </div>
            {job && (
              <div className="job-state">
                {job.status === "queued"
                  ? "Analysis queued · starting shortly…"
                  : job.status === "running"
                    ? job.progress
                      ? `Analyzing · ${job.progress}%`
                      : "Starting Stockfish…"
                    : job.status === "completed"
                      ? "Analysis complete"
                      : job.error || job.error_message}
              </div>
            )}
            <div className="analysis-content">
              {explorationBoard ? (
                explorationPending ? (
                  <div className="analysis-empty">Stockfish is evaluating your position…</div>
                ) : explorationError ? (
                  <div className="analysis-empty">{explorationError}</div>
                ) : explorationAnalysis ? (
                  <>
                    <div className="eval-score">
                      {shownEvaluationLabel}
                      <span>White eval · explored position</span>
                    </div>
                    <div className="best-move missed-best">
                      <div className="move-comparison-side recommended">
                        <span>STOCKFISH BEST · FOLLOW THE ARROW</span>
                        <b>{explorationAnalysis.best_move_uci || "Game over"}</b>
                      </div>
                    </div>
                    <div className="pv">
                      <span>PRINCIPAL VARIATION</span>
                      <b>{explorationAnalysis.principal_variation?.join(" ") || "—"}</b>
                    </div>
                  </>
                ) : (
                  <div className="analysis-empty">Make a legal move to analyze this position.</div>
                )
              ) : selected?.analysis ? (
                <>
                  <div className="eval-score">
                    {evaluationLabel}
                    <span>White eval after {selected.san}</span>
                  </div>
                  <div className={`best-move ${playedBestMove ? "played-best" : "missed-best"}`}>
                    <div className="move-comparison-side">
                      <span>PLAYED</span>
                      <b>{selected.san}</b>
                    </div>
                    {!playedBestMove && (
                      <>
                        <ArrowRight size={14} />
                        <div className="move-comparison-side recommended">
                          <span>STOCKFISH BEST</span>
                          <b>{bestMoveSan || "—"}</b>
                        </div>
                      </>
                    )}
                    <i
                      className={`quality ${selected.analysis.classification.toLowerCase()}`}
                    />
                    <small>{playedBestMove ? "Best move" : selected.analysis.classification}</small>
                  </div>
                  <div className="pv">
                    <span>PRINCIPAL VARIATION</span>
                    <b>
                      {selected.analysis.principal_variation.join(" ") || "—"}
                    </b>
                  </div>
                </>
              ) : (
                <div className="analysis-empty">
                  <span className="analysis-spark">✳</span>
                  <p>
                    {job?.status === "completed"
                      ? "Select a move to inspect its evaluation and best continuation."
                      : "Run Stockfish to uncover the best lines and turning points in this game."}
                  </p>
                  {(!job || job.status === "failed") && (
                    <button className="secondary full" onClick={analyze}>
                      <Activity size={15} /> Start analysis
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="accuracy-panel">
            <div className="accuracy-heading">
              <span>PLAYER ACCURACY</span>
              {!game.analysis_summary && <small>Available after analysis completes</small>}
            </div>
            <div>
              <span>WHITE ACCURACY</span>
              <b>
                {game.analysis_summary?.accuracy_white == null
                  ? "—"
                  : `${game.analysis_summary.accuracy_white}%`}
              </b>
            </div>
            <div>
              <span>BLACK ACCURACY</span>
              <b>
                {game.analysis_summary?.accuracy_black == null
                  ? "—"
                  : `${game.analysis_summary.accuracy_black}%`}
              </b>
            </div>
            <p>
              Review scores summarize move quality and are not official chess
              ratings.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
