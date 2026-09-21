/** Explicit private utterance capture, with no public chat transport dependency. */
export function createMicrophone(options: {
  started(): void
  captured(data: string, format: string): void
  changed(recording: boolean): void
  failed(message: string): void
}) {
  let stream: MediaStream | undefined
  let recorder: MediaRecorder | undefined
  let generation = 0
  let busy = false
  let timer: ReturnType<typeof setTimeout> | undefined
  const release = () => {
    clearTimeout(timer)
    stream?.getTracks().forEach((track) => track.stop())
    stream = undefined
  }
  return {
    async start() {
      if (busy) return
      busy = true
      const token = ++generation
      options.started()
      options.changed(true)
      try {
        const acquired = await navigator.mediaDevices.getUserMedia({
          audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
        })
        if (token !== generation) {
          acquired.getTracks().forEach((track) => track.stop())
          return
        }
        stream = acquired
        const mimeType = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus'].find((value) =>
          MediaRecorder.isTypeSupported(value),
        )
        if (!mimeType) throw new Error('此浏览器不支持私密录音，请使用文字输入')
        const chunks: Blob[] = []
        recorder = new MediaRecorder(stream, { mimeType })
        recorder.ondataavailable = (event) => chunks.push(event.data)
        recorder.onstop = async () => {
          if (token !== generation) {
            acquired.getTracks().forEach((track) => track.stop())
            return
          }
          release()
          busy = false
          options.changed(false)
          const blob = new Blob(chunks, { type: mimeType })
          if (blob.size > 8 * 1024 * 1024) {
            options.failed('录音过长，请分段描述')
            return
          }
          const bytes = new Uint8Array(await blob.arrayBuffer())
          if (token !== generation) return
          let binary = ''
          for (let offset = 0; offset < bytes.length; offset += 8192)
            binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192))
          options.captured(btoa(binary), mimeType.includes('ogg') ? 'ogg' : 'webm')
        }
        recorder.start()
        options.changed(true)
        timer = setTimeout(() => {
          if (recorder?.state === 'recording') recorder.stop()
        }, 60000)
      } catch (error) {
        if (token !== generation) return
        release()
        busy = false
        options.changed(false)
        options.failed(error instanceof Error ? error.message : '麦克风不可用')
      }
    },
    stop() {
      if (recorder?.state === 'recording') recorder.stop()
      else {
        generation++
        busy = false
        release()
        options.changed(false)
      }
    },
    dispose() {
      generation++
      busy = false
      if (recorder?.state === 'recording') recorder.stop()
      release()
    },
  }
}
