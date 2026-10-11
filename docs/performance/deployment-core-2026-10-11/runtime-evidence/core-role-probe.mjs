
import { chromium } from 'playwright'; import { io } from 'socket.io-client'; import { randomUUID } from 'node:crypto';
const token=process.env.ANIMETTA_ACCESS_TOKEN,base=new URL('http://localhost'),safe=x=>String(x).replaceAll(token,'[redacted]');
const task=randomUUID(),payload={text:'请用一句自然中文，冷静但明显开心地告诉我今天值得期待。',message_id:randomUUID(),conversation_id:randomUUID(),task_id:task,turn_id:task,source:'text',is_inspection:false,is_acceptance:false};
const p={schema_version:1,run_id:'c-dc2-role01',started_at:new Date().toISOString(),url:base.href,authentication:'documented Socket.IO auth.token; secret from child env',command_event:'chat:developer_text',command:payload,events:[],errors:[],dashboard_writer_ui_missing:'No account login credentials; browser bearer does not authenticate its WebSocket. Prior UI probes preserved.'};
const browser=await chromium.launch({headless:true}),context=await browser.newContext({extraHTTPHeaders:{Authorization:`Bearer ${token}`}});
await context.route('**/*',route=>new URL(route.request().url()).origin===base.origin?route.continue():route.abort('blockedbyclient'));
await context.addInitScript(() => {
  const qa = {
    events: [],
    audio_starts: [],
    audio_contexts: 0,
    legacy_play_calls: 0,
    ws_connections: 0,
    last_socket: null,
    last_identity: null,
  }
  window.__ttsQa = qa

  const safeIdentity = (data) => ({
    message_id: data?.message_id,
    conversation_id: data?.conversation_id,
    task_id: data?.task_id,
    turn_id: data?.turn_id,
  })
  const recordFrame = (raw, direction, socket) => {
    if (typeof raw !== 'string') return;
    if (direction === 'received' && raw.startsWith('40')) qa.socket_accepted = true;
    if (direction === 'received' && raw.startsWith('44')) qa.socket_error = raw.slice(2,300);
    if (!raw.startsWith('42')) return
    try {
      const packet = JSON.parse(raw.slice(2))
      const name = packet[0]
      const data = packet[1] ?? {}
      const allowed = new Set([
        'chat:text',
        'chat:developer_text',
        'system:error',
        'chat:control',
        'chat:sentence',
        'chat:interrupt',
        'chat:audio_stream_start',
        'chat:audio_stream_chunk',
        'chat:audio_stream_end',
        'chat:audio_with_expression',
        'chat:stop_audio',
      ])
      if (!allowed.has(name)) return
      const event = {
        direction,
        name,
        at_ms: performance.now(),
        epoch_ms: Date.now(),
        ...safeIdentity(data),
      }
      if (name === 'chat:audio_stream_start') {
        Object.assign(event, {
          stream_id: data.stream_id,
          format: data.format,
          sample_rate: data.sample_rate,
          channels: data.channels,
          emotion: data.emotion,
        })
      } else if (name === 'chat:audio_stream_chunk') {
        Object.assign(event, {
          stream_id: data.stream_id,
          sequence: data.sequence,
          encoded_length: typeof data.audio_data === 'string' ? data.audio_data.length : 0,
        })
      } else if (name === 'chat:audio_stream_end') {
        Object.assign(event, {
          stream_id: data.stream_id,
          final_sequence: data.final_sequence,
          status: data.status,
          reason: data.reason,
        })
      }
      if (name === 'chat:sentence') event.text = data.text ?? data.sentence ?? null;
      if (name === 'system:error') event.error = {code:data.code,message:data.message,component:data.component,phase:data.phase};
      if (direction === 'received' && ['chat:audio_stream_start','chat:audio_with_expression'].includes(name)) qa.last_identity=safeIdentity(data);
      qa.events.push(event)
      if (direction === 'sent' && ['chat:text','chat:developer_text'].includes(name)) {
        qa.last_socket = socket
        qa.last_identity = safeIdentity(data)
      }
    } catch {
      // Engine.IO control frames and non-JSON traffic are irrelevant here.
    }
  }

  const NativeWebSocket = window.WebSocket
  class ObservedWebSocket extends NativeWebSocket {
    constructor(...args) {
      super(...args)
      qa.ws_connections += 1
      this.addEventListener('message', (event) => recordFrame(event.data, 'received', this))
    }

    send(data) {
      recordFrame(data, 'sent', this)
      return super.send(data)
    }
  }
  window.WebSocket = ObservedWebSocket
  window.__interruptTtsQaTurn = () => {
    if (!qa.last_socket || !qa.last_identity) throw new Error('No active chat identity')
    qa.last_socket.send(`42${JSON.stringify(['chat:interrupt', qa.last_identity])}`)
  }

  const NativeAudioContext = window.AudioContext
  window.AudioContext = class ObservedAudioContext extends NativeAudioContext {
    constructor(...args) {
      super(...args)
      qa.audio_contexts += 1
    }
  }

  let nextSourceId = 1
  const sourceEntries = new WeakMap()
  const nativeStart = AudioBufferSourceNode.prototype.start
  AudioBufferSourceNode.prototype.start = function (when = 0, ...args) {
    const samples = this.buffer?.getChannelData(0) ?? new Float32Array()
    let energy = 0
    for (const sample of samples) energy += sample * sample
    const entry = {
      id: nextSourceId++,
      wall_at_ms: performance.now(),
      epoch_ms: Date.now(),
        epoch_ms: Date.now(),
      scheduled_at: Number(when),
      duration: Number(this.buffer?.duration ?? 0),
      rms: samples.length > 0 ? Math.sqrt(energy / samples.length) : 0,
      context_state: this.context.state,
      task_id: qa.last_identity?.task_id ?? null,
      stopped: false,
      ended: false,
    }
    sourceEntries.set(this, entry)
    qa.audio_starts.push(entry)
    this.addEventListener(
      'ended',
      () => {
        entry.ended = true
        entry.ended_at_ms = performance.now()
      },
      { once: true },
    )
    return nativeStart.call(this, when, ...args)
  }
  const nativeStop = AudioBufferSourceNode.prototype.stop
  AudioBufferSourceNode.prototype.stop = function (...args) {
    const entry = sourceEntries.get(this)
    if (entry) {
      entry.stopped = true
      entry.stopped_at_ms = performance.now()
    }
    return nativeStop.apply(this, args)
  }

  const nativePlay = HTMLMediaElement.prototype.play
  HTMLMediaElement.prototype.play = function (...args) {
    qa.legacy_play_calls += 1
    return nativePlay.apply(this, args)
  }
});

