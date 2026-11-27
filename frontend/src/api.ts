import axios from "axios";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api",
  withCredentials: true,
});
api.interceptors.request.use((config) => {
  const method = (config.method || "get").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrfName = `${import.meta.env.VITE_CSRF_COOKIE_NAME || "stockfish_review_csrf"}=`;
    const cookie = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith(csrfName));
    if (cookie) config.headers["X-CSRF-Token"] = decodeURIComponent(cookie.slice(csrfName.length));
    else config.headers["X-CSRF-Token"] = "";
  }
  return config;
});
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 401 &&
      !String(error.config?.url || "").includes("/auth/me") &&
      !String(error.config?.url || "").includes("/auth/") &&
      !String(error.config?.url || "").includes("/users/profile")
    ) {
      window.dispatchEvent(new Event("chess-auth-expired"));
    }
    if (error.response?.status === 403 && String(error.response?.data?.detail || "").includes("CSRF")) {
      window.dispatchEvent(new Event("chess-csrf-refresh"));
    }
    return Promise.reject(error);
  },
);
export type MoveRow = {
  id: string;
  ply: number;
  move_number: number;
  color: string;
  san: string;
  uci: string;
  fen_after: string;
  analysis?: {
    evaluation_before: number;
    evaluation_after: number;
    centipawn_loss: number;
    classification: string;
    best_move_uci: string;
    principal_variation: string[];
  } | null;
};
export type Game = {
  id: string;
  white_player: string;
  black_player: string;
  result: string;
  event: string;
  played_at: string | null;
  initial_fen: string;
  analysis_summary?: {
    accuracy_white: number | null;
    accuracy_black: number | null;
    inaccuracies: number;
    mistakes: number;
    blunders: number;
  } | null;
  moves: MoveRow[];
  move_count?: number;
  source?: string;
  user_color?: string | null;
  white_rating?: number | null;
  black_rating?: number | null;
  opening_name?: string | null;
  eco_code?: string | null;
  time_control?: string | null;
};
