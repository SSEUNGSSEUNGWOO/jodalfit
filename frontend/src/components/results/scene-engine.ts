// 머리 장면 엔진 — D-2 점 격자. gen_funnel_variants.py::fixedDots('d2') 포팅.
//
// 공고 하나 = 점 하나. 네 덩어리가 **같은 pitch** 를 쓰므로 점유 면적이 건수에 그대로 비례한다
// (눈금을 속일 수 없다 — 세면 된다). 이게 통로 폭으로 좁히던 A 안을 버린 이유다: 통로는
// 180/160/150/100 으로 44% 만 좁아지는데 건수는 99.8% 준다.
//
// 네 칸은 앞 칸의 **부분집합**이다 — 지금 입찰 가능 → 비슷한 순서로 추린 후보 → 자격 통과 → 추천.
// 시안의 D-2 는 "등록업종 허용 845" 를 둘째 칸에 두고 후보 200 을 그 안의 진한 점으로 그렸는데
// 그건 거짓이었다(후보는 그 집합이 아니라 전체에서 유사도 순으로 뽑는다 — 2026-10-23 확인:
// 최종 20건 중 8건이 업종 불일치). 지금은 네 칸이 진짜 중첩이라 면적 비례가 전 구간에서 정직하다.
//
// 원본과 다른 점 셋: 전역 querySelector 대신 엘리먼트를 받는다 / cfg JSON 대신 SCENE 상수 + counts
// 인자 / 시간 t 가 아니라 **전진 좌표 x** 로 움직인다(실제 진행에 묶인 가림막이라 숫자가 와야 다음 칸으로 간다).

export const SCENE = {
  W: 1120,
  H: 392,
  // 관문 셋의 설계 좌표. 그리기에는 쓰지 않는다(실제 관문 x 는 레이아웃이 정한다) —
  // Scene.tsx 가 "어디까지 전진할지"와 라벨 초기 위치를 잡는 기준이다.
  XS: [0, 288, 576, 864],
  RSN_Y: 346, // 탈락 이유 캡션 y
  // 큰 것부터 — 캔버스에 들어가는 첫 pitch 를 쓴다. 작을수록 많은 점이 들어간다.
  PITCHES: [5, 4.2, 3.6, 3, 2.6, 2.2, 1.8] as const,
  ALIVE: 0.85,
  // 끝난 상태에는 통과분이 다음 칸으로 옮겨 가 각 칸에 탈락분만 남는다. 너무 흐리면 덩어리가
  // 안 보여 면적 비례가 전달되지 않는다 — 0.10 → 0.24 (2026-10-23 승우님 '잘 안 보인다').
  DEAD: 0.24,
} as const;

const { W, H, XS, PITCHES, ALIVE, DEAD } = SCENE;
const NS = 4; // 칸 수
const NT = NS - 1; // 관문 수

export type Engine = {
  setup(): void;
  paint(x: number): void;
  setCounts(cnt: number[]): void;
  counts(): number[];
};

export type Layout = {
  p: number; // pitch (장치 픽셀)
  shp: [number, number][]; // 칸마다 [열, 행]
  cxs: number[]; // 칸 중심 x
  gx: number[]; // 관문 x — 덩어리 사이 한가운데
  pad: number;
  tick: number;
};

/** 숫자가 아직 안 온 칸의 '점 몇 개를 그릴지'만 메우는 값 — 기하 전용이다.
 *  화면에 뜨는 숫자는 라벨이 data-to 로 따로 쥐고 있고(모르면 "…"), 여기 값이 사용자에게 보이는 일은 없다.
 *  없으면 N=0 이라 첫 1초가 빈 캔버스다 — 머리 장면은 계산 대기 가림막이니 처음부터 덩어리가 있어야 한다.
 *  0057 이후 첫 칸은 8,225 쯤(마감 90일 이내 · 벡터 있음 · 자격등록 안 지남). */
const FALLBACK_GEOM = [8200, 200, 85, 20] as const;

export const geom = (c: readonly number[]) => c.map((n, i) => (n < 0 ? (FALLBACK_GEOM[i] ?? 0) : n));

/** 칸 배치. 같은 pitch 를 쓰는 게 핵심이라 pitch 를 먼저 고르고 칸 모양을 맞춘다.
 *  순수 함수 — DOM 없이 테스트에서 면적 비례를 검사한다. 들어갈 pitch 가 없으면 null. */
