'use strict';
const out=document.getElementById('out'),markButton=document.getElementById('mark');
const fields=['year','component','work','question_type','question','passage','response'];
const esc=x=>String(x??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const MAX_WORDS=1000;
let activeJob=null,view='new',latestReport=null,lastJob=null,submitting=false;
function wordCount(){const text=document.getElementById('response').value.trim();return text?text.split(/\s+/u).length:0}
function updateWordCount(){
 const count=wordCount(),over=count>MAX_WORDS,counter=document.getElementById('response-count');
 counter.textContent=count+' of 1000 words'+(over?' remove '+(count-MAX_WORDS)+' '+(count-MAX_WORDS===1?'word':'words'):'');
 counter.style.color=over?'#b83250':'';
 document.getElementById('response').setAttribute('aria-invalid',String(over));
 markButton.disabled=Boolean(activeJob)||submitting||over;
}
function readForm(){return Object.fromEntries(fields.map(id=>[id,id==='year'?+document.getElementById(id).value:document.getElementById(id).value]))}
function restore(payload){for(const id of fields)if(payload?.[id]!=null)document.getElementById(id).value=payload[id]}
function storeValue(key,value){try{localStorage.setItem(key,JSON.stringify(value))}catch{}}
function loadValue(key){try{return JSON.parse(localStorage.getItem(key)||'null')}catch{return null}}
function removeValue(key){try{localStorage.removeItem(key)}catch{}}
restore(loadValue('marginDraft'));
fields.forEach(id=>document.getElementById(id).addEventListener('input',()=>{storeValue('marginDraft',readForm());updateWordCount()}));
async function fetchJSON(url,options={}){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
 try{const response=await fetch(url,{...options,signal:controller.signal,cache:'no-store'});
 const body=await response.json();if(!response.ok){const error=Error(body.error||'Request failed');error.status=response.status;throw error}return body}
 finally{clearTimeout(timer)}
}
function empty() {
  out.className = '';
  out.innerHTML = '<h2>output</h2><p class="small">your marking will appear here</p>';
}
function attention(message, payload) {
  out.className = '';
  out.innerHTML = `<h2>output</h2><p>${esc(message)}</p><p class="small">your answer is saved</p><button class="button" id="retry">try again</button>`;
  document.getElementById('retry').onclick = () => {
    if (payload) restore(payload);
    startAssessment();
  };
}
function progress(job) {
  lastJob = job;
  if (view !== 'new') return;
  const seconds = job.elapsed_seconds || 0;
  out.className = '';
  out.innerHTML = `<h2>output</h2>
    <p>marking your answer</p>
    <p>${esc(job.stage)}</p>
    <p class="small">${Math.floor(seconds / 60)} minutes ${seconds % 60} seconds</p>
    ${job.tokens ? `<p class="small">${esc(job.tokens)} tokens generated</p>` : ''}
    <p class="small">your answer is saved and marking continues if you leave this page</p>
    <p class="small">keep the server running and your computer awake</p>`;
}
async function pollJob(){
 if(!activeJob)return;
 try{
  const job=await fetchJSON('/api/jobs/'+encodeURIComponent(activeJob));lastJob=job;
  if(job.state==='complete'){activeJob=null;removeValue('marginActiveJob');updateWordCount();report(job.result,job.payload);return}
  if(job.state==='failed'){activeJob=null;removeValue('marginActiveJob');updateWordCount();attention(job.error,job.payload);return}
  progress(job);
 }catch(error){
  if(error.status===404){activeJob=null;removeValue('marginActiveJob');updateWordCount();attention('The previous assessment job could not be found. Your browser draft is preserved.',loadValue('marginDraft'));return}
  if(view==='new'){out.className='panel';out.innerHTML='<h2>output</h2><p>reconnecting</p><p class="small">your answer is saved</p><p class="small">if the server stopped start it again and this page will reconnect</p>'}
 }
 setTimeout(pollJob,2500);
}
async function startAssessment(){
 if(activeJob)return;view='new';selectChips();
 const payload=readForm();storeValue('marginDraft',payload);
 if(wordCount()>MAX_WORDS){updateWordCount();return}
 if(!payload.question.trim()||!payload.response.trim()){attention('Enter both the exact question and the complete response.',payload);return}
 submitting=true;updateWordCount();
 const pending=loadValue('marginPendingRequest');
 const requestId=pending&&JSON.stringify(pending.payload)===JSON.stringify(payload)?pending.request_id:crypto.randomUUID();
 storeValue('marginPendingRequest',{request_id:requestId,payload});
 progress({stage:'Saving your response and starting assessment',elapsed_seconds:0});
 try{
  const result=await fetchJSON('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({assessment:payload,request_id:requestId})});
  activeJob=result.job_id;storeValue('marginActiveJob',activeJob);removeValue('marginPendingRequest');pollJob();
 }catch(error){attention(error.message,payload)}
 finally{submitting=false;updateWordCount()}
}
function selectChips(){document.querySelectorAll('.chip').forEach(x=>{const selected=x.dataset.view===view;x.classList.toggle('active',selected);x.setAttribute('aria-current',selected?'page':'false')})}
function setView(v){view=v;selectChips();document.getElementById('workspace').scrollIntoView({behavior:'auto'});if(v==='saved')showSaved();else if(v==='library')showLibrary();else if(activeJob&&lastJob)progress(lastJob);else if(latestReport)report(latestReport.report,latestReport.payload);else empty()}
document.querySelectorAll('[data-view]').forEach(x=>x.onclick=()=>setView(x.dataset.view));
function report(r, payload) {
  latestReport = {report: r, payload};
  const a = r.assessment || {};
  const result = r.result || {};
  const paragraphs = r.semantic_paragraph_reviews || [];
  const objectives = r.ao_indicators || [];
  const notes = r.line_feedback || [];
  const section = (title, text) => text ? `<h3>${esc(title)}</h3><p>${esc(text)}</p>` : '';

  out.className = '';
  out.innerHTML = `<h2>output</h2>
    <p>mark ${esc(result.mark ?? 'not available')} out of ${esc(result.maximum_mark || 25)}<br>level ${esc(result.indicative_level ?? 'not available')}</p>
    <p class="context">${esc(a.work)} ${esc(a.question_type)} ${esc(a.year)} component ${esc(a.component)}</p>
    ${section('question', a.question)}
    ${section('overall feedback', r.examiner_judgement)}
    ${section('strengths', r.strengths)}
    ${section('what would improve the mark', r.next_band)}
    <h3>paragraph feedback</h3>
    ${paragraphs.length ? paragraphs.map(p => `<p>paragraph ${esc(p.paragraph)}</p><p>${esc(p.judgement)}</p>`).join('') : '<p class="small">this earlier report has no paragraph feedback</p>'}
    <h3>assessment objectives</h3>
    ${objectives.map(ao => `<p>${esc(ao.code)} ${esc(ao.label)}</p><p>${esc(ao.judgement || 'no comment in this earlier report')}</p>`).join('')}
    <h3>lines to improve</h3>
    ${notes.length ? notes.map(note => `
      <h3>${esc(note.title || 'line to improve')}</h3>
      <p class="small">${esc(note.location)}</p>
      <blockquote>${esc(note.candidate_line)}</blockquote>
      ${section('mistake', note.mistake)}
      ${section('why it matters', note.why_it_matters)}
      ${section('how to improve', note.improvement)}
      ${section('example', note.model_line)}
      ${section('next step', note.next_action)}
    `).join('') : '<p class="small">no individual lines selected</p>'}
    ${section('final feedback', r.final_remarks)}
    ${payload?.response ? `<details><summary>your full answer</summary><pre>${esc(payload.response)}</pre></details>` : ''}
    <p class="notice">saved on this computer${r.model_audit?.elapsed_seconds ? ' in ' + Math.round(r.model_audit.elapsed_seconds) + ' seconds' : ''}</p>
    <p class="notice">AI feedback is provisional</p>`;
}
async function showSaved() {
  try {
    const data = await fetchJSON('/api/submissions');
    if (view !== 'saved') return;
    const items = data.submissions || [];
    out.className = '';
    out.innerHTML = `<h2>saved work</h2>${items.length ? items.map(item => `
      <button class="archive-item" data-id="${esc(item.id)}">
        <strong>${esc(item.work || 'untitled answer')} ${esc(item.result?.result?.mark ?? 'not marked')} out of 25</strong>
        <span>${esc(item.created_at)} ${esc(item.question_type)}</span>
        <span>${esc((item.question || '').slice(0,100))}</span>
      </button>`).join('') : '<p class="small">no saved marking yet</p>'}`;
    out.querySelectorAll('[data-id]').forEach(button => {
      button.onclick = async () => {
        try {
          const saved = await fetchJSON('/api/submissions/' + encodeURIComponent(button.dataset.id));
          report(saved.result, saved);
        } catch (error) {
          attention(error.message);
        }
      };
    });
  } catch (error) {
    attention(error.message);
  }
}
async function showLibrary() {
  try {
    const data = await fetchJSON('/api/dashboard');
    if (view !== 'library') return;
    const count = (data.resources || []).reduce((n, item) => n + item.count, 0);
    out.className = '';
    out.innerHTML = `<h2>library</h2><p>${esc(count)} resources</p><p>${esc(data.annotations)} annotations</p><p>${esc(data.rubrics)} marking rubrics</p>`;
    const refresh = document.createElement('button');
    refresh.className = 'button';
    refresh.textContent = 'refresh library';
    refresh.onclick = async () => {
      refresh.disabled = true;
      refresh.textContent = 'refreshing library';
      try {
        const response = await fetch('/api/ingest', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: '{}'
        });
        const result = await response.json();
        if (!response.ok) throw Error(result.error || 'library refresh failed');
        if (view === 'library') showLibrary();
      } catch (error) {
        refresh.textContent = 'refresh failed ' + error.message;
        refresh.disabled = false;
      }
    };
    out.appendChild(refresh);
  } catch (error) {
    attention(error.message);
  }
}
async function checkModel() {
  const status = document.getElementById('model-status');
  try {
    const model = await fetchJSON('/api/model-status');
    status.className = model.ready ? 'ready' : 'offline';
    status.querySelector('span:last-child').textContent = model.ready ? 'model ready' : (model.error || 'start the local model');
  } catch {
    status.className = 'offline';
    status.querySelector('span:last-child').textContent = 'start the Margin server to mark an answer';
  }
}
markButton.onclick=startAssessment;checkModel();
activeJob=loadValue('marginActiveJob');updateWordCount();if(activeJob){pollJob()}

