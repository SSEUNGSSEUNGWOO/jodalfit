import type { ReactNode } from "react";
import styles from "./BackgroundC.module.css";

/**
 * 메인 히어로 배경 — 토스식 isometric 메타포 컨베이어.
 * 콘텐츠 영역과 분리하기 위해 호출하는 main에는 충분한 padding-bottom 필요.
 * 컨베이어는 SSR로 한 번 + 무한 루프용 복제 한 번 (총 2회) 렌더링.
 */
export function BackgroundC() {
  return (
    <div className={styles.section} aria-hidden="true">
      <SvgDefs />
      <div className={styles.bg}>
        <Floor />
        <div className={styles.shelf}>
          <div className={styles.trackWrap}>
            <div className={styles.track}>
              {PIECES.map((p, i) => (
                <IsoPiece key={`a-${i}`} piece={p} />
              ))}
              {PIECES.map((p, i) => (
                <IsoPiece key={`b-${i}`} piece={p} dup />
              ))}
            </div>
          </div>
        </div>
        <Twinkles />
      </div>
    </div>
  );
}

type FloatClass = "float1" | "float2" | "float3" | "float4" | "float5" | "float6" | "float7" | "float8";
type ExtraClass = "checkBadge" | "coin";

interface Piece {
  width: number;
  float: FloatClass;
  extra?: ExtraClass;
  render: () => ReactNode;
}

const PIECES: Piece[] = [
  { width: 130, float: "float1", render: () => <FolderStack /> },
  { width: 138, float: "float2", render: () => <ContractStack /> },
  { width: 116, float: "float3", render: () => <Clipboard /> },
  { width: 140, float: "float4", render: () => <BidBox /> },
  { width: 108, float: "float5", render: () => <Stamp /> },
  { width: 96, float: "float6", render: () => <Envelope /> },
  { width: 56, float: "float7", extra: "checkBadge", render: () => <CheckBadge /> },
  { width: 48, float: "float8", extra: "coin", render: () => <Coin /> },
];

function IsoPiece({ piece, dup }: { piece: Piece; dup?: boolean }) {
  const cls = [styles.iso, styles[piece.float], piece.extra && styles[piece.extra]]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} style={{ width: piece.width }} aria-hidden={dup ? "true" : undefined}>
      {piece.render()}
    </div>
  );
}

function SvgDefs() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
      <defs>
        <linearGradient id="bgcPaperTop" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="100%" stopColor="#E7F3EC" />
        </linearGradient>
        <linearGradient id="bgcPaperSide" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#B7D5C2" />
          <stop offset="100%" stopColor="#94BAA3" />
        </linearGradient>
        <linearGradient id="bgcPaperFront" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#CFE3D6" />
          <stop offset="100%" stopColor="#A5C2AF" />
        </linearGradient>

        <linearGradient id="bgcFolderTop" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3F8D5C" />
          <stop offset="100%" stopColor="#1F7541" />
        </linearGradient>
        <linearGradient id="bgcFolderSide" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#155A2D" />
          <stop offset="100%" stopColor="#0B3A1D" />
        </linearGradient>
        <linearGradient id="bgcFolderFront" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1F7541" />
          <stop offset="100%" stopColor="#0F4A26" />
        </linearGradient>

        <linearGradient id="bgcBoxTop" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#9CC3A9" />
          <stop offset="100%" stopColor="#6FA582" />
        </linearGradient>
        <linearGradient id="bgcBoxFront" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3F8D5C" />
          <stop offset="100%" stopColor="#155A2D" />
        </linearGradient>
        <linearGradient id="bgcBoxSide" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0F4A26" />
          <stop offset="100%" stopColor="#093017" />
        </linearGradient>

        <linearGradient id="bgcStampHandle" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2F6B40" />
          <stop offset="100%" stopColor="#143A1F" />
        </linearGradient>
        <linearGradient id="bgcStampRed" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#C9554A" />
          <stop offset="100%" stopColor="#9C3829" />
        </linearGradient>

        <linearGradient id="bgcEnvFront" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="100%" stopColor="#DDEBE0" />
        </linearGradient>
        <linearGradient id="bgcEnvFlap" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#CADDCF" />
          <stop offset="100%" stopColor="#A4C0AC" />
        </linearGradient>

        <radialGradient id="bgcFloor" cx="50%" cy="80%" r="55%">
          <stop offset="0%" stopColor="#BFDDC8" stopOpacity="0.65" />
          <stop offset="100%" stopColor="#BFDDC8" stopOpacity="0" />
        </radialGradient>
      </defs>
    </svg>
  );
}

