import { useEffect, useState } from "react";
import { api } from "../api";

export function ProfileEditor({
  onSaved,
}: {
  onSaved: (name: string) => void;
}) {
  const [name, setName] = useState(""),
    [country, setCountry] = useState(""),
    [bio, setBio] = useState(""),
    [status, setStatus] = useState("");
  useEffect(() => {
    api
      .get("/v1/users/profile")
      .then(({ data }) => {
        setName(data.profile.display_name || "");
        setCountry(data.profile.country || "");
        setBio(data.profile.bio || "");
      })
      .catch(() => setStatus("Could not load profile."));
  }, []);
  return (
    <div className="panel settings-card">
      <label>
        Display name
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={100}
        />
      </label>
      <label>
        Country
        <input
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          maxLength={100}
        />
      </label>
      <label>
        Bio
        <textarea
          value={bio}
          onChange={(e) => setBio(e.target.value)}
          maxLength={1000}
        />
      </label>
      <button
        className="primary"
        onClick={async () => {
          try {
            await api.patch("/v1/users/profile", {
              display_name: name,
              country,
              bio,
            });
            onSaved(name);
            setStatus("Profile saved.");
          } catch {
            setStatus("Could not save profile.");
          }
        }}
      >
        {"Save profile"}
      </button>
      {status && <p>{status}</p>}
    </div>
  );
}
