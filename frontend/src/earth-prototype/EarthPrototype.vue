<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import type * as Cesium from 'cesium'
import EarthCompanion from '@/shared/live2d/Companion.vue'

declare global {
  interface Window {
    Cesium: typeof Cesium
    earthPrototype?: {
      focus: (stage: number) => Promise<void>
      pause: () => void
      getView: () => Record<string, unknown>
      capture: () => string
    }
  }
}

// Throwaway prototype: real imagery/camera, scripted guide, no LLM or home inference.
const stops = [
  {
    name: '地球',
    lon: 115,
    lat: 29,
    height: 19000000,
    why: '我们先从一个大范围开始。你记得在哪座城市，或者附近有什么吗？',
    next: null,
  },
  {
    name: '上海',
    lon: 121.47,
    lat: 31.23,
    height: 180000,
    why: '先把上海和周边放进视野，看看城市与海岸的位置。接下来我会稍微靠近，标出几个区供你辨认。',
    next: 2,
  },
  {
    name: '辨认区域',
    lon: 121.26,
    lat: 31.16,
    height: 105000,
    why: '青浦在上海西侧，闵行在中南部，浦东在东侧。这里的标签只是位置提示。你对哪一片更熟悉？',
    next: null,
  },
  {
    name: '青浦',
    lon: 121.04,
    lat: 31.15,
    height: 47000,
    why: '我们来到青浦附近。我保留周围的水系和城区，方便你对照记忆。有没有熟悉的湖，或者道路？',
    next: null,
  },
  {
    name: '淀山湖',
    lon: 120.97,
    lat: 31.105,
    height: 22000,
    why: '先看淀山湖整体轮廓，确定湖岸方向。稍后只向同一片湖区靠近一点，方便辨认沿岸细节。',
    next: 5,
  },
  {
    name: '湖岸细节',
    lon: 121.005,
    lat: 31.105,
    height: 6500,
    why: '我靠近了湖的东侧作为观察起点，这不代表你住在这里。你可以拖到熟悉的位置，点“指认这里”，再点击常走的那条路。',
    next: null,
  },
] as const
type Phase =
  '准备中' | '移动中' | '加载画面' | '解释中' | '等待反馈' | '等待你辨认' | '已暂停' | '已指认'
const globe = ref<HTMLElement>()
const stage = ref(0)
const phase = ref<Phase>('准备中')
const message = ref(stops[0].why as string)
const remaining = ref(0)
const ready = ref(false)
const error = ref('')
const input = ref('')
const spoken = ref(false)
const slow = ref(true)
const selecting = ref(false)
const settings = ref(false)
const googleKey = ref('')
const provider = ref('Esri 卫星影像')
const picked = ref('')
let viewer: Cesium.Viewer | undefined
let picker: Cesium.ScreenSpaceEventHandler | undefined
let tiles: Cesium.Cesium3DTileset | undefined
let revision = 0
let timer: ReturnType<typeof setTimeout> | undefined
let detachTileListener: (() => void) | undefined
const title = computed(() => stops[stage.value].name)
const status = computed(() =>
  remaining.value ? `${phase.value} · ${remaining.value} 秒` : phase.value,
)
const C = () => window.Cesium

function pause() {
  revision++
  clearTimeout(timer)
  detachTileListener?.()
  detachTileListener = undefined
  remaining.value = 0
  window.speechSynthesis?.cancel()
  viewer?.camera.cancelFlight()
  phase.value = '已暂停'
}

function feedback(token: number) {
  if (token !== revision) return
  if (stops[stage.value].next === null) {
    phase.value = '等待你辨认'
    return
  }
  phase.value = '等待反馈'
  remaining.value = 5
  const tick = () => {
    if (token !== revision) return
    remaining.value--
    if (remaining.value > 0) timer = setTimeout(tick, 1000)
    else {
      const next = stops[stage.value].next
      if (next !== null) void focus(next)
    }
  }
  timer = setTimeout(tick, 1000)
}

function explain(token: number) {
  if (token !== revision) return
  phase.value = '解释中'
  message.value = stops[stage.value].why
  if (spoken.value && window.speechSynthesis) {
    const utterance = new SpeechSynthesisUtterance(message.value)
    utterance.lang = 'zh-CN'
    utterance.rate = 0.9
    utterance.onend = () => feedback(token)
    utterance.onerror = () => {
      if (token === revision) timer = setTimeout(() => feedback(token), 7000)
    }
    window.speechSynthesis.speak(utterance)
  } else timer = setTimeout(() => feedback(token), 7000)
}