const live=await context.newPage();live.on('pageerror',e=>p.errors.push(safe(e.message)));live.on('console',e=>{if(e.type()==='error')p.errors.push(safe(e.text()))});
const sock=io(base.origin,{path:'/socket.io/',transports:['websocket'],auth:{token},extraHeaders:{Origin:base.origin},autoConnect:false,reconnection:false,timeout:15000});
sock.onAny((name,data)=>{if(['chat:sentence','chat:control','system:error','chat:audio_stream_start','chat:audio_stream_end','chat:audio_with_expression'].includes(name))p.events.push({name,epoch_ms:Date.now(),task_id:data?.task_id,text:name==='chat:sentence'?data?.text:null,status:data?.status,error:name==='system:error'?data:null})});
try{
 await live.goto(new URL('/live.html',base).href,{waitUntil:'domcontentloaded'});await live.locator('#socketStatus[data-state="connected"]').waitFor({timeout:45000});await live.locator('#modelStatus[data-state="live"]').waitFor({timeout:45000});await live.locator('body').click({position:{x:20,y:20}});p.live_before=await live.locator('#audioStatus').evaluate(e=>({...e.dataset}));
 await new Promise((res,rej)=>{sock.once('connect',res);sock.once('connect_error',e=>rej(new Error('Socket auth rejected: '+safe(e.message))));sock.connect()});p.socket_authenticated=true;p.sent_at_ms=Date.now();sock.emit('chat:developer_text',payload);
 const deadline=Date.now()+120000;
 while(Date.now()<deadline){p.live_after=await live.locator('#audioStatus').evaluate(e=>({...e.dataset}));if(p.live_after.lastAudioTaskId===task&&Number(p.live_after.playbackCount)>Number(p.live_before.playbackCount??0)&&p.live_after.playbackState==='completed')break;const err=p.events.find(e=>e.name==='system:error'&&(e.task_id===task||!e.task_id));if(err){p.task_error=err;break}await new Promise(res=>setTimeout(res,200))}
 p.live_observations=await live.evaluate(()=>{const q=window.__ttsQa;return {identity:q.last_identity,events:q.events,audio_starts:q.audio_starts,audio_contexts:q.audio_contexts,legacy_play_calls:q.legacy_play_calls,ws_connections:q.ws_connections,socket_accepted:q.socket_accepted,socket_error:q.socket_error}});
 p.live_persistent_playback=!!p.live_after&&p.live_after.lastAudioTaskId===task&&Number(p.live_after.playbackCount)>Number(p.live_before.playbackCount??0)&&p.live_after.playbackState==='completed';
 const reply=p.events.find(e=>e.name==='chat:sentence'&&e.task_id===task),audio=p.live_observations.audio_starts.find(a=>a.task_id===task&&a.rms>0&&a.context_state==='running');p.first_reply_seconds=reply?(reply.epoch_ms-p.sent_at_ms)/1000:null;p.first_native_audio_start_seconds=audio?(audio.epoch_ms-p.sent_at_ms)/1000:null;p.native_nonzero_audio_completed=p.live_observations.audio_starts.some(a=>a.task_id===task&&a.rms>0&&a.context_state==='running'&&a.ended&&!a.stopped);

 p.live2d=await live.evaluate(()=>{const model=document.querySelector('#modelStatus'),canvas=document.querySelector('#live2dCanvas'),audio=document.querySelector('#audioStatus');return {model_status:model?.dataset.state,model_text:model?.textContent,canvas_width:canvas?.width,canvas_height:canvas?.height,canvas_bounds:canvas?.getBoundingClientRect().toJSON(),audio_dataset:audio?{...audio.dataset}:null}});
 p.live2d_model_runtime_loaded=p.live2d.model_status==='live'&&p.live2d.canvas_width>0&&p.live2d.canvas_height>0;
 p.live2d_real_task_mouth_applied=p.live_after.lastLipSyncTaskId===task&&Number(p.live_after.lipSyncAppliedCount)>Number(p.live_before.lipSyncAppliedCount??0)&&Number(p.live_after.lipSyncPeak)>0.02;
 p.status=p.live_persistent_playback&&reply&&p.native_nonzero_audio_completed?'passed':'blocked';
 if(p.status==='passed'){
  const code='青竹'+randomUUID().replaceAll('-','').slice(0,8),conversation=payload.conversation_id;
  p.continuity={code,conversation_id:conversation,socket_id:sock.id,scope:'short-term same socket/logical conversation; production long_term_memory_mode off unchanged',rounds:[]};
  for(const [name,text] of [['code-set',`本轮验收代号是${code}。请用一句简短中文确认记住。`],['code-recall','刚才我告诉你的本轮验收代号是什么？请原样给出。']]){
   const turnTask=randomUUID(),command={...payload,text,message_id:randomUUID(),task_id:turnTask,turn_id:turnTask,conversation_id:conversation};
   const before=await live.locator('#audioStatus').evaluate(e=>({...e.dataset})),round={name,command,socket_id_before:sock.id,before,sent_at_ms:Date.now()};
   sock.emit('chat:developer_text',command);
   await live.waitForFunction(({task,count})=>{const e=document.querySelector('#audioStatus');return e?.dataset.lastAudioTaskId===task&&Number(e?.dataset.playbackCount)>count&&e?.dataset.playbackState==='completed'},{task:turnTask,count:Number(before.playbackCount??0)},{timeout:120000});
   round.after=await live.locator('#audioStatus').evaluate(e=>({...e.dataset}));round.socket_id_after=sock.id;
   round.events=p.events.filter(e=>e.task_id===turnTask);round.actual_reply=round.events.filter(e=>e.name==='chat:sentence').map(e=>e.text??'').join('');
   round.same_socket_and_conversation=round.socket_id_before===p.continuity.socket_id&&round.socket_id_after===p.continuity.socket_id&&command.conversation_id===conversation;
   round.native_audio=await live.evaluate(t=>window.__ttsQa.audio_starts.filter(a=>a.task_id===t),turnTask);
   round.real_native_completed=round.native_audio.some(a=>a.rms>0&&a.context_state==='running'&&a.ended&&!a.stopped);
   round.completed_at=new Date().toISOString();p.continuity.rounds.push(round);
  }
  p.continuity.actual_recalled_reply=p.continuity.rounds[1].actual_reply;
  p.continuity.code_recalled=p.continuity.actual_recalled_reply.includes(code);
  p.continuity.status=p.continuity.code_recalled&&p.continuity.rounds.every(r=>r.same_socket_and_conversation&&r.real_native_completed)?'passed':'failed';
 }

}catch(e){p.status='blocked';p.error=safe(e.message)}finally{sock.disconnect();p.finished_at=new Date().toISOString();await browser.close();process.stdout.write(JSON.stringify(p))}