function Floor() {
  return (
    <svg viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" className={styles.floorSvg}>
      <ellipse cx="720" cy="800" rx="820" ry="140" fill="url(#bgcFloor)" />
    </svg>
  );
}

function FolderStack() {
  return (
    <svg viewBox="0 0 220 200" width="100%">
      <g transform="translate(0,40)">
        <polygon points="20,80  110,30 200,80 110,130" fill="url(#bgcFolderTop)" />
        <polygon points="20,80  110,130 110,150 20,100" fill="url(#bgcFolderSide)" />
        <polygon points="200,80 110,130 110,150 200,100" fill="url(#bgcFolderFront)" />
        <polygon points="60,60 120,30 150,46 90,76" fill="#4D9C68" opacity="0.85" />
      </g>
      <g transform="translate(10,0)">
        <polygon points="20,80  110,30 200,80 110,130" fill="url(#bgcFolderTop)" />
        <polygon points="20,80  110,130 110,150 20,100" fill="url(#bgcFolderSide)" />
        <polygon points="200,80 110,130 110,150 200,100" fill="url(#bgcFolderFront)" />
        <polygon points="60,60 120,30 150,46 90,76" fill="#5BAE76" opacity="0.9" />
      </g>
    </svg>
  );
}

function ContractStack() {
  return (
    <svg viewBox="0 0 240 220" width="100%">
      <g transform="translate(0, 80)">
        <polygon points="30,60 130,15 220,55 120,100" fill="url(#bgcPaperTop)" stroke="#B7D5C2" strokeWidth="0.5" />
        <polygon points="30,60 120,100 120,108 30,68" fill="url(#bgcPaperSide)" />
        <polygon points="220,55 120,100 120,108 220,63" fill="url(#bgcPaperFront)" />
      </g>
      <g transform="translate(6, 50)">
        <polygon points="30,60 130,15 220,55 120,100" fill="url(#bgcPaperTop)" stroke="#B7D5C2" strokeWidth="0.5" />
        <polygon points="30,60 120,100 120,108 30,68" fill="url(#bgcPaperSide)" />
        <polygon points="220,55 120,100 120,108 220,63" fill="url(#bgcPaperFront)" />
        <g stroke="#94BAA3" strokeWidth="1.8" strokeLinecap="round">
          <line x1="60" y1="55" x2="110" y2="32" />
          <line x1="80" y1="62" x2="160" y2="44" />
          <line x1="80" y1="72" x2="180" y2="50" />
        </g>
      </g>
      <g transform="translate(12, 20)">
        <polygon points="30,60 130,15 220,55 120,100" fill="url(#bgcPaperTop)" stroke="#B7D5C2" strokeWidth="0.5" />
        <polygon points="30,60 120,100 120,108 30,68" fill="url(#bgcPaperSide)" />
        <polygon points="220,55 120,100 120,108 220,63" fill="url(#bgcPaperFront)" />
        <g stroke="#94BAA3" strokeWidth="1.8" strokeLinecap="round">
          <line x1="60" y1="55" x2="110" y2="32" />
          <line x1="80" y1="62" x2="160" y2="44" />
        </g>
        <g transform="translate(150 30) skewX(-30) scale(1, 0.85)">
          <circle cx="0" cy="0" r="14" fill="none" stroke="#C9554A" strokeWidth="2.5" opacity="0.9" />
          <circle cx="0" cy="0" r="9" fill="#C9554A" opacity="0.2" />
        </g>
      </g>
    </svg>
  );
}