export function layout(cnt: readonly number[], wd: number, hd: number): Layout | null {
  const N = cnt[0];
  if (N <= 0 || wd <= 0 || hd <= 0) return null;
  const pad = (46 * hd) / H;
  const tick = (44 * wd) / W; // 마지막 칸 오른쪽 주황 눈금 자리
  const marg = (24 * wd) / W;
  const gmin = (64 * wd) / W;
  const gmax = (150 * wd) / W;
  const availh = hd - 2 * pad;

  for (const p of PITCHES) {
    const rows0 = Math.max(1, Math.floor(availh / p) + 1);
    const ar = Math.ceil(N / rows0) / rows0; // 첫 덩어리의 가로세로비 — 나머지도 닮게 만든다
    const shp: [number, number][] = [];
    for (const n of cnt) {
      if (n <= 0) {
        shp.push([0, 0]); // 아는 0 은 지어내지 않는다 — 빈 칸으로 둔다
        continue;
      }
      let best: [number, number, number] | null = null; // [닮은 정도, 열, 행]
      for (let r = 1; r <= rows0; r++) {
        if ((r - 1) * p > availh) continue;
        const c = Math.ceil(n / r);
        if (c * r > n * 1.06) continue; // 낭비 6% 안
        const d = Math.abs(Math.log(c / r / ar));
        if (!best || d < best[0]) best = [d, c, r];
      }
      if (!best) break;
      shp.push([best[1], best[2]]);
    }
    if (shp.length !== cnt.length) continue;
    const ws = shp.map((s) => Math.max(0, (s[0] - 1) * p));
    const sum = ws.reduce((a, b) => a + b, 0);
    const gap = Math.min(gmax, (wd - tick - 2 * marg - sum) / (ws.length - 1));
    if (gap < gmin) continue;
    let x = (wd - tick - sum - gap * (ws.length - 1)) / 2;
    const cxs: number[] = [];
    for (const w of ws) {
      cxs.push(x + w / 2);
      x += w + gap;
    }
    const gx: number[] = [];
    for (let k = 0; k < NT; k++) {
      const a = cxs[k] + ((shp[k][0] || 1) - 1) * (p / 2);
      const b = cxs[k + 1] - ((shp[k + 1][0] || 1) - 1) * (p / 2);
      gx.push((a + b) / 2);
    }
    return { p, shp, cxs, gx, pad, tick };
  }
  return null;
}

/** 칸 i 가 차지하는 면적(장치 픽셀²). D-2 의 주장 = 이 값이 건수에 비례한다. */
export const blockArea = (l: Layout, i: number) => l.shp[i][0] * l.shp[i][1] * l.p * l.p;

