const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const root = path.resolve(__dirname, '..')
const manifest = require('./texture-pages.json')
const textureCount = require('../whale-maid-v1.model3.json').FileReferences.Textures.length
const corePath = path.resolve(root, '../live2dcubismcore.min.js')
global.__dirname = path.dirname(corePath)
global.require = require
vm.runInThisContext(fs.readFileSync(corePath, 'utf8'))
setTimeout(() => {
  const file = path.join(root, 'whale-maid-v1.moc3')
  const bytes = fs.readFileSync(file)
  const buffer = () => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength)
  const moc = Live2DCubismCore.Moc.fromArrayBuffer(buffer())
  assert(moc, 'Model must load before repairing its texture pages')
  const model = Live2DCubismCore.Model.fromMoc(moc)
  assert.equal(model.drawables.count, Object.keys(manifest).length)
  const offset = bytes.readUInt32LE(64 + 41 * 4)
  const nextOffset = bytes.readUInt32LE(64 + 42 * 4)
  assert(offset >= 1984 && nextOffset >= offset + model.drawables.count * 4)
  for (const [index, id] of model.drawables.ids.entries()) {
    assert(Number.isInteger(manifest[id]) && manifest[id] >= 0 && manifest[id] < textureCount, id)
    bytes.writeInt32LE(manifest[id], offset + index * 4)
  }
  model.release()
  moc._release()
  const repaired = Live2DCubismCore.Moc.fromArrayBuffer(buffer())
  assert(repaired && repaired.hasMocConsistency(buffer()), 'Repaired MOC must be consistent')
  const check = Live2DCubismCore.Model.fromMoc(repaired)
  for (const [index, id] of check.drawables.ids.entries()) {
    assert.equal(check.drawables.textureIndices[index], manifest[id], id)
  }
  check.release()
  repaired._release()
  fs.writeFileSync(file, bytes)
  console.log(`Restored all ${Object.keys(manifest).length} drawable texture pages and verified Cubism consistency`)
}, 100)