function Clipboard() {
  return (
    <svg viewBox="0 0 200 220" width="100%">
      <polygon points="20,90 110,40 190,85 100,135" fill="#2E7A48" />
      <polygon points="20,90 100,135 100,200 20,155" fill="#0F4A26" />
      <polygon points="190,85 100,135 100,200 190,150" fill="#1F7541" />
      <polygon points="90,46 120,30 142,42 112,58" fill="#093017" />
      <g transform="translate(2,-6)">
        <polygon points="30,90 110,50 180,85 100,125" fill="#FFFFFF" />
        <polygon points="30,90 100,125 100,135 30,100" fill="#CFE3D6" />
        <polygon points="180,85 100,125 100,135 180,95" fill="#C2DAC9" />
        <g transform="translate(46,72) skewY(-26)">
          <rect x="0" y="0" width="10" height="10" rx="2.5" fill="#166534" />
          <path d="M2.5 5 L4.5 7 L8 3" stroke="#FFFFFF" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          <rect x="16" y="2.5" width="58" height="4.5" rx="1.5" fill="#94BAA3" />
          <rect x="0" y="15" width="10" height="10" rx="2.5" fill="#166534" />
          <path d="M2.5 20 L4.5 22 L8 18" stroke="#FFFFFF" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          <rect x="16" y="17.5" width="48" height="4.5" rx="1.5" fill="#94BAA3" />
          <rect x="0" y="30" width="10" height="10" rx="2.5" fill="#E3E9E5" />
          <rect x="16" y="32.5" width="54" height="4.5" rx="1.5" fill="#C7D0CA" />
        </g>
      </g>
    </svg>
  );
}

function BidBox() {
  return (
    <svg viewBox="0 0 240 220" width="100%">
      <polygon points="30,70 130,20 230,70 130,120" fill="url(#bgcBoxTop)" />
      <polygon points="30,70 130,120 130,200 30,150" fill="url(#bgcBoxFront)" />
      <polygon points="230,70 130,120 130,200 230,150" fill="url(#bgcBoxSide)" />
      <polygon points="80,68 130,43 180,68 130,93" fill="#093017" />
      <polygon points="92,67 130,48 168,67 130,86" fill="#051E0E" />
      <g transform="translate(106 6)">
        <polygon points="0,30 30,15 60,30 30,45" fill="url(#bgcEnvFront)" />
        <polygon points="0,30 30,45 30,53 0,38" fill="#B7D5C2" />
        <polygon points="60,30 30,45 30,53 60,38" fill="#A4C0AC" />
        <polygon points="0,30 30,15 60,30 30,30" fill="url(#bgcEnvFlap)" />
      </g>
      <g transform="translate(60,135)">
        <rect x="0" y="0" width="46" height="6" rx="1.5" fill="#FFFFFF" opacity="0.85" transform="skewY(-26)" />
        <rect x="0" y="12" width="34" height="4" rx="1" fill="#FFFFFF" opacity="0.55" transform="skewY(-26)" />
      </g>
    </svg>
  );
}

function Stamp() {
  return (
    <svg viewBox="0 0 180 180" width="100%">
      <polygon points="20,120 90,90 160,120 90,150" fill="#9CC3A9" />
      <polygon points="20,120 90,150 90,160 20,130" fill="#6A8F77" />
      <polygon points="160,120 90,150 90,160 160,130" fill="#7FA68C" />
      <polygon points="35,118 90,96 145,118 90,140" fill="#C9554A" />
      <polygon points="48,116 90,100 132,116 90,132" fill="#A23E32" opacity="0.7" />
      <g transform="translate(0,-30)">
        <polygon points="55,114 90,100 125,114 90,128" fill="url(#bgcStampRed)" />
        <polygon points="55,114 90,128 90,138 55,124" fill="#73271E" />
        <polygon points="125,114 90,128 90,138 125,124" fill="#92382C" />
        <polygon points="74,70 90,62 106,70 90,78" fill="url(#bgcStampHandle)" />
        <polygon points="74,70 90,78 90,104 74,96" fill="#093017" />
        <polygon points="106,70 90,78 90,104 106,96" fill="#155A2D" />
        <ellipse cx="90" cy="62" rx="20" ry="8" fill="#1F7541" />
        <ellipse cx="90" cy="60" rx="20" ry="8" fill="#3F8D5C" />
      </g>
    </svg>
  );
}

