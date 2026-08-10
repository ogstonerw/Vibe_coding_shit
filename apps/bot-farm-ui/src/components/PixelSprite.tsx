import type { SpriteKind } from "../domain/botFarm";

const palettes: Record<
  SpriteKind,
  { skin: string; hair: string; shirt: string; accent: string; trousers: string }
> = {
  courier: { skin: "#f1bd83", hair: "#4a2b20", shirt: "#3677a8", accent: "#93d5eb", trousers: "#24445d" },
  merchant: { skin: "#d99967", hair: "#251a16", shirt: "#a64b32", accent: "#f0c262", trousers: "#513122" },
  trainee: { skin: "#efbd82", hair: "#e6b248", shirt: "#5d8c42", accent: "#d8e26d", trousers: "#3f5430" },
  guardian: { skin: "#c98d62", hair: "#211a1a", shirt: "#34475b", accent: "#8ba3af", trousers: "#252f3b" },
  mechanic: { skin: "#e5aa78", hair: "#6c3e8c", shirt: "#536f89", accent: "#ddb35c", trousers: "#303d4c" },
  reviewer: { skin: "#edb77d", hair: "#b15a2e", shirt: "#507b46", accent: "#f0d58b", trousers: "#384d32" },
  owner: { skin: "#efb97f", hair: "#6b3b24", shirt: "#6f9142", accent: "#f0c75f", trousers: "#3c4f31" },
};

interface PixelSpriteProps {
  kind: SpriteKind;
  label?: string;
  size?: "small" | "medium" | "large";
  decorative?: boolean;
}

function Headwear({ kind }: { kind: SpriteKind }) {
  if (kind === "courier") {
    return <><path d="M8 7h16v4H8z" fill="#265b88" /><path d="M20 10h8v3h-8z" fill="#93d5eb" /></>;
  }
  if (kind === "trainee") {
    return <><path d="M9 5h4v3H9zM13 3h5v5h-5zM18 5h5v4h-5z" fill="#f0c65c" /></>;
  }
  if (kind === "guardian") {
    return <path d="M8 5h16v5H8zM6 9h20v3H6z" fill="#20222a" />;
  }
  if (kind === "mechanic") {
    return <><path d="M7 7h4V4h4v3h4V3h4v5h3v4H7z" fill="#75469a" /></>;
  }
  if (kind === "reviewer") {
    return <><path d="M7 6h5V3h7v2h5v7H7z" fill="#b45c30" /><path d="M9 13h6v3H9zM18 13h6v3h-6z" fill="none" stroke="#30221c" strokeWidth="2" /></>;
  }
  if (kind === "owner") {
    return <><path d="M7 6h18v5H7z" fill="#d6a13b" /><path d="M10 3h12v5H10z" fill="#edc960" /></>;
  }
  return <path d="M7 5h18v8H7zM5 9h4v5H5z" fill="#2b211e" />;
}

function Tool({ kind, accent }: { kind: SpriteKind; accent: string }) {
  switch (kind) {
    case "courier":
      return <><rect x="22" y="22" width="7" height="10" fill="#27394b" /><rect x="23" y="23" width="5" height="6" fill={accent} /></>;
    case "merchant":
      return <><rect x="2" y="25" width="8" height="7" fill="#8b5a2f" /><path d="M2 27h8M5 25v7" stroke="#d7a65d" strokeWidth="1" /></>;
    case "trainee":
      return <><path d="M25 18h2v15h-2z" fill="#e5dcc2" /><path d="M22 20h8v2h-8z" fill="#9b6e34" /></>;
    case "guardian":
      return <><path d="M22 20h8v9l-4 5-4-5z" fill="#8da5b1" /><path d="M25 22h2v8h-2zM23 25h6v2h-6z" fill="#e1c66f" /></>;
    case "mechanic":
      return <><path d="M24 19h3v15h-3z" fill="#aab9bd" /><path d="M21 18h9v4h-3v3h-3v-3h-3z" fill="#d6b35f" /></>;
    case "reviewer":
      return <><rect x="22" y="21" width="8" height="11" fill="#f0ddb1" /><path d="M24 24h4M24 27h4" stroke="#7b5938" strokeWidth="1" /></>;
    case "owner":
      return <><path d="M23 22h7v8h-7z" fill="#a8b86b" /><path d="M25 20h3v4h-3zM21 27h4" stroke="#5e7838" strokeWidth="2" /></>;
  }
}

export function PixelSprite({ kind, label, size = "medium", decorative = false }: PixelSpriteProps) {
  const colors = palettes[kind];
  return (
    <svg
      className={`pixel-sprite pixel-sprite--${size} pixel-sprite--${kind}`}
      viewBox="0 0 32 40"
      shapeRendering="crispEdges"
      role={decorative ? undefined : "img"}
      aria-hidden={decorative || undefined}
      aria-label={decorative ? undefined : label ?? kind}
    >
      <ellipse cx="16" cy="38" rx="11" ry="2" fill="#24331e" opacity="0.35" />
      <Headwear kind={kind} />
      <rect x="8" y="10" width="16" height="12" fill={colors.skin} />
      <rect x="6" y="12" width="3" height="7" fill={colors.hair} />
      <rect x="23" y="12" width="3" height="7" fill={colors.hair} />
      <rect x="11" y="14" width="3" height="3" fill="#2c2622" />
      <rect x="19" y="14" width="3" height="3" fill="#2c2622" />
      <rect x="14" y="19" width="5" height="2" fill="#9f5d4d" />
      <rect x="7" y="22" width="18" height="11" fill={colors.shirt} />
      <rect x="5" y="23" width="3" height="8" fill={colors.skin} />
      <rect x="24" y="23" width="3" height="8" fill={colors.skin} />
      <path d="M10 22h12v4H10z" fill={colors.accent} />
      <rect x="9" y="33" width="6" height="5" fill={colors.trousers} />
      <rect x="18" y="33" width="6" height="5" fill={colors.trousers} />
      <rect x="7" y="37" width="8" height="2" fill="#35251e" />
      <rect x="18" y="37" width="8" height="2" fill="#35251e" />
      <Tool kind={kind} accent={colors.accent} />
    </svg>
  );
}
