/**
 * DocuMind AI — Application Shell
 *
 * Minimal homepage. No fake data, no placeholder dashboard.
 * Full UI implementation comes in the feature development phases.
 */
export default function HomePage() {
  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        gap: "var(--space-4)",
        padding: "var(--space-8)",
        backgroundColor: "var(--bg-base)",
        color: "var(--text-primary)",
      }}
    >
      {/* Wordmark */}
      <h1
        style={{
          fontSize: "var(--text-2xl)",
          fontWeight: 600,
          letterSpacing: "-0.025em",
          margin: 0,
          color: "var(--text-primary)",
        }}
      >
        DocuMind AI
      </h1>

      {/* Tagline */}
      <p
        style={{
          fontSize: "var(--text-sm)",
          color: "var(--text-muted)",
          margin: 0,
          textAlign: "center",
          maxWidth: "400px",
          lineHeight: 1.6,
        }}
      >
        Multimodal document intelligence.
      </p>

      {/* Status badge */}
      <span
        style={{
          marginTop: "var(--space-6)",
          fontSize: "var(--text-xs)",
          fontFamily: "var(--font-mono)",
          color: "var(--text-muted)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-sm)",
          padding: "var(--space-1) var(--space-3)",
          letterSpacing: "0.05em",
        }}
      >
        scaffold — product functionality not yet implemented
      </span>
    </main>
  );
}
