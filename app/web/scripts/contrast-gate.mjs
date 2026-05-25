// Phase 0 color gate — OKLCH -> sRGB, WCAG contrast, and Machado CVD simulation.
// Throwaway verification tool for the Reading Room token migration. Run:
//   node app/web/scripts/contrast-gate.mjs
// Not imported by the app. Deleted/ignored after Phase 0 sign-off.

// ---- OKLCH -> linear sRGB -> sRGB ----
function oklchToLinearSrgb(L, C, H) {
  const h = (H * Math.PI) / 180;
  const a = C * Math.cos(h);
  const b = C * Math.sin(h);
  const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = L - 0.0894841775 * a - 1.291485548 * b;
  const l = l_ ** 3, m = m_ ** 3, s = s_ ** 3;
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
}
const enc = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055);
const dec = (c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
const clamp01 = (x) => Math.min(1, Math.max(0, x));
function oklch(str) {
  // accepts "L% C H" with L in %, e.g. "55% 0.205 25"
  const [Ls, Cs, Hs] = str.trim().split(/\s+/);
  const L = parseFloat(Ls) / 100, C = parseFloat(Cs), H = parseFloat(Hs);
  const lin = oklchToLinearSrgb(L, C, H);
  return lin; // linear rgb (may be out of gamut; clamp at use)
}
function toHex(lin) {
  return '#' + lin.map((c) => Math.round(clamp01(enc(clamp01(c))) * 255).toString(16).padStart(2, '0')).join('');
}
function relLum(lin) {
  const [r, g, b] = lin.map(clamp01);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contrast(linA, linB) {
  const a = relLum(linA), b = relLum(linB);
  const hi = Math.max(a, b), lo = Math.min(a, b);
  return (hi + 0.05) / (lo + 0.05);
}

// ---- Machado 2009 CVD matrices (severity 1.0), applied in linear RGB ----
const CVD = {
  deuter: [[0.367322,0.860646,-0.227968],[0.280085,0.672501,0.047413],[-0.01182,0.04294,0.968881]],
  protan: [[0.152286,1.052583,-0.204868],[0.114503,0.786281,0.099216],[-0.003882,-0.048116,1.051998]],
  tritan: [[1.255528,-0.076749,-0.178779],[-0.078411,0.930809,0.147602],[0.004733,0.691367,0.3039]],
};
function simulate(lin, M) {
  const c = lin.map(clamp01);
  return [0,1,2].map((i) => M[i][0]*c[0] + M[i][1]*c[1] + M[i][2]*c[2]);
}
// linear sRGB -> OKLab L (perceptual lightness) for separation checks
function linToOklab(lin) {
  const [r,g,b] = lin.map(clamp01);
  const l = Math.cbrt(0.4122214708*r + 0.5363325363*g + 0.0514459929*b);
  const m = Math.cbrt(0.2119034982*r + 0.6806995451*g + 0.1073969566*b);
  const s = Math.cbrt(0.0883024619*r + 0.2817188376*g + 0.6299787005*b);
  return [
    0.2104542553*l + 0.793617785*m - 0.0040720468*s,
    1.9779984951*l - 2.428592205*m + 0.4505937099*s,
    0.0259040371*l + 0.7827717662*m - 0.808675766*s,
  ];
}
function deltaE(linA, linB) {
  const A = linToOklab(linA), B = linToOklab(linB);
  return Math.hypot(A[0]-B[0], A[1]-B[1], A[2]-B[2]);
}

// ================= CANDIDATE TOKENS =================
const N = {
  bg:      '99.3% 0.004 75',
  bgSoft:  '97.6% 0.008 70',
  bgSoft2: '95.6% 0.010 65',
  ink:     '20% 0.020 45',
  ink2:    '33% 0.035 45',
  ink3:    '46% 0.030 47',
  ink4:    '56% 0.028 50',
  ink5:    '76% 0.014 55',
  line:    '89% 0.010 60',
  line2:   '82% 0.012 60',
};
const TIERS = {
  P:   { bg:'95% 0.030 25',   text:'41% 0.13 28',  bdr:'86% 0.075 27',  dot:'55% 0.205 25'  },
  LP:  { bg:'95.5% 0.038 60', text:'43% 0.10 58',  bdr:'87% 0.085 58',  dot:'62% 0.165 58'  },
  VUS: { bg:'96.5% 0.050 95', text:'46% 0.105 85', bdr:'87% 0.110 95',  dot:'80% 0.155 90'  },
  LB:  { bg:'96% 0.045 135',  text:'43% 0.10 138', bdr:'87% 0.080 138', dot:'71% 0.150 140' },
  B:   { bg:'96% 0.035 162',  text:'40% 0.09 160', bdr:'86% 0.070 162', dot:'60% 0.130 162' },
};

const bg = oklch(N.bg);
const pass = (r, need) => (r >= need ? 'PASS' : 'FAIL');

console.log('=== Neutrals: hex + contrast on --bg (', toHex(bg), ') ===');
for (const [k, v] of Object.entries(N)) {
  const lin = oklch(v);
  const r = contrast(lin, bg);
  const note = ['ink','ink2','ink3','ink4'].includes(k) ? `  text AA(4.5): ${pass(r,4.5)}`
             : k==='ink5' ? `  large/icon AA(3): ${pass(r,3)}`
             : k==='line'||k==='line2' ? `  (hairline, want >=1.18 vs bg): ${pass(r,1.18)}` : '';
  console.log(`${k.padEnd(8)} ${toHex(lin)}  CR=${r.toFixed(2)}${note}`);
}

console.log('\n=== Classification tiers: text-on-tier-bg (need 4.5) + dot vs page ===');
for (const [t, c] of Object.entries(TIERS)) {
  const tbg = oklch(c.bg), txt = oklch(c.text), dot = oklch(c.dot);
  const rText = contrast(txt, tbg);
  const rDotPage = contrast(dot, bg);
  console.log(`${t.padEnd(4)} bg ${toHex(tbg)} text ${toHex(txt)} bdr ${toHex(oklch(c.bdr))} dot ${toHex(dot)}  | text/bg CR=${rText.toFixed(2)} ${pass(rText,4.5)}  dot/page CR=${rDotPage.toFixed(2)}`);
}

console.log('\n=== CVD: dot separation (OKLab deltaE, normal + simulated). Adjacent & red/green pairs ===');
const order = ['P','LP','VUS','LB','B'];
const dots = Object.fromEntries(order.map((t) => [t, oklch(TIERS[t].dot)]));
const pairs = [['P','LP'],['LP','VUS'],['VUS','LB'],['LB','B'],['P','B'],['P','VUS'],['LP','LB']];
const sims = { normal: (x)=>x, ...CVD };
for (const [name, M] of Object.entries(sims)) {
  const row = pairs.map(([a,b]) => {
    const da = name==='normal' ? dots[a] : simulate(dots[a], M);
    const db = name==='normal' ? dots[b] : simulate(dots[b], M);
    const de = deltaE(da, db);
    return `${a}-${b}:${de.toFixed(3)}${de < 0.06 ? '!' : ''}`;
  });
  console.log(`${name.padEnd(7)} ${row.join('  ')}`);
}
console.log('\n(deltaE < 0.060 flagged "!" = risk of collapse; labels+lane position are redundant encoders.)');
