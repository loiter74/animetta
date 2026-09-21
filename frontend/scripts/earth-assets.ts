import { readFile, readdir } from 'node:fs/promises'
import { resolve, relative, extname } from 'node:path'
import type { Plugin } from 'vite'

/** Serve the same pinned, self-hosted Cesium distribution in development and builds. */
export function earthAssets(): Plugin {
  const root = resolve(import.meta.dirname, '../node_modules/cesium/Build/Cesium')
  const prefix = '/earth/cesium/'
  const mime: Record<string, string> = {
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.svg': 'image/svg+xml',
    '.wasm': 'application/wasm',
    '.jpg': 'image/jpeg',
  }
  return {
    name: 'earth-assets',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (!req.url?.startsWith(prefix)) return next()
        const path = resolve(root, decodeURIComponent(req.url.slice(prefix.length).split('?')[0]))
        if (relative(root, path).startsWith('..')) {
          res.statusCode = 403
          res.end()
          return
        }
        try {
          const body = await readFile(path)
          res.setHeader('Content-Type', mime[extname(path)] ?? 'application/octet-stream')
          res.end(body)
        } catch {
          res.statusCode = 404
          res.end()
        }
      })
    },
    async generateBundle() {
      for (const file of await readdir(root, { recursive: true, withFileTypes: true })) {
        if (!file.isFile()) continue
        const absolute = resolve(file.parentPath, file.name)
        this.emitFile({
          type: 'asset',
          fileName: `earth/cesium/${relative(root, absolute).replaceAll('\\', '/')}`,
          source: await readFile(absolute),
        })
      }
    },
  }
}
