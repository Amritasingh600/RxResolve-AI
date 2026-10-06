import { useRef, useState } from "react";

const ACCEPT = ".pdf,.txt,.docx";
const MAX_BYTES = 5 * 1024 * 1024;

// A file picker with client-side checks. The backend validates again.
export default function FileUpload({ label = "Upload document", onUpload, busy = false }) {
  const inputRef = useRef(null);
  const [localError, setLocalError] = useState("");

  function handleChange(event) {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow picking the same file again
    if (!file) return;

    const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (![".pdf", ".txt", ".docx"].includes(extension)) {
      setLocalError("Only PDF, TXT and DOCX files are allowed.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setLocalError("File is too large. Maximum size is 5 MB.");
      return;
    }
    setLocalError("");
    onUpload(file);
  }

  return (
    <div className="file-upload">
      <input ref={inputRef} type="file" accept={ACCEPT} onChange={handleChange} hidden />
      <button type="button" className="btn btn-secondary" onClick={() => inputRef.current?.click()} disabled={busy}>
        {busy ? "Uploading…" : label}
      </button>
      <span className="muted small">PDF, TXT or DOCX · max 5 MB</span>
      {localError && <div className="field-error">{localError}</div>}
    </div>
  );
}
