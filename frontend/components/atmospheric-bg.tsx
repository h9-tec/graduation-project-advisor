export function AtmosphericBg() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 grain"
      style={{
        backgroundImage: `
          radial-gradient(at 0% 0%, color-mix(in srgb, var(--color-accent) 14%, transparent), transparent 50%),
          radial-gradient(at 100% 100%, color-mix(in srgb, var(--color-accent-strong) 10%, transparent), transparent 60%)
        `,
      }}
    />
  );
}
