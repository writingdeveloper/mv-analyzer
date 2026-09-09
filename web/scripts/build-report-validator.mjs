import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import Ajv2020 from 'ajv/dist/2020.js'
import standalone from 'ajv/dist/standalone/index.js'

const schemaPath = new URL('../../mv_analyzer/schemas/analyze-report.schema.json', import.meta.url)
const outputPath = new URL('../src/data/reportValidator.mjs', import.meta.url)
const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf8'))
const ajv = new Ajv2020({ strict: false, allErrors: false, code: {source:true,esm:true} })
const validate = ajv.compile(schema)
let code = standalone(ajv,validate)
// Ajv's generated runtime helpers use CJS even in ESM mode; make them explicit
// imports so the Vite bundle has no require() or runtime code generation.
code = code.replace(/const (\w+) = require\("([^"\n]+)"\)\.default;/g, (_m,name,path) => `import ${name}Module from "${path}.js"; const ${name}=typeof ${name}Module==="function"?${name}Module:${name}Module.default;`)
if (/require\(/.test(code)) throw new Error('Unhandled Ajv runtime helper; do not ship an unresolved require')
code = '// Generated from mv_analyzer/schemas/analyze-report.schema.json. Do not edit.\n' + code + '\n'
if (process.argv.includes('--check')) {
  if (!fs.existsSync(outputPath) || fs.readFileSync(outputPath,'utf8').replace(/\r\n/g,'\n') !== code) throw new Error('Report validator drift')
} else fs.writeFileSync(outputPath,code)
console.log('CSP-safe report validator:',fileURLToPath(outputPath))
