/**
 * Banner fuer StrawKnight, hell und dunkel.
 *
 * Nach demselben Muster wie glimstones gen-banner.mjs: 1600 auf 500, Marke
 * links, Name in Bree Serif, Claim in Lato. Der Text wird ueber opentype.js in
 * SVG-Pfade gewandelt, damit das SVG ohne Schrift auskommt und ueberall gleich
 * aussieht. Ein Banner, das erst beim Betrachter eine Schrift sucht, sieht bei
 * jedem anders aus.
 *
 * Deps (global): opentype.js, @resvg/resvg-js. Die Schriften werden einmal in
 * das Temp-Verzeichnis geladen.
 *
 *   node .github/assets/gen-banner.mjs
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { tmpdir } from "node:os";
import { createRequire } from "node:module";
import { execSync } from "node:child_process";

const require = createRequire(import.meta.url);
const groot = execSync("npm root -g").toString().trim();
const opentype = require(`${groot}/opentype.js`);
const { Resvg } = require(`${groot}/@resvg/resvg-js`);

const __dir = dirname(fileURLToPath(import.meta.url));

const SLUG = "strawknight";
const NAME = "StrawKnight";
const CLAIM = "A phone you can break.";
const MARK = join(__dir, "..", "..", "assets", "strawknight.svg");

const W = 1600, H = 500;
const LH = 420, LW = 420;
const nameSize = 132, claimSize = 44, gap = 70, lineGap = 8;

const THEMES = [
  { suffix: "", bg: "#ffffff", name: "#1f2328", claim: "#5a5d5e" },
  { suffix: "-dark", bg: "#0d1117", name: "#e6edf3", claim: "#9aa4ad" },
];

async function laden(datei, url) {
  const p = join(tmpdir(), datei);
  if (!existsSync(p)) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`font fetch ${r.status} fuer ${datei}`);
    writeFileSync(p, Buffer.from(await r.arrayBuffer()));
  }
  return opentype.parse(readFileSync(p));
}

const font = await laden("Haus-BreeSerif-Regular.ttf",
  "https://github.com/google/fonts/raw/main/ofl/breeserif/BreeSerif-Regular.ttf");
const claimFont = await laden("Haus-Lato-Regular.ttf",
  "https://github.com/google/fonts/raw/main/ofl/lato/Lato-Regular.ttf");

const startX = 165;
const LX = startX, LY = (H - LH) / 2;
const textX = startX + LW + gap;

const sc = (s) => s / font.unitsPerEm;
const nameAsc = font.ascender * sc(nameSize);
const nameDesc = -font.descender * sc(nameSize);
const claimAsc = claimFont.ascender * (claimSize / claimFont.unitsPerEm);
const claimDesc = -claimFont.descender * (claimSize / claimFont.unitsPerEm);
const blockH = nameAsc + nameDesc + lineGap + claimAsc + claimDesc;
const nameBaseline = H / 2 - blockH / 2 + nameAsc;
const claimBaseline = nameBaseline + nameDesc + lineGap + claimAsc;

function textGroups(fnt, text, fontSize, x0, y0) {
  const scale = fontSize / fnt.unitsPerEm;
  let cx = x0;
  const parts = [];
  for (let i = 0; i < text.length; i++) {
    const glyph = fnt.charToGlyph(text[i]);
    const d = glyph.getPath(0, 0, fontSize).toPathData(2);
    parts.push(`<g transform="translate(${cx.toFixed(2)},${y0.toFixed(2)})"><path d="${d}"/></g>`);
    cx += glyph.advanceWidth * scale;
    if (i < text.length - 1) {
      cx += fnt.getKerningValue(glyph, fnt.charToGlyph(text[i + 1])) * scale;
    }
  }
  return parts.join("");
}

function embedMark(x, y, w, h) {
  const raw = readFileSync(MARK, "utf8").replace(/<\?xml[^>]*\?>\s*/, "");
  const vb = (raw.match(/viewBox="([^"]+)"/) || [, "0 0 1000 1000"])[1];
  return raw.replace(
    /<svg\b[^>]*>/,
    `<svg x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${w}" height="${h}" viewBox="${vb}" xmlns="http://www.w3.org/2000/svg">`,
  );
}

for (const t of THEMES) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <rect width="${W}" height="${H}" fill="${t.bg}"/>
  ${embedMark(LX, LY, LW, LH)}
  <g fill="${t.name}">${textGroups(font, NAME, nameSize, textX, nameBaseline)}</g>
  <g fill="${t.claim}">${textGroups(claimFont, CLAIM, claimSize, textX, claimBaseline)}</g>
</svg>
`;
  const basis = `${SLUG}-banner${t.suffix}`;
  writeFileSync(join(__dir, `${basis}.svg`), svg);
  writeFileSync(join(__dir, `${basis}.png`),
    new Resvg(svg, { background: t.bg, fitTo: { mode: "width", value: W } }).render().asPng());
  console.log(`wrote ${basis}.svg + .png`);
}