function settle(token: number) {
  if (token !== revision || !viewer) return
  phase.value = '加载画面'
  const loaded = () => viewer?.scene.globe.tilesLoaded && (!tiles || tiles.tilesLoaded)
  const check = () => {
    if (token !== revision || !loaded()) return
    detachTileListener?.()
    detachTileListener = undefined
    clearTimeout(timer)
    explain(token)
  }
  detachTileListener = viewer.scene.postRender.addEventListener(check)
  timer = setTimeout(() => {
    if (token !== revision) return
    pause()
    error.value = '影像仍在加载，已暂停自动移动。网络恢复后点击“继续观察”。'
  }, 20000)
  check()
}

async function focus(index: number) {
  if (!viewer || !Number.isInteger(index) || index < 0 || index >= stops.length) return
  pause()
  selecting.value = false
  error.value = ''
  stage.value = index
  const token = revision
  const stop = stops[index]
  phase.value = '移动中'
  message.value = `正在靠近${stop.name}，镜头停稳后我再解释。`
  // Camera travel is the user's requested multi-second exploration, not UI animation.
  viewer.camera.flyTo({
    destination: C().Cartesian3.fromDegrees(stop.lon, stop.lat, stop.height),
    orientation: { heading: 0, pitch: -Math.PI / 2, roll: 0 },
    duration: slow.value ? 5 : 3,
    complete: () => settle(token),
  })
}

function resume() {
  if (!viewer) return
  pause()
  error.value = ''
  settle(revision)
}

function send() {
  const text = input.value.trim()
  if (!text) return
  input.value = ''
  if (/等|停|慢/.test(text)) {
    pause()
    if (/慢/.test(text)) slow.value = true
    message.value = '好，我停在这里。你准备好后，可以继续观察或选择新的位置。'
  } else if (/淀山湖/.test(text)) void focus(4)
  else if (/青浦/.test(text)) void focus(3)
  else if (/上海/.test(text)) void focus(1)
  else if (/这条|这里|路/.test(text)) selectHere()
  else if (/继续/.test(text)) resume()
  else {
    pause()
    message.value =
      '这个原型目前识别“上海、青浦、淀山湖、这条路、暂停、继续”。你也可以直接拖动地图并点击指认。自由对话和视觉理解尚未接入。'
  }
}

function selectHere() {
  pause()
  selecting.value = true
  message.value = '请在地图上点击你说的位置。我会保持视角，标记这个点，再等你解释它。'
}

function getView() {
  const camera = viewer?.camera
  return {
    stage: title.value,
    phase: phase.value,
    provider: provider.value,
    longitude: camera ? C().Math.toDegrees(camera.positionCartographic.longitude) : null,
    latitude: camera ? C().Math.toDegrees(camera.positionCartographic.latitude) : null,
    height: camera?.positionCartographic.height,
    heading: camera?.heading,
    pitch: camera?.pitch,
    picked: picked.value,
    tilesLoaded: viewer?.scene.globe.tilesLoaded,
    scripted: true,
  }
}

async function connectGoogle() {
  if (!viewer || !googleKey.value.trim()) return
  pause()
  error.value = ''
  try {
    const nextTiles = await C().createGooglePhotorealistic3DTileset({ key: googleKey.value.trim() })
    if (tiles) viewer.scene.primitives.remove(tiles)
    tiles = viewer.scene.primitives.add(nextTiles)
    provider.value = 'Google 三维实景 + Esri 卫星底图'
    message.value = 'Google 三维接口已连接。实景覆盖取决于地区，上海示例不保证有三维建筑。'
    googleKey.value = ''
  } catch {
    error.value =
      'Google 三维接口连接失败。请检查 Map Tiles API、计费、密钥来源限制及网络。卫星底图仍可使用。'
  }
}

