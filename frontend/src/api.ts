import axios from "axios";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api",
});
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 401 &&
      !String(error.config?.url || "").includes("/auth/")
    ) {
      localStorage.removeItem("token");
      window.dispatchEvent(new Event("chess-auth-expired"));
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
};
