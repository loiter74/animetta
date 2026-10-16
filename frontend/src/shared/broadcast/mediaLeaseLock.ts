import type { PublicMediaLockManager } from './mediaOwnership'

const STORE = 'owners'
const LEASE_MS = 5000
const RENEW_MS = 1000

export interface MediaLeaseStore {
  update(name: string, owner: string, renew: boolean): Promise<number>
  release(name: string, owner: string): Promise<void>
}

function indexedDbLeaseStore(factory: IDBFactory): MediaLeaseStore {
  let database: Promise<IDBDatabase> | null = null
  const open = (): Promise<IDBDatabase> =>
    (database ??= new Promise<IDBDatabase>((resolve, reject) => {
      const request = factory.open('animetta-media-owner', 1)
      request.onupgradeneeded = () => request.result.createObjectStore(STORE)
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
      request.onblocked = () => reject(new Error('Media ownership database unavailable'))
    }))
  const transact = async (
    name: string,
    owner: string,
    renew: boolean,
    release = false,
  ): Promise<number> => {
    const db = await open()
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE, 'readwrite')
      const store = transaction.objectStore(STORE)
      const request = store.get(name)
      let deadline = 0
      request.onsuccess = () => {
        const current = request.result as { owner: string; deadline: number } | undefined
        if (release) {
          if (current?.owner === owner) store.delete(name)
        } else {
          const now = Date.now()
          const available = !current || current.deadline <= now
          if (renew ? current?.owner === owner && !available : available) {
            deadline = now + LEASE_MS
            store.put({ owner, deadline }, name)
          }
        }
      }
      transaction.oncomplete = () => resolve(deadline)
      transaction.onabort = () => reject(transaction.error)
      transaction.onerror = () => reject(transaction.error)
    })
  }
  return {
    update: (name, owner, renew) => transact(name, owner, renew),
    release: async (name, owner) => {
      await transact(name, owner, false, true)
    },
  }
}

export function createIndexedDbMediaLockManager(
  factory: IDBFactory,
  store: MediaLeaseStore = indexedDbLeaseStore(factory),
): PublicMediaLockManager {
  // Web Locks requires a secure context; IndexedDB transactions also work on LAN HTTP.
  return {
    async request(name, _options, callback) {
      const owner = `${Date.now()}:${Math.random()}`
      let deadline = await store.update(name, owner, false)
      if (!deadline) {
        await callback(null)
        return
      }
      const controller = new AbortController()
      let expiryTimer: ReturnType<typeof setTimeout>
      const armExpiry = (): void => {
        clearTimeout(expiryTimer)
        expiryTimer = setTimeout(() => controller.abort(), Math.max(0, deadline - Date.now()))
      }
      armExpiry()
      let renewing = false
      const renewTimer = setInterval(() => {
        if (renewing || controller.signal.aborted) return
        if (Date.now() >= deadline) {
          controller.abort()
          return
        }
        renewing = true
        void store
          .update(name, owner, true)
          .then((nextDeadline) => {
            if (!nextDeadline || controller.signal.aborted) controller.abort()
            else {
              deadline = nextDeadline
              armExpiry()
            }
          })
          .catch(() => controller.abort())
          .finally(() => {
            renewing = false
          })
      }, RENEW_MS)
      try {
        await callback({
          name,
          signal: controller.signal,
          isValid: () => !controller.signal.aborted && Date.now() < deadline,
        })
      } finally {
        controller.abort()
        clearInterval(renewTimer)
        clearTimeout(expiryTimer!)
        await store.release(name, owner)
      }
    },
  }
}
