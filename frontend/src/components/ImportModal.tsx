import { useState } from "react";
import { ArrowRight, CloudUpload, FileText, ShieldCheck, X } from "lucide-react";

const sample =
  '[Event "Casual Game"]\n[Site "Local"]\n[Date "2026.11.24"]\n[White "Mira Chen"]\n[Black "You"]\n[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 *';

export function ImportModal({
  onClose,
  onImport,
  loading,
}: {
  onClose: () => void;
  onImport: (p: string) => void;
  loading: boolean;
}) {
  const [text, setText] = useState(sample),
    [tab, setTab] = useState("paste"),
    [fileName, setFileName] = useState("");
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-heading">
          <div>
            <div className="eyebrow">ADD TO YOUR LIBRARY</div>
            <h2>Bring in a game</h2>
          </div>
          <button className="icon-btn" onClick={onClose}>
            <X />
          </button>
        </div>
        <p className="modal-intro">
          Paste a PGN or upload a file. We’ll check the moves before saving.
        </p>
        <div className="tabs">
          <button
            className={tab === "paste" ? "selected" : ""}
            onClick={() => setTab("paste")}
          >
            <FileText size={15} /> Paste PGN
          </button>
          <button
            className={tab === "upload" ? "selected" : ""}
            onClick={() => setTab("upload")}
          >
            <CloudUpload size={15} /> Upload file
          </button>
        </div>
        {tab === "paste" ? (
          <textarea
            className="pgn-input"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={
              '[Event "Casual Game"]\n[White "Player 1"]\n[Black "Player 2"]\n\n1. e4 e5 ...'
            }
          />
        ) : (
          <label className="file-drop">
            <input
              type="file"
              accept=".pgn,.txt"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (f) {
                  setFileName(f.name);
                  setText(await f.text());
                }
              }}
            />
            <CloudUpload size={25} />
            <b>{fileName || "Choose a PGN file"}</b>
            <span>PGN or TXT, up to 500 KB</span>
          </label>
        )}
        <div className="modal-footer">
          <span>
            <ShieldCheck size={15} /> Your games stay private
          </span>
          <button
            className="primary"
            disabled={loading || !text.trim()}
            onClick={() => onImport(text)}
          >
            {loading ? "Validating…" : "Import game"} <ArrowRight size={15} />
          </button>
        </div>
      </div>
    </div>
  );
}
