import {io} from 'socket.io-client';
const token=process.env.ANIMETTA_ACCESS_TOKEN;
const safe=x=>String(x).replaceAll(token,'<redacted>');
const socket=io('http://localhost',{path:'/socket.io/',transports:['websocket'],auth:{token:'invalid-r4-boundary-token'},extraHeaders:{Origin:'http://localhost'},autoConnect:false,reconnection:false,timeout:8000});
const result=await new Promise(resolve=>{
  const timeout=setTimeout(()=>{socket.disconnect();resolve({status:'blocked',reason:'Invalid-token rejection not observed within 10 seconds'});},10000);
  socket.once('connect',()=>{clearTimeout(timeout);socket.disconnect();resolve({status:'failed',invalid_token_connected:true});});
  socket.once('connect_error',e=>{clearTimeout(timeout);socket.disconnect();resolve({status:'passed',invalid_token_connected:false,rejection:safe(e.message)});});
  socket.connect();
});
process.stdout.write(JSON.stringify(result));
process.exitCode=result.status==='passed'?0:1;