function Envelope() {
  return (
    <svg viewBox="0 0 160 140" width="100%">
      <polygon points="10,60 80,20 150,60 80,100" fill="url(#bgcEnvFront)" />
      <polygon points="10,60 80,100 80,118 10,78" fill="#B7D5C2" />
      <polygon points="150,60 80,100 80,118 150,78" fill="#A4C0AC" />
      <polygon points="10,60 80,80 150,60 80,20" fill="url(#bgcEnvFlap)" opacity="0.85" />
      <g transform="translate(80,78) scale(1, 0.7)">
        <circle r="9" fill="#C9554A" />
        <circle r="5" fill="#FFFFFF" opacity="0.25" />
      </g>
    </svg>
  );
}

function CheckBadge() {
  return (
    <svg viewBox="0 0 80 80" width="100%">
      <circle cx="40" cy="40" r="26" fill="#166534" />
      <circle cx="40" cy="40" r="26" fill="none" stroke="#FFFFFF" strokeWidth="2" strokeDasharray="2 3" opacity="0.45" />
      <path d="M28 41 L36 49 L52 32" stroke="#FFFFFF" strokeWidth="4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Coin() {
  return (
    <svg viewBox="0 0 80 80" width="100%">
      <ellipse cx="40" cy="44" rx="26" ry="10" fill="#0F4A26" />
      <ellipse cx="40" cy="40" rx="26" ry="10" fill="#1F7541" />
      <ellipse cx="40" cy="40" rx="22" ry="8" fill="#3F8D5C" />
      <text
        x="40"
        y="44"
        textAnchor="middle"
        fontFamily="Plus Jakarta Sans, Pretendard, sans-serif"
        fontSize="11"
        fontWeight="800"
        fill="#FFFFFF"
        opacity="0.95"
      >
        G2B
      </text>
    </svg>
  );
}

function Twinkles() {
  return (
    <svg
      className={styles.tinyAcc}
      viewBox="0 0 1440 900"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <g fill="#166534">
        <g className={`${styles.twinkle} ${styles.tw1}`} transform="translate(180 200)">
          <path d="M0 -7 L1.2 -1.2 L7 0 L1.2 1.2 L0 7 L-1.2 1.2 L-7 0 L-1.2 -1.2 Z" />
        </g>
        <g className={`${styles.twinkle} ${styles.tw2}`} transform="translate(1260 180)">
          <path d="M0 -6 L1 -1 L6 0 L1 1 L0 6 L-1 1 L-6 0 L-1 -1 Z" />
        </g>
        <g className={`${styles.twinkle} ${styles.tw3}`} transform="translate(140 360)">
          <path d="M0 -5 L0.9 -0.9 L5 0 L0.9 0.9 L0 5 L-0.9 0.9 L-5 0 L-0.9 -0.9 Z" />
        </g>
        <g className={`${styles.twinkle} ${styles.tw4}`} transform="translate(1300 360)">
          <path d="M0 -6 L1 -1 L6 0 L1 1 L0 6 L-1 1 L-6 0 L-1 -1 Z" />
        </g>
      </g>
      <g fill="#166534" opacity="0.18">
        <circle cx="320" cy="140" r="2.5" />
        <circle cx="1110" cy="130" r="2.5" />
        <circle cx="230" cy="480" r="2.5" />
        <circle cx="1210" cy="480" r="2.5" />
        <circle cx="560" cy="95" r="2" />
        <circle cx="900" cy="95" r="2" />
      </g>
      <g stroke="#166534" strokeWidth="1.6" strokeLinecap="round" opacity="0.3">
        <g transform="translate(420 200)">
          <line x1="-3" y1="0" x2="3" y2="0" />
          <line x1="0" y1="-3" x2="0" y2="3" />
        </g>
        <g transform="translate(1030 230)">
          <line x1="-3" y1="0" x2="3" y2="0" />
          <line x1="0" y1="-3" x2="0" y2="3" />
        </g>
      </g>
    </svg>
  );
}
