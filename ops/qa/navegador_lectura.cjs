// QA remoto acotado. Credenciales solo por stdin; nunca se escriben en evidencia.
// No crea servicios/catálogo/recomendaciones ni modifica criterios del servidor.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

class CDP {
  constructor(url) {
    this.socket = new WebSocket(url); this.id = 0; this.pending = new Map();
    this.ready = new Promise((resolve, reject) => {
      this.socket.addEventListener('open', resolve, {once:true});
      this.socket.addEventListener('error', () => reject(new Error('CDP no disponible')), {once:true});
    });
    this.socket.addEventListener('message', ({data}) => {
      const m = JSON.parse(data); const p = this.pending.get(m.id);
      if (p) { this.pending.delete(m.id); clearTimeout(p.timer);
        m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result); }
    });
  }
  async send(method, params={}) {
    await this.ready; const id = ++this.id;
    return new Promise((resolve,reject) => {
      const timer=setTimeout(()=>{this.pending.delete(id);reject(new Error('Timeout CDP: '+method));},25000);
      this.pending.set(id,{resolve,reject,timer}); this.socket.send(JSON.stringify({id,method,params}));
    });
  }
  async evaluate(expression) {
    const r=await this.send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
    if(r.exceptionDetails) throw new Error('Fallo de evaluación de navegador');
    return r.result.value;
  }
  async navigate(url) {
    const r=await this.send('Page.navigate',{url});
    if(r.errorText) throw new Error('Navegación: '+r.errorText);
    await this.evaluate(`new Promise(resolve=>{const start=Date.now();const poll=()=>document.readyState==='complete'?resolve(true):Date.now()-start>15000?resolve(false):setTimeout(poll,100);setTimeout(poll,700);})`);
  }
}

