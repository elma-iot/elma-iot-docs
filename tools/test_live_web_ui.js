#!/usr/bin/env node
const {spawn}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path');
const base=process.argv[2],out=process.argv[3];
if(!base||!out)throw new Error('Usage: test_live_web_ui.js <url> <output-dir>');
fs.mkdirSync(out,{recursive:true});
const port=9334,profile=path.join(process.env.TEMP||'.',`elma-live-ui-${process.pid}`);
const chrome=spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',[
 '--headless=new','--disable-gpu','--hide-scrollbars',`--remote-debugging-port=${port}`,
 `--user-data-dir=${profile}`,'--window-size=1440,1200',base],{stdio:'ignore'});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function json(url){for(let i=0;i<60;i++){try{return await (await fetch(url)).json()}catch{await delay(200)}}throw Error('Chrome did not start')}
async function main(){
 const tabs=await json(`http://127.0.0.1:${port}/json/list`),tab=tabs.find(x=>x.type==='page'&&x.url.startsWith(base));
 const ws=new WebSocket(tab.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j});
 let id=0;const pending=new Map();ws.onmessage=e=>{const m=JSON.parse(e.data),p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.j(Error(m.error.message)):p.r(m.result)}};
 const send=(method,params={})=>new Promise((r,j)=>{const n=++id;pending.set(n,{r,j});ws.send(JSON.stringify({id:n,method,params}))});
 const evaluate=async expression=>{const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);return result.result.value};
 const drag=async(from,to)=>{await send('Input.dispatchMouseEvent',{type:'mousePressed',x:from.x,y:from.y,button:'left',buttons:1,clickCount:1});await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:to.x,y:to.y,button:'left',buttons:1});await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:to.x,y:to.y,button:'left',buttons:0,clickCount:1});await delay(200)};
 const screenshot=async name=>{const x=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(out,name),Buffer.from(x.data,'base64'))};
 await send('Page.enable');await send('Runtime.enable');await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1200,deviceScaleFactor:1,mobile:false});await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:'dark'}]});await delay(5000);
 await evaluate(`document.querySelector('[data-tab="logics"]').click();scrollTo(0,0)`);await delay(2000);
 const logics=await evaluate(`(()=>{const save=document.querySelector('[data-logic-save]'),r=save.getBoundingClientRect(),details=[...document.querySelectorAll('[data-logic-palette] details')].find(x=>x.textContent.includes('Active peripherals'));details.open=true;const opened=details.open;document.querySelector('.logic-node')?.dispatchEvent(new Event('pointerdown',{bubbles:true}));const paths=[...document.querySelectorAll('.logic-wires path')];return{saveText:save.textContent.trim(),saveVisible:getComputedStyle(save).display!=='none'&&r.width>0&&r.left>=0&&r.right<=innerWidth,saveRect:{left:r.left,right:r.right,top:r.top,width:r.width},wireCount:paths.length,wirePaths:paths.map(x=>x.getAttribute('d')),wireStrokes:paths.map(x=>x.getAttribute('stroke')),opened,closedAfterOutside:!details.open}})()`);
 await screenshot('logics-fixed.png');
 const dragTargets=await evaluate(`(()=>{const group=document.querySelector('.logic-group'),nodes=[...document.querySelectorAll('.logic-node')],head=nodes[0]?.querySelector('header'),gr=group?.getBoundingClientRect(),hr=head?.getBoundingClientRect();return{group:gr&&{x:gr.left+10,y:gr.top+14},node:hr&&{x:hr.left+Math.min(80,hr.width/2),y:hr.top+hr.height/2},before:nodes.map(n=>({id:n.dataset.id,left:parseFloat(n.style.left),top:parseFloat(n.style.top)}))}})()`);
 await drag(dragTargets.group,dragTargets.group); // Select every member through the group frame.
 await drag(dragTargets.node,{x:dragTargets.node.x+24,y:dragTargets.node.y+12});
 const afterNode=await evaluate(`[...document.querySelectorAll('.logic-node')].map(n=>({id:n.dataset.id,left:parseFloat(n.style.left),top:parseFloat(n.style.top)}))`);
 const groupPoint=await evaluate(`(()=>{const r=document.querySelector('.logic-group').getBoundingClientRect();return{x:r.left+10,y:r.top+14}})()`);
 await drag(groupPoint,{x:groupPoint.x+18,y:groupPoint.y+10});
 const afterGroup=await evaluate(`[...document.querySelectorAll('.logic-node')].map(n=>({id:n.dataset.id,left:parseFloat(n.style.left),top:parseFloat(n.style.top)}))`);
 const nodeMoved=afterNode.filter((n,i)=>Math.abs(n.left-dragTargets.before[i].left)>1||Math.abs(n.top-dragTargets.before[i].top)>1);
 const groupMoved=afterGroup.filter((n,i)=>Math.abs(n.left-afterNode[i].left)>1||Math.abs(n.top-afterNode[i].top)>1);
 logics.nodeDragMovedOnlyOne=nodeMoved.length===1;
 logics.groupDragMovedAll=groupMoved.length===afterGroup.length;
 await evaluate(`document.querySelector('[data-tab="gpio"]').click();document.querySelector('.peripheral-diagram-frame')?.scrollIntoView({block:'center'})`);await delay(2000);
 const configuration=await evaluate(`(()=>{document.querySelector('#gpioExtraToggle')?.click();const frame=document.querySelector('.peripheral-diagram-frame'),canvas=document.querySelector('.peripheral-diagram-placeholder'),viewport=document.querySelector('.diagram-viewport'),select=document.querySelector('.gpio-pin-row select[data-gpio-role-select]'),advanced=document.querySelector('.gpio-extra-shell'),paths=[...document.querySelectorAll('.peripheral-diagram-wire:not(.peripheral-diagram-wire-glow)')],scl=document.querySelector('#oledSclPin'),shownScl=document.querySelector('[data-peripheral-binding-key="oled.sclPin"]');const surface=e=>e?{color:getComputedStyle(e).backgroundColor,image:getComputedStyle(e).backgroundImage}:null;return{theme:document.documentElement.dataset.elmaTheme,frame:surface(frame),canvas:surface(canvas),viewport:surface(viewport),gpioSelect:getComputedStyle(select).backgroundColor,gpioText:select?getComputedStyle(select).color:null,advanced:getComputedStyle(advanced).backgroundColor,advancedExpanded:document.querySelector('#gpioExtraToggle')?.getAttribute('aria-expanded'),sclValue:scl?.value,sclOptions:[...(scl?.options||[])].map(x=>x.value),shownSclValue:shownScl?.value,shownSclOptions:[...(shownScl?.options||[])].map(x=>x.value),wires:paths.length,wireFilters:[...new Set(paths.map(x=>getComputedStyle(x).filter))],wireDetails:paths.map(x=>({key:x.parentElement?.dataset?.connectionKey,routePoints:x.parentElement?.dataset?.routePoints,path:x.getAttribute('d'),stroke:x.getAttribute('stroke')})),curvedPaths:paths.map(x=>x.getAttribute('d')).filter(x=>/C/i.test(x||''))}})()`);
 await screenshot('configuration-dark-fixed.png');
 console.log(JSON.stringify({logics,configuration},null,2));ws.close();
 const darkDiagram=configuration.frame?.image==='none'&&configuration.canvas?.image==='none'&&configuration.frame?.color!=='rgba(0, 0, 0, 0)'&&configuration.canvas?.color!=='rgba(0, 0, 0, 0)';
 const cleanPcmPower=configuration.wireDetails.find(x=>x.key==='audio-out:VCC:rail:5V')?.routePoints==='[]';
 if(!logics.saveVisible||logics.wireCount<3||!logics.closedAfterOutside||!logics.nodeDragMovedOnlyOne||!logics.groupDragMovedAll||!darkDiagram||!cleanPcmPower||configuration.curvedPaths.length)process.exitCode=1;
}
main().finally(async()=>{chrome.kill();await delay(300);fs.rmSync(profile,{recursive:true,force:true})}).catch(e=>{console.error(e.stack||e);process.exitCode=1});