function rng(a: number) {
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const sstep = (t: number) => {
  const u = Math.min(1, Math.max(0, t));
  return u * u * (3 - 2 * u);
};

// 관문 k 의 전진 구간(설계 좌표) — Scene.tsx 가 XS[k+1]-30 까지만 전진시키므로 거기서 시작한다.
const gateStart = (k: number) => XS[k + 1] - 30;
const gateEnd = (k: number) => Math.min(W, XS[k + 1] + 70);
const UNFOLD_FROM = gateEnd(NT - 1);

export function createEngine(
  canvas: HTMLCanvasElement,
  labels: HTMLElement[],
  reasons: HTMLElement[],
  counts: number[],
): Engine {
  const ctx = canvas.getContext("2d")!;
  let cnt = geom(counts);
  let lay: Layout | null = null;
  let pos = new Float32Array(0); // 칸마다의 자리
  let unf = new Float32Array(0); // 마지막 펼침 자리(표 행)
  let ends = new Uint8Array(0); // 이 점이 마지막으로 서는 칸
  let rank = new Int32Array(0);
  let sz = 2;
  let dpr = 1;
  let wd = 1;
  let hd = 1;
  let placed = ""; // 라벨·사유를 둔 자리 — 바뀔 때만 style 을 쓴다(매 프레임 레이아웃 치지 않게)

  /* ---- 점의 운명: counts 가 바뀔 때만 계산한다 -------------------------- */
  function build() {
    const N = cnt[0];
    ends = new Uint8Array(N);
    rank = new Int32Array(N * NS).fill(-1);
    if (N <= 0) return;
    // 살아남는 점은 씨앗 고정으로 고른다 — 그림이 매번 같아야 비교가 된다.
    const rnd = rng(7);
    const idx = new Int32Array(N);
    for (let i = 0; i < N; i++) idx[i] = i;
    for (let i = N - 1; i > 0; i--) {
      const j = (rnd() * (i + 1)) | 0;
      const t = idx[i];
      idx[i] = idx[j];
      idx[j] = t;
    }
    for (let i = 0; i < N; i++) rank[i * NS] = i;
    // 칸마다 앞 칸의 부분집합 — 같은 idx 앞쪽을 잘라 쓰므로 중첩이 보장된다.
    for (let s = 1; s < NS; s++) {
      const a = Int32Array.from(idx.slice(0, Math.max(0, Math.min(N, cnt[s])))).sort();
      a.forEach((i, r) => {
        ends[i] = s;
        rank[i * NS + s] = r;
      });
    }
  }

  function setup() {
    const r = canvas.getBoundingClientRect();
    dpr = devicePixelRatio || 1;
    wd = Math.round(r.width * dpr);
    hd = Math.round((r.height || H) * dpr);
    if (wd <= 0 || hd <= 0) return;
    canvas.width = wd;
    canvas.height = hd;
    lay = layout(cnt, wd, hd);
    if (!lay) return;
    // 390px·dpr3 에서 pitch 가 5 아래로 눌린다 — 1px 밑으로 가면 점이 사라져 얼룩이 된다.
    sz = Math.max(1, Math.round(lay.p * 0.55));
    const N = cnt[0];
    pos = new Float32Array(N * NS * 2);
    for (let s = 0; s < NS; s++) {
      const [c, rw] = lay.shp[s];
      if (!c) continue;
      const x0 = lay.cxs[s] - ((c - 1) * lay.p) / 2;
      const y0 = hd / 2 - ((rw - 1) * lay.p) / 2;
      for (let i = 0; i < N; i++) {
        const q = rank[i * NS + s];
        if (q < 0) continue;
        pos[(i * NS + s) * 2] = x0 + (q % c) * lay.p;
        pos[(i * NS + s) * 2 + 1] = y0 + Math.floor(q / c) * lay.p;
      }
    }
    // 결과 점이 표 행 자리에 앉는다. 행 간격은 26px 가 기본이되 캔버스를 넘으면 좁힌다 —
    // 결과 건수는 회사마다 다르고(최대 20) 20×26 은 392px 를 넘는다.
    const last = Math.max(1, cnt[NS - 1]);
    const rg = Math.min((26 * hd) / H, (hd - 2 * lay.pad) / Math.max(1, last - 1));
    unf = new Float32Array(N * 2);
    for (let i = 0; i < N; i++) {
      const q = rank[i * NS + (NS - 1)];
      if (q < 0) continue;
      unf[i * 2] = lay.cxs[NS - 1];
      unf[i * 2 + 1] = hd / 2 + (q - (last - 1) / 2) * rg;
    }
    place();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
  }

  // 세로선은 한 벌이어야 한다 — 라벨 괘선과 탈락 사유를 캔버스 관문선과 같은 x 에 둔다.
  // 덩어리 모서리나 설계 좌표에 맞추면 관문선과 70~80px 어긋나 선이 두 벌로 보인다(2026-10-23).
  function place() {
    if (!lay) return;
    const toPct = (devX: number) => (devX / dpr / (wd / dpr)) * 100;
    const key = `${wd}x${hd}:${lay.gx.map((g) => g.toFixed(1)).join(",")}`;
    if (key === placed) return;
    placed = key;
    labels.forEach((e, i) => {
      const x = i === 0 ? lay!.cxs[0] - ((lay!.shp[0][0] || 1) - 1) * (lay!.p / 2) : lay!.gx[i - 1];
      e.style.left = `${toPct(x)}%`;
    });
    reasons.forEach((e, k) => {
      e.style.right = `${100 - toPct(lay!.gx[k])}%`;
    });
  }

  /* ---- 그리기 ---------------------------------------------------------- */
  function paintDots(x: number) {
    if (!lay) return;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, wd, hd);
    const N = cnt[0];

    let done = 0;
    let kact = -1;
    let lp = 0;
    for (let k = 0; k < NT; k++) {
      if (x >= gateEnd(k)) done = k + 1;
      else if (x >= gateStart(k)) {
        kact = k;
        lp = sstep((x - gateStart(k)) / (gateEnd(k) - gateStart(k)));
      }
    }
    const un = done >= NT ? sstep((x - UNFOLD_FROM) / Math.max(1, W - UNFOLD_FROM)) : 0;

    // 관문 자리 — 먹 헤어라인. 전진선이 닿은 관문만 긋는다.
    for (let k = 0; k < NT; k++) {
      if (x < gateStart(k)) continue;
      ctx.lineWidth = dpr;
      ctx.strokeStyle = "#d8d6d0";
      ctx.beginPath();
      ctx.moveTo(lay.gx[k], lay.pad * 0.5);
      ctx.lineTo(lay.gx[k], hd - lay.pad * 0.5);
      ctx.stroke();
    }

    // 덩어리가 차지한 자리를 가는 외곽선으로 — 끝난 상태에는 통과분이 다음 칸으로 가버려 탈락분만
    // 남는다. 200 중 118, 85 중 62 뿐이라 점만으로는 먼지로 보이고 200 과 85 를 구분할 수 없다.
    // 외곽선은 '이만큼이었다'를 증언한다(D-3 가 쓰던 방식을 여기에만 빌려온다). 2026-10-23.
    for (let s = 0; s < NS; s++) {
      const [c, rw] = lay.shp[s];
      if (!c || !rw) continue;
      if (x < (s === 0 ? 0 : gateStart(s - 1))) continue; // 아직 안 닿은 칸은 그리지 않는다
      // 마지막 칸은 펼쳐지기 시작하면 격자 자리가 의미를 잃는다 — 외곽선만 남으면 주황 눈금
      // 한가운데 작은 네모가 떠다닌다. 건수는 눈금이 이미 세어 보여준다.
      if (s === NS - 1 && un > 0) continue;
      const w = (c - 1) * lay.p;
      const h = (rw - 1) * lay.p;
      ctx.lineWidth = dpr;
      ctx.strokeStyle = "rgba(20,20,20,.16)";
      ctx.strokeRect(lay.cxs[s] - w / 2 - lay.p, hd / 2 - h / 2 - lay.p, w + 2 * lay.p, h + 2 * lay.p);
    }

    // 불투명도를 1/64 로 묶어 Path2D 하나씩 — N 번 fillStyle 을 바꾸지 않는다. 이게 60fps 의 전부다.
    const paths = new Map<number, Path2D>();
    for (let i = 0; i < N; i++) {
      const e = ends[i];
      // d: 이 점이 흐려지는 관문(= 마지막으로 선 칸). 끝까지 남으면 -1.
      const d = e === NS - 1 ? -1 : e;
      let px: number;
      let py: number;
      let a: number;
      if (d >= 0 && (d < done || d === kact)) {
        // 제자리에서 흐려진다 — 떨어진 점도 사라지지 않는다.
        // 그 공고가 나쁜 게 아니라 이 회사에 해당되지 않을 뿐이다.
        const o = (i * NS + d) * 2;
        px = pos[o];
        py = pos[o + 1];
        a = d === kact ? lerp(ALIVE, DEAD, lp) : DEAD;
      } else if (kact >= 0 && e > kact) {
        const o = (i * NS + kact) * 2;
        const n = (i * NS + kact + 1) * 2;
        px = lerp(pos[o], pos[n], lp);
        py = lerp(pos[o + 1], pos[n + 1], lp);
        a = ALIVE;
      } else {
        const s = Math.min(e, done);
        const o = (i * NS + s) * 2;
        px = pos[o];
        py = pos[o + 1];
        a = ALIVE;
        if (s === NS - 1 && un > 0) {
          px = lerp(px, unf[i * 2], un);
          py = lerp(py, unf[i * 2 + 1], un);
        }
      }
      if (a <= 0.02) continue;
      const q = Math.round(a * 64) / 64;
      let pa = paths.get(q);
      if (!pa) {
        pa = new Path2D();
        paths.set(q, pa);
      }
      pa.rect(px - sz / 2, py - sz / 2, sz, sz);
    }
    paths.forEach((pa, q) => {
      ctx.fillStyle = `rgba(20,20,20,${q.toFixed(4)})`;
      ctx.fill(pa);
    });

    // 주황은 면이 아니라 눈금(선)으로만 — docs/design/README.md 의 결정.
    if (un > 0) {
      ctx.strokeStyle = `rgba(249,115,22,${un.toFixed(3)})`;
      ctx.lineWidth = 1.5 * dpr;
      for (let i = 0; i < N; i++) {
        if (ends[i] !== NS - 1) continue;
        ctx.beginPath();
        ctx.moveTo(unf[i * 2] + 7 * dpr, unf[i * 2 + 1]);
        ctx.lineTo(unf[i * 2] + 44 * dpr, unf[i * 2 + 1]);
        ctx.stroke();
      }
    }
  }

  // 전진선 x 기준 라벨·글자: 관문을 지나 150px 동안 카운트업. 모르는 값은 "…"(0 은 실제 값이라 쓰지 않는다).
  function paintLabels(x: number) {
    for (const t of reasons) t.classList.toggle("on", x >= Number(t.dataset.x));
    for (const g of labels) {
      const gxv = Number(g.dataset.x);
      g.classList.toggle("on", x >= gxv);
      const span = g.querySelector<HTMLElement>(".cnt");
      if (!span) continue;
      const to = Number(span.dataset.to);
      if (to < 0) {
        span.textContent = "…";
        continue;
      }
      const p = Math.min(1, Math.max(0, (x - gxv) / 150));
      span.textContent = Math.round(to * (1 - Math.pow(1 - p, 3))).toLocaleString("ko-KR");
    }
  }

  build();

  return {
    setup,
    paint(x: number) {
      if (!lay) setup();
      place();
      paintDots(x);
      paintLabels(x);
    },
    setCounts(next: number[]) {
      const c = geom(next);
      if (c.length === cnt.length && c.every((n, i) => n === cnt[i])) return;
      cnt = c;
      build();
      setup(); // 칸 모양이 건수에서 나온다 — 숫자가 오면 배치를 다시 잡는다
    },
    counts: () => cnt.slice(),
  };
}
