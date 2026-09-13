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

// Die Marke ist fuer hellen Grund gezeichnet, und auf dem dunklen Banner kostet
// das die Haelfte der Zeichnung: die beiden Aehren ueber dem Helm stehen frei
// und sind reines #1d1d1b, also unsichtbar, und die Kontur ringsum liest sich
// nicht als Linie, sondern als Luecke zwischen Gold und Grund.
//
// `tinte` faerbt die dunkle Tinte deshalb nur in der dunklen Fassung um, auf
// denselben Wert wie das Hintergrundbild des Emulators, damit Banner und Geraet
// dieselbe Figur zeigen. `auge` bleibt dunkel: cremefarbene Augen auf Gold sind
// keine Augen mehr.
const TINTE_ALT = "#1d1d1b";

const THEMES = [
  { suffix: "", bg: "#ffffff", name: "#1f2328", claim: "#5a5d5e" },
  { suffix: "-dark", bg: "#0d1117", name: "#e6edf3", claim: "#9aa4ad",
    tinte: "#615a49", auge: "#22201c" },
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

function embedMark(x, y, w, h, tinte, auge) {
  let raw = readFileSync(MARK, "utf8").replace(/<\?xml[^>]*\?>\s*/, "");
  if (tinte) {
    // Die beiden klassenlosen Pfade zuerst: sie tragen KEIN fill-Attribut, sind
    // also per SVG-Vorgabe schwarz, und ein Ersetzen der Farbwerte allein
    // laesst sie unberuehrt. Es sind Koerperkontur und Strohlinien, zusammen
    // der groesste Schwarzanteil der Zeichnung.
    raw = raw.split("<path d=").join(`<path fill="${tinte}" d=`);
    raw = raw.split(TINTE_ALT).join(tinte);
    // Die Augen per style, nicht per fill: ein fill-Attribut ist eine
    // Praesentationsangabe und steht in der SVG-Kaskade UNTER einer Regel aus
    // dem <style>-Block, also wuerde .cls-3 es ueberstimmen.
    raw = raw.split('<circle class="cls-3"').join(`<circle class="cls-3" style="fill:${auge}"`);
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
  ${embedMark(LX, LY, LW, LH, t.tinte, t.auge)}
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

// The support thread's banner: the mark alone, centred on white, no text at
// all. It is generated in the same run rather than kept around from an earlier
// one, so it cannot drift away from the mark the other two show.
{
  const h = 420;
  const w = h * (339.95 / 458.74);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${NAME}">
  <rect width="${W}" height="${H}" fill="#ffffff"/>
  ${embedMark((W - w) / 2, (H - h) / 2, w, h)}
</svg>
`;
  const basis = `${SLUG}-banner-logo`;
  writeFileSync(join(__dir, `${basis}.svg`), svg);
  writeFileSync(join(__dir, `${basis}.png`),
    new Resvg(svg, { background: "#ffffff", fitTo: { mode: "width", value: W } }).render().asPng());
  console.log(`wrote ${basis}.svg + .png`);
}
