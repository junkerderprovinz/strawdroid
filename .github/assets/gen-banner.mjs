/**
 * Generates the light and dark StrawDroid banners, 1600x500, on the pattern of
 * glimstone's gen-banner.mjs: the mark on the left, the name in Bree Serif and
 * the claim in Lato. Text is turned into SVG paths with opentype.js so the
 * banner looks the same everywhere without a font.
 *
 * Deps (global): opentype.js, @resvg/resvg-js. The fonts are downloaded once to
 * the temp dir.
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

const SLUG = "strawdroid";
const NAME = "StrawDroid";
const CLAIM = "A phone you can break.";
const MARK = join(__dir, "..", "..", "assets", "strawdroid.svg");

const W = 1600, H = 500;
const LH = 420, LW = 420;
const nameSize = 132, claimSize = 44, gap = 70, lineGap = 8;

// The mark is drawn for a light ground. On the dark banner the two free-standing
// ears of straw above the helmet are pure #1d1d1b and vanish, and the outline
// reads as a gap between gold and ground. So the dark theme recolours the ink
// to the tone of the emulator wallpaper, while the eyes stay dark: cream eyes on
// gold stop reading as eyes.
const OLD_INK = "#1d1d1b";

const THEMES = [
  { suffix: "", bg: "#ffffff", name: "#1f2328", claim: "#5a5d5e" },
  { suffix: "-dark", bg: "#0d1117", name: "#e6edf3", claim: "#9aa4ad",
    ink: "#615a49", eye: "#22201c" },
];

async function loadFont(file, url) {
  const p = join(tmpdir(), file);
  if (!existsSync(p)) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`font fetch ${r.status} for ${file}`);
    writeFileSync(p, Buffer.from(await r.arrayBuffer()));
  }
  return opentype.parse(readFileSync(p));
}

const font = await loadFont("Haus-BreeSerif-Regular.ttf",
  "https://github.com/google/fonts/raw/main/ofl/breeserif/BreeSerif-Regular.ttf");
const claimFont = await loadFont("Haus-Lato-Regular.ttf",
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

function embedMark(x, y, w, h, ink, eye) {
  let raw = readFileSync(MARK, "utf8").replace(/<\?xml[^>]*\?>\s*/, "");
  if (ink) {
    // The two paths without a class, the body outline and the straw lines,
    // carry no fill attribute and default to black, so replacing colour values
    // alone would miss them.
    raw = raw.split("<path d=").join(`<path fill="${ink}" d=`);
    raw = raw.split(OLD_INK).join(ink);
    // A style rather than a fill attribute, because the .cls-3 rule in the
    // <style> block outranks a presentation attribute.
    raw = raw.split('<circle class="cls-3"').join(`<circle class="cls-3" style="fill:${eye}"`);
  }
  const vb = (raw.match(/viewBox="([^"]+)"/) || [, "0 0 1000 1000"])[1];
  return raw.replace(
    /<svg\b[^>]*>/,
    `<svg x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${w}" height="${h}" viewBox="${vb}" xmlns="http://www.w3.org/2000/svg">`,
  );
}

for (const t of THEMES) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <rect width="${W}" height="${H}" fill="${t.bg}"/>
  ${embedMark(LX, LY, LW, LH, t.ink, t.eye)}
  <g fill="${t.name}">${textGroups(font, NAME, nameSize, textX, nameBaseline)}</g>
  <g fill="${t.claim}">${textGroups(claimFont, CLAIM, claimSize, textX, claimBaseline)}</g>
</svg>
`;
  const base = `${SLUG}-banner${t.suffix}`;
  writeFileSync(join(__dir, `${base}.svg`), svg);
  writeFileSync(join(__dir, `${base}.png`),
    new Resvg(svg, { background: t.bg, fitTo: { mode: "width", value: W } }).render().asPng());
  console.log(`wrote ${base}.svg + .png`);
}

// The support thread's banner is the mark alone, centred on white. It is
// generated in the same run so it cannot drift from the other two.
{
  const h = 420;
  const w = h * (339.95 / 458.74);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${NAME}">
  <rect width="${W}" height="${H}" fill="#ffffff"/>
  ${embedMark((W - w) / 2, (H - h) / 2, w, h)}
</svg>
`;
  const base = `${SLUG}-banner-logo`;
  writeFileSync(join(__dir, `${base}.svg`), svg);
  writeFileSync(join(__dir, `${base}.png`),
    new Resvg(svg, { background: "#ffffff", fitTo: { mode: "width", value: W } }).render().asPng());
  console.log(`wrote ${base}.svg + .png`);
}
