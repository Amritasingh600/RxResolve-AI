// Human-in-the-loop disclaimer shown on every page.
export default function Disclaimer({ compact = false }) {
  return (
    <div className={`disclaimer ${compact ? "compact" : ""}`} role="note">
      <strong>Human review required.</strong> RxResolveAI provides AI-assisted administrative guidance. All
      recommendations and generated documents must be reviewed by authorized staff before use. This demo system does
      not diagnose, prescribe, make coverage decisions or submit anything to insurers.
    </div>
  );
}
