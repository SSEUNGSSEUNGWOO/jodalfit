// gen_flow.py::ENGINE_JS 포팅 — 선 하나 = 공고 하나, 벽 셋, 통로만 뚫림. 색·펜·이징·오프스크린 blit 전부 원본 값.
// 원본과 다른 점 넷: 전역 querySelector 대신 엘리먼트를 받는다 / cfg JSON 대신 SCENE 상수 + counts 인자 /
// 공고명(.ttl) 자리에 탈락 이유 엘리먼트 / paint 가 document.body 에 'done' 을 토글하지 않는다(React 가 든다).

export const SCENE = {
  W: 1120,
  H: 392,
  CY: 196,
  XS: [0, 288, 576, 864],
  FAN_X: 936,
  FAN_SP: 150,
  HH: [180, 160, 150, 100],
  CONV: 44,
  PRESS: 44,
  RSN_Y: 346, // 탈락 이유 캡션 y
} as const;

const { W, H, CY, XS, FAN_X, FAN_SP, HH, CONV, PRESS } = SCENE;
const NW = XS.length - 1; // 벽 수
const S = NW + 1; // 구간 수(=코호트 수)

/** 구간 s 의 선 간격(px). 간격이 벌어지는 것이 곧 '몇 개가 남았나'다. */
export function pitch(s: number, cnt: readonly number[]): number {
  return (2 * HH[s]) / Math.max(1, cnt[s] - 1);
}

/** 네 구간의 간격. gen_flow.py --demo 의 gap 과 같은 값(cnt > 1 일 때). */
export function gaps(cnt: readonly number[]): number[] {
  return HH.map((_, s) => pitch(s, cnt));
}

export type Engine = {
  setup(): void;
  paint(x: number): void;
  setCounts(cnt: number[]): void;
  counts(): number[];
};

