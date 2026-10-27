// Test the shipped stream parser with split UTF-8 bytes, errors and truncated streams.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync(path.join(__dirname, '../app/templates/dashboard.html'), 'utf8');
const source = html.match(/async function readRunStream\(response\)\{[\s\S]*?(?=\nfunction stopReveal)/)[0];
const events = [];
const parse = new vm.Script(source + '; readRunStream').runInNewContext({TextDecoder, Error, receiveAudit:e=>events.push(e)});
function response(text) {
  const bytes = new TextEncoder().encode(text);
  return new Response(new ReadableStream({start(controller) {
    for(let i=0; i<bytes.length; i+=3) controller.enqueue(bytes.slice(i,i+3));
    controller.close();
  }}));
}
(async()=>{
  const data = {type:'result',result:{data:{architect_spec:'Research → 开发'}}};
  const result = await parse(response(JSON.stringify({type:'event',event:{action:'stage_started'}})+'\n'+JSON.stringify({type:'heartbeat'})+'\n'+JSON.stringify(data)+'\n'));
  assert.equal(result.data.architect_spec, 'Research → 开发');
  assert.equal(events.length,1);
  await assert.rejects(parse(response('{"type":"heartbeat"}\n')), /ended before a result/);
  await assert.rejects(parse(response('{"type":"error","message":"Synthetic failure"}\n')), /Synthetic failure/);
  await assert.rejects(parse(response('invalid JSON\n')));
  console.log('Stream decoder: 4 checks passed.');
})().catch(error=>{console.error(error);process.exitCode=1});