(async()=>{
  let input=''; for await(const part of process.stdin) input+=part;
  const config=JSON.parse(input); input='';
  const origin='https://18.225.245.214';
  const port=fs.readFileSync(path.join(os.tmpdir(),'eva-qa-browser-20261104','DevToolsActivePort'),'utf8').split(/\r?\n/)[0];
  const target=await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,{method:'PUT'})).json();
  const c=new CDP(target.webSocketDebuggerUrl);
  const out=path.resolve(config.output); fs.mkdirSync(out,{recursive:true});
  const report={fecha:new Date().toISOString(),base:'7615a24',entorno:origin,
    navegador:await c.send('Browser.getVersion'),nota:'HTTPS sin omitir certificado; viewport emulado no es dispositivo físico',casos:[]};
  await c.send('Page.enable'); await c.send('Network.enable');
  async function request(url,method='GET') {
    return c.evaluate(`(async()=>{const token=document.cookie.split('; ').find(x=>x.startsWith('csrftoken='))?.split('=')[1];const r=await fetch(${JSON.stringify(url)},{method:${JSON.stringify(method)},redirect:'manual',credentials:'same-origin',headers:${method==='POST'?"{'X-CSRFToken':token||'','Content-Type':'application/x-www-form-urlencoded'}":"{}"}${method==='POST'?",body:''":""}});return {status:r.status,type:r.type,cache:r.headers.get('cache-control')};})()`);
  }
  async function screenshot(name,width,height) {
    await c.send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
    await c.evaluate('document.fonts.ready.then(()=>new Promise(r=>setTimeout(r,250)))');
    const metrics=await c.evaluate(`({width:innerWidth,height:innerHeight,scroll:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,passwords:Array.from(document.querySelectorAll('input[type=password]')).some(x=>x.value.length>0)})`);
    if(metrics.passwords) throw new Error('Captura bloqueada: campo sensible no vacío');
    const r=await c.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    fs.writeFileSync(path.join(out,name+'.png'),Buffer.from(r.data,'base64')); return metrics;
  }
  try {
    await c.send('Network.clearBrowserCookies'); await c.navigate(origin+'/cuentas/login/');
    report.login_publico=await screenshot('login-1440',1440,900);
    for(const url of ['/captura/bandeja/','/catalogo/platos/','/analisis/','/historico/','/recomendaciones/','/recomendaciones/demostracion/']) {
      const respuesta=await request(url);
      await c.navigate(origin+url);
      report.casos.push({id:'E03/E25',rol:'Anonimo',url,...respuesta,destino:await c.evaluate('location.pathname')});
    }
    for(const cuenta of config.accounts) {
      await c.send('Network.clearBrowserCookies'); await c.navigate(origin+'/cuentas/login/');
      await c.evaluate(`(()=>{document.querySelector('[name=username]').value=${JSON.stringify(cuenta.username)};document.querySelector('[name=password]').value=${JSON.stringify(cuenta.password)};document.querySelector('form').requestSubmit();return true;})()`);
      await new Promise(r=>setTimeout(r,1200));
      const destino=await c.evaluate('location.pathname');
      if(destino==='/cuentas/login/') {report.casos.push({id:'E01',rol:cuenta.role,estado:'FALLIDO',motivo:'No se inició sesión'});continue;}
      report.casos.push({id:'E01-login',rol:cuenta.role,destino});
      for(const url of ['/captura/bandeja/','/catalogo/platos/','/analisis/','/historico/','/recomendaciones/','/recomendaciones/demostracion/']) {
        report.casos.push({id:'E04/E25',rol:cuenta.role,url,...await request(url)});
      }
      const prohibida=cuenta.role==='Registro'?'/catalogo/platos/nuevo/':cuenta.role==='Cocina'?'/captura/bandeja/':'/analisis/servicio/00000000-0000-0000-0000-000000000001/solicitar/';
      report.casos.push({id:'E05',rol:cuenta.role,url:prohibida,method:'POST',...await request(prohibida,'POST')});
      const pages=cuenta.role==='Registro'?['/captura/bandeja/']:['/historico/','/recomendaciones/','/recomendaciones/demostracion/?escenario=prueba'];
      for(const page of pages) {
        await c.navigate(origin+page);
        const name=cuenta.role.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'')+'-'+(page.includes('demostracion')?'demo':page.split('/').filter(Boolean).join('-'));
        for(const [w,h] of [[1440,900],[390,844],[820,900]]) {
          report.casos.push({id:'J02-cruzada',rol:cuenta.role,page,evidencia:name+'-'+w+'.png',...await screenshot(name+'-'+w,w,h)});
        }
      }
      if(cuenta.role!=='Registro') {
        for(const escenario of ['mantener','porcion','prueba','insuficiente']) {
          await c.navigate(origin+'/recomendaciones/demostracion/?escenario='+escenario);
          const visible=await c.evaluate(`(()=>{const t=document.body.innerText;return {datosEjemplo:/Datos de ejemplo/i.test(t),noPrediccion:/no son predicciones/i.test(t),recomendacion:Array.from(document.querySelectorAll('h2')).map(x=>x.innerText).find(x=>x.startsWith('Recomendaci')),indicadores:Array.from(document.querySelectorAll('.rec-contadores div')).map(x=>({nombre:x.querySelector('dt').innerText,valor:x.querySelector('dd').innerText}))}})()`);
          report.casos.push({id:'E18/E19',rol:cuenta.role,escenario,...visible});
        }
      }
      report.casos.push({id:'E06-logoutGET',rol:cuenta.role,...await request('/cuentas/logout/')});
      await request('/cuentas/logout/','POST');
      const protegida=cuenta.role==='Registro'?'/captura/bandeja/':'/historico/';
      const verifica=await request(protegida);
      await c.navigate(origin+protegida);
      report.casos.push({id:'E01-logout',rol:cuenta.role,protegido:verifica,destino:await c.evaluate('location.pathname')});
      cuenta.password='';cuenta.username='';
    }
  } finally {
    fs.writeFileSync(path.join(out,'navegador_resultados.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify({casos:report.casos.length,navegador:report.navegador.product,output:out}));
    await c.send('Network.clearBrowserCookies').catch(()=>{}); c.socket.close();
  }
})().catch(e=>{console.error('QA detenido: '+e.message);process.exitCode=1;});