function rng(a: number) {
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// 벽 1·2·3 에서 막히는 코호트의 (불투명도, 눌림, 꼬리, 굵기). 남은 선이 적을수록 진하게.
const PEN: readonly [number, number, number, number][] = [
  [0.055, 0.16, 0.03, 0.3],
  [0.3, 0.6, 0.08, 0.35],
  [0.34, 0.65, 0.09, 0.35],
];

/** 숫자가 아직 안 온 칸의 '선 몇 개를 그릴지'만 메우는 값 — 기하 전용이다.
 *  화면에 뜨는 숫자는 라벨이 data-to 로 따로 쥐고 있고(모르면 "…"), 여기 값이 사용자에게 보이는 일은 없다.
 *  없으면 N=0 이라 첫 1초가 빈 캔버스다 — 머리 장면은 계산 대기 가림막이니 처음부터 덩어리가 있어야 한다. */
const FALLBACK_GEOM = [9400, 850, 90, 12] as const;

export const geom = (c: readonly number[]) => c.map((n, i) => (n < 0 ? (FALLBACK_GEOM[i] ?? 0) : n));

export function createEngine(
  canvas: HTMLCanvasElement,
  labels: HTMLElement[],
  reasons: HTMLElement[],
  counts: number[],
): Engine {
  const ctx = canvas.getContext("2d")!;
  let cnt = geom(counts);
  let paths: Path2D[] = [];
  let off: HTMLCanvasElement | null = null;
  let sx = 1;
  let sy = 1;

  /* ---- 선 기하: counts 가 바뀔 때만 계산한다 ---------------------------- */
  function build() {
    const N = cnt[0];
    // 살아남는 선은 씨앗 고정으로 고른다 — 그림이 매번 같아야 비교가 된다.
    const rnd = rng(7);
    const idx = new Int32Array(N);
    for (let i = 0; i < N; i++) idx[i] = i;
    for (let i = N - 1; i > 0; i--) {
      const j = (rnd() * (i + 1)) | 0;
      const t = idx[i];
      idx[i] = idx[j];
      idx[j] = t;
    }

    const fate = new Uint8Array(N).fill(1); // 1=1번 벽에서 막힘 … S=끝까지 통과
    const alive: Int32Array[] = [];
    for (let s = 1; s <= NW; s++) {
      const a = Int32Array.from(idx.slice(0, cnt[s])).sort();
      for (const i of a) fate[i] = s + 1;
      alive.push(a);
    }

    // Y[i*S+s] = s 구간에서의 y. 간격이 1px 아래로 내려가면 무아레 — 0.45px 지터로 위상을 흩는다.
    const Y = new Float32Array(N * S);
    const jit = (p: number) => (p < 1.2 ? (rnd() * 2 - 1) * 0.45 : 0);
    for (let i = 0; i < N; i++) Y[i * S] = CY + ((i / (N - 1)) * 2 - 1) * HH[0] + jit(pitch(0, cnt));
    for (let s = 1; s <= NW; s++) {
      const a = alive[s - 1];
      const m = a.length;
      const pj = pitch(s, cnt);
      for (let r = 0; r < m; r++) Y[a[r] * S + s] = CY + (m === 1 ? 0 : (r / (m - 1)) * 2 - 1) * HH[s] + jit(pj);
    }

    // 코호트별 Path2D. 매 프레임 새로 만들지 않는다 — 이게 60fps 의 전부다.
    paths = Array.from({ length: S }, () => new Path2D());
    for (let i = 0; i < N; i++) {
      const f = fate[i];
      const p = paths[f - 1];
      let y = Y[i * S];
      p.moveTo(0, y);
      for (let s = 1; s < f; s++) {
        // 통과한 벽마다 통로 폭으로 모인다
        const g = XS[s];
        const ny = Y[i * S + s];
        p.lineTo(g - CONV, y);
        p.bezierCurveTo(g - 20, y, g - 16, ny, g, ny);
        y = ny;
      }
      if (f < S) p.lineTo(XS[f], y); // 벽까지 가서 멈춘다 (아래로 새지 않는다)
      else {
        p.lineTo(FAN_X, y);
        const row = CY + ((y - CY) / HH[NW]) * FAN_SP;
        p.bezierCurveTo(FAN_X + 70, y, W - 70, row, W, row);
      }
    }
  }

  /* ---- 그리기 ---------------------------------------------------------- */
  // 막힌 코호트는 벽 앞에서 눌렸다 벽면에서 흩어진다. 벽면에서 옅게 남겨야 '막혔다'로 읽힌다.
  function fade(c: CanvasRenderingContext2D, x1: number, a: number, pressed: number, tail: number) {
    const g = c.createLinearGradient(0, 0, x1, 0);
    g.addColorStop(0, `rgba(20,20,20,${a})`);
    g.addColorStop((x1 - PRESS) / x1, `rgba(20,20,20,${a})`);
    g.addColorStop((x1 - 6) / x1, `rgba(20,20,20,${pressed})`);
    g.addColorStop(1, `rgba(20,20,20,${tail})`);
    return g;
  }

  function pen(g: CanvasRenderingContext2D, c: number): [CanvasGradient, number] {
    if (c < NW) {
      const a = PEN[c];
      return [fade(g, XS[c + 1], a[0], a[1], a[2]), a[3]];
    }
    const last = g.createLinearGradient(0, 0, W, 0); // 마지막 코호트만 주황
    last.addColorStop(0, "rgba(20,20,20,.8)");
    last.addColorStop((XS[NW] - 20) / W, "rgba(20,20,20,.8)");
    last.addColorStop((XS[NW] + 30) / W, "rgba(249,115,22,.9)");
    last.addColorStop(1, "rgba(249,115,22,.9)");
    return [last, 0.9];
  }

  // 벽 k — 화면 끝까지, 통로만 뚫려 있다.
  function wall(g: CanvasRenderingContext2D, k: number) {
    const x = XS[k];
    g.strokeStyle = "#141414";
    for (const sg of [-1, 1]) {
      g.lineWidth = 2.5;
      g.beginPath();
      g.moveTo(x, sg < 0 ? 0 : CY + HH[k]);
      g.lineTo(x, sg < 0 ? CY - HH[k] : H);
      g.stroke();
      g.lineWidth = 1.5;
      g.beginPath(); // 통로 입술 — 구멍임을 분명히
      g.moveTo(x - 7, CY + sg * HH[k]);
      g.lineTo(x + 7, CY + sg * HH[k]);
      g.stroke();
    }
  }

  function render() {
    if (!off) return;
    const g = off.getContext("2d")!;
    const dpr = devicePixelRatio || 1;
    g.setTransform(sx * dpr, 0, 0, sy * dpr, 0, 0); // 설계 좌표 그대로, 레티나는 dpr. sy 는 390px 의 낮은 머리
    g.clearRect(0, 0, W, H);
    g.lineCap = "butt";
    for (let c = 0; c < S; c++) {
      const [stroke, width] = pen(g, c);
      g.strokeStyle = stroke;
      g.lineWidth = width;
      g.stroke(paths[c]);
    }
    for (let k = 1; k <= NW; k++) wall(g, k);
  }

  function setup() {
    const r = canvas.getBoundingClientRect();
    const dpr = devicePixelRatio || 1;
    sx = r.width / W;
    sy = r.height ? r.height / H : 1;
    canvas.width = Math.round(r.width * dpr);
    canvas.height = Math.round(H * sy * dpr);
    off = Object.assign(document.createElement("canvas"), { width: canvas.width, height: canvas.height });
    ctx.setTransform(1, 0, 0, 1, 0, 0); // blit 는 장치 픽셀로
    render();
  }

  // 왼쪽(x 까지)만 체(off)에서 떠 온다 — 오른쪽은 빈 캔버스.
  function draw(front: number) {
    if (!off) return;
    const fw = Math.max(1, Math.round(front * sx * (devicePixelRatio || 1)));
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(off, 0, 0, fw, canvas.height, 0, 0, fw, canvas.height);
  }

  // 전진선 x 기준 라벨·글자: 벽을 지나 150px 동안 카운트업, 글자는 제 폭을 다 지나야 뜬다.
  function paintLabels(x: number) {
    for (const t of reasons) t.classList.toggle("on", x >= Number(t.dataset.x));
    for (const g of labels) {
      const gx = Number(g.dataset.x);
      g.classList.toggle("on", x >= gx);
      const span = g.querySelector<HTMLElement>(".cnt");
      if (!span) continue;
      const to = Number(span.dataset.to);
      if (to < 0) {
        span.textContent = "…";
        continue;
      }
      const p = Math.min(1, Math.max(0, (x - gx) / 150));
      span.textContent = Math.round(to * (1 - Math.pow(1 - p, 3))).toLocaleString("ko-KR");
    }
  }

  build();

  return {
    setup,
    paint(x: number) {
      draw(x);
      paintLabels(x);
    },
    setCounts(next: number[]) {
      const c = geom(next);
      if (c.length === cnt.length && c.every((n, i) => n === cnt[i])) return;
      cnt = c;
      build();
      render();
    },
    counts: () => cnt.slice(),
  };
}
