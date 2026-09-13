// Rasterise an SVG onto a solid ground, so the mark can be judged the way it
// will actually be seen: on the dark surface, not on the white of a viewer.
// ESM ignores NODE_PATH, so the globally installed package is imported by its
// absolute path rather than by name.
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
