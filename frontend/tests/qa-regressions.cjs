const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
const base=process.env.FSP_QA_URL || 'http://127.0.0.1:5188';
const catalog={specs:[{id:'backend',title:'Бэкенд-разработчик'}],grades:[{id:'junior',title:'Junior',threshold:-.5},{id:'middle',title:'Middle',threshold:.5},{id:'senior',title:'Senior',threshold:1.5}],skills:{backend:['Python']}};
const profile=(id=701)=>({user_id:id,email:`qa-${id}@example.com`,full_name:'Тестовая Анна Ивановна',birth_date:null,phone:null,telegram:null,city:'Москва',work_format:'remote',salary_expect_from:100000,spec:'backend',skills:['Python'],roles:[],soft_skills:[],experience_years:1,about:null,consent_pd:true,parent_consent:false,visible_fields:{},minor:false,published:true,fsp_linked:false,fsp_id:null,fsp_skipped:false});
const attempt=(done=false)=>({id:81,spec:'backend',claimed_grade:'junior',started_at:new Date(Date.now()-300000).toISOString(),finished_at:done?new Date().toISOString():null,theta:done?-2.61:null,result:done?'failed':null});
const category=(attempts=[],done=false)=>({spec:'backend',grade:done?'junior':null,status:done?'unconfirmed':'none',theta:done?-2.61:null,percentile:done?.05:null,confirmed_at:null,tested_at:null,next_attempt_at:null,suggest_upgrade:false,can_retest:{junior:null,middle:null,senior:null},attempts});
const item={item_id:'x1',template_id:'t1',text:'Выберите ответ',code:null,kind:'single',options:['Первый','Второй'],topic:'python',no:1,total:10};
const state=(finished=false,deadline=new Date(Date.now()+300000).toISOString())=>({attempt_id:81,spec:'backend',claimed_grade:'junior',item:finished?null:item,finished,answered:2,total:10,deadline,item_time_limit_sec:90,result:null});
const result={attempt_id:81,spec:'backend',claimed_grade:'junior',theta:-2.61,grade:null,confirmed:false,suggest_upgrade:false,correct:1,total:10,topics:[{topic:'python',total:10,correct:1}],category:{},next_attempt_at:null,started_at:new Date().toISOString(),finished_at:new Date().toISOString()};
let checks=0;
async function test(name,fn){await fn();checks++;console.log(`PASS ${name}`);}
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});
async function setup(custom=()=>null, user=701, viewport={width:375,height:812},role='candidate'){
 const context=await browser.newContext({viewport}); const errors=[];const requests=[];
 let serverProfile=profile(user);
 await context.addInitScript(({id,role})=>{localStorage.setItem('fsp_token',JSON.stringify({access_token:`qa-user-${id}`,role,user_id:id,token_type:'bearer'}));},{id:user,role});
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',async route=>{
  const req=route.request(); const path=new URL(req.url()).pathname.replace('/api','');requests.push([req.method(),path,req.url(),req.headers()]);
  let data=await custom(path,req);
  if(data===null){if(path==='/me/profile'){if(req.method()==='PUT')serverProfile={...serverProfile,...req.postDataJSON()};data=serverProfile;}else if(path==='/me/category')data=category();else if(path==='/catalog')data=catalog;else if(path==='/me/invitations')data=[];else if(path==='/tests/81/result')data=result;else if(path==='/me/results')data={sources:{},fsp_linked:false,fsp_score:0,explain:[]};else data=[];}
  await route.fulfill({status:data?.__status??200,contentType:'application/json',body:JSON.stringify(data?.__body??data)});
 });return{context,page,errors,requests,readProfile:()=>serverProfile};}
