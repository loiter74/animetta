import { getSocket } from '@/services/socket'
import { createEarthController, type EarthSnapshot } from './controller'
import { createCesiumMap } from './adapters/cesium'
import { createEarthTransport } from './adapters/socket'
import { createNarration } from './adapters/narration'

export async function mountEarth(options: {
  container: HTMLElement
  signal: AbortSignal
  changed(snapshot: EarthSnapshot): void
  mouth(value: number): void
  playback(taskId: string, status: 'started' | 'ended' | 'cancelled'): void
}) {
  const map = await createCesiumMap(options.container, options.signal)
  const socket = getSocket()
  const controller = createEarthController({
    conversationId: crypto.randomUUID(),
    map,
    transport: createEarthTransport(socket),
    narration: createNarration({
      mouth: options.mouth,
      observed: options.playback,
      started: (taskId) => {
        void controller.playbackStarted(taskId)
      },
    }),
    changed: options.changed,
  })
  void controller.open()
  return controller
}
