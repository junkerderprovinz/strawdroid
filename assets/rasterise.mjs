// Rasterises an SVG onto a solid ground, so the mark can be judged on the dark
// surface it is shown on rather than on a viewer's white. ESM ignores
// NODE_PATH, so the global package is imported by its absolute path.
import { readFileSync, writeFileSync } from 'node:fs'
import { execSync } from 'node:child_process'
import { pathToFileURL } from 'node:url'

const groot = execSync('npm root -g').toString().trim()
const { Resvg } = await import(pathToFileURL(`${groot}/@resvg/resvg-js/index.js`).href)

const [, , src, out, width, bg] = process.argv
const svg = readFileSync(src, 'utf8')
const r = new Resvg(svg, {
  fitTo: { mode: 'width', value: Number(width) },
  background: bg || 'transparent',
})
writeFileSync(out, r.render().asPng())
console.log(out)
