const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const elements=new Map();
for(const id of ['out','mark','year','component','work','question_type','question','passage','response','response-count','model-status']){
 elements.set(id,{value:id==='year'?'2026':id==='question_type'?'essay':'',textContent:'',style:{},events:{},
 addEventListener(type,callback){this.events[type]=callback},setAttribute(key,value){this[key]=value},
 querySelector(){return {textContent:''}}});
}
const context={document:{getElementById:id=>elements.get(id),querySelectorAll:()=>[]},localStorage:{getItem:()=>null,setItem(){},removeItem(){}},
 fetch:async()=>({ok:true,json:async()=>({ready:true})}),setTimeout,clearTimeout,AbortController,console};
vm.runInNewContext(fs.readFileSync('app/app.js','utf8'),context);
const response=elements.get('response'),counter=elements.get('response-count'),button=elements.get('mark');
for(const count of [0,999,1000,1001]){
 response.value=Array(count).fill('word').join(' ');response.events.input();
 assert.equal(button.disabled,count>1000);
 assert.equal(response['aria-invalid'],String(count>1000));
 assert.match(counter.textContent,new RegExp(count+' of 1000 words'));
 if(count===1001)assert.match(counter.textContent,/remove 1 word/);
}
console.log('Browser-script limit checks passed: 0, 999, 1000, 1001 words.');
context.report({
 assessment:{question:'How is conflict presented?',work:'A poem',year:2026,component:'12',question_type:'essay'},
 result:{mark:18,maximum_mark:25,indicative_level:6},
 examiner_judgement:'Overall comment',strengths:'Strength comment',next_band:'Band comment',
 semantic_paragraph_reviews:[{paragraph:1,judgement:'Paragraph comment'}],
 ao_indicators:[{code:'AO1',label:'Knowledge',judgement:'Objective comment'}],
 line_feedback:[{candidate_line:'It is "very effective".',title:'Develop this line',location:'Paragraph 1, source line 1',
 mistake:'Mistake comment',why_it_matters:'Reason comment',improvement:'Improvement comment',
 model_line:'A better sentence.',next_action:'Action comment'}],
 final_remarks:'Final comment',model_audit:{elapsed_seconds:50}
},{response:'The original answer keeps its punctuation!'});
const output=elements.get('out').innerHTML;
for(const text of ['18 out of 25','level 6','Overall comment','Strength comment','Band comment','Paragraph comment',
 'Objective comment','Mistake comment','Reason comment','Improvement comment','A better sentence.',
 'Action comment','Final comment','The original answer keeps its punctuation!','&quot;very effective&quot;']){
 assert.ok(output.includes(text),text);
}
console.log('Plain report retains every feedback section and original punctuation.');