try {
 await test('skip FSP saves the choice on the server and updates without reload',async()=>{
 const x=await setup();await x.page.goto(base+'/candidate');await x.page.getByRole('button',{name:'У меня нет истории ФСП'}).click();
 await x.page.getByRole('heading',{name:'Шаг 3. Выберите специализацию и грейд'}).waitFor();assert(x.readProfile().fsp_skipped);assert(!await x.page.getByText('✓. Профиль').count());
 const overflow=await x.page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth);assert(!overflow);assert.deepEqual(x.errors,[]);await x.context.close();});
 await test('fresh browser after test does not return to FSP linking',async()=>{
 const x=await setup(p=>p==='/me/category'?category([attempt(true)],true):null);await x.page.goto(base+'/candidate');await x.page.getByRole('heading',{name:'Грейд пока не подтверждён'}).waitFor();assert.equal(await x.page.getByRole('button',{name:'У меня нет истории ФСП'}).count(),0);assert.deepEqual(x.errors,[]);await x.context.close();});
 await test('unfinished attempt has explicit Continue and does not start a new test',async()=>{
 const x=await setup(p=>p==='/me/category'?category([attempt()]):p==='/tests/81'?state():null);await x.page.goto(base+'/candidate');await x.page.getByRole('link',{name:'Продолжить попытку'}).click();await x.page.getByText('Выберите ответ',{exact:true}).waitFor();assert(!x.requests.some(([m,p])=>m==='POST'&&p==='/tests/start'));assert.deepEqual(x.errors,[]);await x.context.close();});
 await test('expired attempt on journey is finalized and exposes its result',async()=>{
 let finished=false;const x=await setup(p=>{if(p==='/me/category')return category([attempt(finished)],finished);if(p==='/tests/81'){finished=true;return state(true,new Date(Date.now()-20000).toISOString());}return null;});await x.page.goto(base+'/candidate');await x.page.getByRole('link',{name:'Посмотреть результат'}).waitFor();assert.equal(await x.page.getByRole('button',{name:'Начать тест'}).count(),0);assert.deepEqual(x.errors,[]);await x.context.close();});
 await test('timer expiry without submission closes test and shows explanation and Russian theta',async()=>{
 let count=0;const deadline=new Date(Date.now()+1200).toISOString();const x=await setup(p=>p==='/tests/81'?state(++count>=2,deadline):null);await x.page.goto(base+'/candidate/test/81');await x.page.getByText('Выберите ответ',{exact:true}).waitFor();await x.page.waitForURL('**/candidate/result/81?timeout=1');await x.page.getByText('Время теста истекло. Результат рассчитан по сохранённым ответам.').waitFor();assert((await x.page.locator('body').innerText()).includes('−2,61'));assert(!x.requests.some(([m,p])=>m==='POST'&&p.includes('/answer')));assert.deepEqual(x.errors,[]);await x.context.close();});
 await test('404 attempt displays error instead of infinite loading',async()=>{
 const x=await setup(p=>p==='/tests/81'?{__status:404,__body:{detail:'Попытка не найдена',code:'not_found'}}:null);await x.page.goto(base+'/candidate/test/81');await x.page.getByText('Попытка не найдена',{exact:true}).waitFor();assert.deepEqual(x.errors,[]);await x.context.close();});
 await test('legacy global skip cannot skip FSP for another account',async()=>{
 const x=await setup(null??(()=>null),702);await x.page.goto(base);await x.page.evaluate(()=>{localStorage.setItem('fsp_skip','1');localStorage.setItem('fsp_skip:701','1');});await x.page.goto(base+'/candidate');await x.page.getByRole('button',{name:'У меня нет истории ФСП'}).waitFor();assert.deepEqual(x.errors,[]);await x.context.close();});
 await test('skip remains immediate when browser storage is unavailable',async()=>{
 const x=await setup();await x.context.addInitScript(()=>{const orig=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k.startsWith('fsp_skip'))throw new Error('storage disabled');return orig.call(this,k,v);};});await x.page.goto(base+'/candidate');await x.page.getByRole('button',{name:'У меня нет истории ФСП'}).click();await x.page.getByRole('heading',{name:'Шаг 3. Выберите специализацию и грейд'}).waitFor();assert.deepEqual(x.errors,[]);await x.context.close();});
 await test('changing accounts clears the previous profile and onboarding state',async()=>{
 let uid=701;let skipped=false;const x=await setup((p,req)=>{if(p==='/me/profile'){if(req.method()==='PUT')skipped=req.postDataJSON().fsp_skipped;return {...profile(uid),fsp_skipped:skipped};}if(p==='/auth/demo/candidate'){uid=702;skipped=false;return {access_token:'qa-user-702',user_id:702,role:'candidate',token_type:'bearer'};}return null;});
 await x.page.goto(base+'/candidate');await x.page.getByRole('button',{name:'У меня нет истории ФСП'}).click();await x.page.getByRole('heading',{name:'Шаг 3. Выберите специализацию и грейд'}).waitFor();
 await x.page.getByRole('button',{name:'Выйти',exact:true}).click();await x.page.getByRole('button',{name:'Я кандидат — демо'}).click();
 await x.page.getByRole('button',{name:'У меня нет истории ФСП'}).waitFor();assert.equal(await x.page.evaluate(()=>JSON.parse(localStorage.getItem('fsp_token')).user_id),702);assert.deepEqual(x.errors,[]);await x.context.close();});
 await test('fresh device retains saved FSP choice before the first test',async()=>{
 const x=await setup();await x.page.goto(base+'/candidate');await x.page.getByRole('button',{name:'У меня нет истории ФСП'}).click();await x.page.getByRole('heading',{name:'Шаг 3. Выберите специализацию и грейд'}).waitFor();
 const saved=x.readProfile();const y=await setup(p=>p==='/me/profile'?saved:null);await y.page.goto(base+'/candidate');await y.page.getByRole('heading',{name:'Шаг 3. Выберите специализацию и грейд'}).waitFor();assert.equal(await y.page.getByRole('button',{name:'У меня нет истории ФСП'}).count(),0);assert.deepEqual(y.errors,[]);await x.context.close();await y.context.close();});
 await test('failed skip stays on FSP step and shows a retryable error',async()=>{
 const x=await setup((p,req)=>p==='/me/profile'&&req.method()==='PUT'?{__status:503,__body:{detail:'Не удалось сохранить выбор',code:'unavailable'}}:null);await x.page.goto(base+'/candidate');await x.page.getByRole('button',{name:'У меня нет истории ФСП'}).click();await x.page.getByText('Не удалось сохранить выбор',{exact:true}).waitFor();assert.equal(await x.page.getByRole('heading',{name:'Шаг 3. Выберите специализацию и грейд'}).count(),0);assert.deepEqual(x.errors,[]);await x.context.close();});
 await test('FSP sign-in uses authenticated POST and only a one-time code in navigation',async()=>{
 const x=await setup(p=>p==='/auth/fsp/start'?{authorize_url:'/api/auth/fsp/authorize?code=one-time-code',expires_in:60}:null);await x.page.goto(base+'/candidate/profile');await x.page.getByRole('button',{name:'Войти через ФСП ID'}).click();await x.page.waitForURL('**/api/auth/fsp/authorize?code=one-time-code');const start=x.requests.find(([m,p])=>m==='POST'&&p==='/auth/fsp/start');assert(start);assert.equal(start[3].authorization,'Bearer qa-user-701');assert(!x.page.url().includes('qa-user-701'));assert(!x.page.url().includes('token='));assert.deepEqual(x.errors,[]);await x.context.close();});
 await test('FSP start failure is visible and does not navigate',async()=>{
 const x=await setup(p=>p==='/auth/fsp/start'?{__status:503,__body:{detail:'Связывание временно недоступно',code:'unavailable'}}:null);await x.page.goto(base+'/candidate/profile');await x.page.getByRole('button',{name:'Войти через ФСП ID'}).click();await x.page.getByText('Связывание временно недоступно',{exact:true}).waitFor();assert(x.page.url().endsWith('/candidate/profile'));assert.deepEqual(x.errors,[]);await x.context.close();});
 await test('matches display the full count, shown count and updated filter count',async()=>{
 const need={id:1,search_id:1,employer_id:1,title:'Проверка подбора',spec:'backend',grade:'middle',skills:[],salary_from:100000,salary_to:200000,salary_type:'gross',work_format:null,published:false};
 const cand={...profile(),id:701,grade:'middle',status:'confirmed',theta:1,percentile:.7,results:[],contacts_hidden:true,invitation_status:null};
 const x=await setup((p,req)=>p==='/needs/1'?need:p==='/needs/1/categories'?[]:p==='/needs/1/matches'?{total:new URL(req.url()).searchParams.get('fsp_only')==='true'?89:136,items:[{candidate_id:701,score:72,explain:[],candidate:cand}]}:null,701,{width:375,height:812},'employer');
 await x.page.goto(base+'/employer/needs/1');await x.page.getByText(/Найдено: 136/).waitFor();await x.page.getByText(/Показано: 1/).waitFor();await x.page.getByRole('button',{name:/Уточнить/}).click();await x.page.getByRole('checkbox',{name:'Только с результатами ФСП'}).check();await x.page.getByText(/Найдено: 89/).waitFor();assert.deepEqual(x.errors,[]);await x.context.close();});
 console.log(`RESULT ${checks} browser regressions passed`);
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