onMounted(async () => {
  try {
    const cesium = C()
    if (!cesium || !globe.value) throw new Error('Cesium 未加载')
    cesium.Ion.defaultAccessToken = ''
    viewer = new cesium.Viewer(globe.value, {
      baseLayer: false,
      baseLayerPicker: false,
      geocoder: false,
      timeline: false,
      animation: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      selectionIndicator: false,
      infoBox: false,
      contextOptions: { webgl: { preserveDrawingBuffer: true } },
    })
    const imagery = await cesium.ArcGisMapServerImageryProvider.fromUrl(
      'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer',
      { enablePickFeatures: false },
    )
    viewer.imageryLayers.addImageryProvider(imagery)
    imagery.errorEvent.addEventListener(() => {
      error.value = '部分卫星影像请求失败，可能暂时模糊。请等待网络恢复。'
    })
    viewer.camera.setView({ destination: cesium.Cartesian3.fromDegrees(115, 29, 19000000) })
    const accent = cesium.Color.fromCssColorString(
      getComputedStyle(document.documentElement).getPropertyValue('--c-accent').trim(),
    )
    for (const [name, lon, lat] of [
      ['上海', 121.47, 31.23],
      ['青浦', 121.12, 31.15],
      ['闵行', 121.38, 31.11],
      ['浦东', 121.65, 31.2],
      ['淀山湖', 120.97, 31.105],
    ] as const) {
      viewer.entities.add({
        position: cesium.Cartesian3.fromDegrees(lon, lat),
        point: { pixelSize: 7, color: accent },
        label: {
          text: name,
          font: '18px Microsoft YaHei',
          pixelOffset: new cesium.Cartesian2(0, -22),
          showBackground: true,
          distanceDisplayCondition: new cesium.DistanceDisplayCondition(0, 700000),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      })
    }
    picker = new cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
    picker.setInputAction((event: { position: Cesium.Cartesian2 }) => {
      if (!selecting.value || !viewer) return
      const point = viewer.camera.pickEllipsoid(event.position, viewer.scene.globe.ellipsoid)
      if (!point) return
      const geo = cesium.Cartographic.fromCartesian(point)
      picked.value = `${cesium.Math.toDegrees(geo.longitude).toFixed(5)}, ${cesium.Math.toDegrees(geo.latitude).toFixed(5)}`
      viewer.entities.removeById('user-place')
      viewer.entities.add({
        id: 'user-place',
        position: point,
        point: { pixelSize: 15, color: accent, disableDepthTestDistance: Number.POSITIVE_INFINITY },
        label: {
          text: '你指认的位置',
          font: '18px Microsoft YaHei',
          showBackground: true,
          pixelOffset: new cesium.Cartesian2(0, -28),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      })
      selecting.value = false
      phase.value = '已指认'
      message.value =
        '记住这个点了。你常沿哪一个方向走？我们可以继续对照路口和建筑。原型尚未识别道路名称，也不会推断这是你的住址。'
    }, cesium.ScreenSpaceEventType.LEFT_CLICK)
    window.earthPrototype = {
      focus,
      pause,
      getView,
      capture: () => {
        viewer?.render()
        return viewer?.scene.canvas.toDataURL('image/png') ?? ''
      },
    }
    ready.value = true
    phase.value = '等待你辨认'
  } catch (reason) {
    error.value = `地图初始化失败：${reason instanceof Error ? reason.message : String(reason)}。检查网络和 WebGL 后刷新。`
  }
})

onBeforeUnmount(() => {
  pause()
  picker?.destroy()
  viewer?.destroy()
  delete window.earthPrototype
})
</script>

<template>
  <main class="h-screen w-screen overflow-hidden bg-c-bg text-c-text font-sans flex flex-col">
    <header class="h-18 px-7 flex items-center justify-between bg-c-surface shrink-0">
      <div class="flex items-center gap-4">
        <span class="text-c-accent text-2xl">◎</span>
        <div>
          <div class="text-lg font-semibold">一起寻找熟悉的地方</div>
          <div class="text-xs text-c-text-muted mt-1">ANIMETTA · 地球探索原型</div>
        </div>
      </div>
      <div class="flex items-center gap-4 text-sm">
        <span class="text-c-text-dim">真实卫星影像 · 脚本引导</span
        ><button class="btn-ghost" @click="settings = !settings">地图接口</button>
      </div>
    </header>
    <div class="flex flex-1 min-h-0">
      <section class="relative flex-1 min-w-0" aria-label="三维地球">
        <div
          ref="globe"
          class="absolute inset-0"
          @pointerdown="pause"
          @wheel.passive="pause"
          @keydown="pause"
        />
        <EarthCompanion
          data-testid="earth-companion"
          class="absolute right-[3%] bottom-0 w-[34%] max-w-104 h-[62%] max-h-140 pointer-events-none"
        />
        <nav
          class="absolute top-5 left-5 flex gap-1 bg-c-panel/90 p-2 rounded-xl text-sm"
          aria-label="探索位置"
        >
          <button
            v-for="(stop, index) in stops"
            :key="stop.name"
            :disabled="!ready"
            class="btn-ghost"
            :class="index === stage ? 'bg-c-accent-soft text-c-accent' : ''"
            @click="focus(index)"
          >
            {{ stop.name }}
          </button>
        </nav>
        <div
          class="absolute bottom-13 left-6 box-border w-[calc(63%_-_3rem)] max-w-182 bg-c-panel/95 backdrop-blur-xl rounded-xl p-6 shadow-xl"
          aria-live="polite"
        >
          <div class="flex items-center justify-between mb-3">
            <span class="text-c-accent font-semibold">Animetta</span
            ><span class="text-xs text-c-text-muted" data-testid="phase">{{ status }}</span>
          </div>
          <p class="m-0 text-lg leading-relaxed">{{ message }}</p>
          <div v-if="remaining" class="h-1 mt-4 rounded-xl bg-c-card">
            <div class="h-full bg-c-accent rounded-xl" :style="{ width: `${remaining * 20}%` }" />
          </div>
        </div>
      </section>
      <aside class="w-80 xl:w-88 shrink-0 bg-c-surface p-6 overflow-y-auto flex flex-col gap-5">
        <div>
          <div class="text-xs text-c-text-muted tracking-widest mb-2">我们正在看</div>
          <h1 class="m-0 text-3xl">{{ title }}</h1>
          <p class="text-sm text-c-text-dim leading-relaxed">
            从模糊的记忆开始，慢慢认出你熟悉的地方。
          </p>
        </div>
        <div class="bg-c-panel rounded-xl p-4">
          <div class="text-sm mb-3">你可以这样说</div>
          <div class="flex flex-col gap-2">
            <button
              v-for="(label, index) in ['好像是在上海', '大概是青浦区', '我记得淀山湖']"
              :key="label"
              class="btn-ghost text-left bg-c-card"
              :disabled="!ready"
              @click="focus([1, 3, 4][index])"
            >
              {{ label }} ↗
            </button>
            <button class="btn-ghost text-left bg-c-card" :disabled="!ready" @click="selectHere">
              这条路我经常走 ↗
            </button>
          </div>
        </div>
        <form class="flex gap-2" @submit.prevent="send">
          <input
            v-model="input"
            aria-label="告诉 Animetta 你的线索"
            placeholder="上海、青浦、淀山湖…"
            class="min-w-0 flex-1 bg-c-panel text-c-text border-none rounded-xl p-3"
            @focus="pause"
            @input="pause"
          /><button class="btn-accent" :disabled="!ready">发送</button>
        </form>
        <div class="grid grid-cols-2 gap-2">
          <button class="btn-accent" :disabled="!ready" @click="pause">暂停</button
          ><button class="btn-ghost bg-c-panel" :disabled="!ready" @click="resume">继续观察</button
          ><button class="btn-ghost bg-c-panel" :disabled="!ready" @click="selectHere">
            {{ selecting ? '请点击地图…' : '指认这里' }}</button
          ><button
            class="btn-ghost bg-c-panel"
            :disabled="!ready"
            @click="focus(Math.max(0, stage - 1))"
          >
            返回上一层
          </button>
        </div>
        <div class="flex flex-col gap-3 text-sm text-c-text-dim">
          <label><input v-model="slow" type="checkbox" /> 慢速镜头</label
          ><label
            ><input v-model="spoken" type="checkbox" @change="pause" /> 朗读解释（系统语音）</label
          >
        </div>
        <p v-if="picked" class="text-sm text-c-mint">已指认：{{ picked }}</p>
        <p v-if="error" role="alert" class="text-sm text-c-warning leading-relaxed">{{ error }}</p>
        <div v-if="settings" class="bg-c-panel rounded-xl p-4 text-sm space-y-3">
          <div>{{ provider }}</div>
          <p class="text-c-text-dim">
            Google 实景需要开启 Map Tiles API 和计费。密钥仅用于本次页面会话，请设置 HTTP 来源与 API
            限制。
          </p>
          <input
            v-model="googleKey"
            type="password"
            autocomplete="off"
            aria-label="Google Map Tiles API 密钥"
            placeholder="输入受限 API Key"
            class="box-border w-full bg-c-card text-c-text rounded-xl p-3 border-none"
          />
          <button class="btn-accent" :disabled="!googleKey || !ready" @click="connectGoogle">
            连接 Google 实景
          </button>
        </div>
        <p class="mt-auto text-xs text-c-text-muted leading-relaxed">
          拖动或输入即暂停。只有已经选定区域内的观察会自动继续。区名为示意位置，无行政边界数据。当前未接入
          Anima 模型、视觉识别或宿主语音。
        </p>
      </aside>
    </div>
  </main>
</template>
