const {test} = require('node:test');
const assert = require('node:assert/strict');
const {prepararFormulario} = require('../../static/js/recomendaciones.js');
function formulario(valido=true) {
  const button = {disabled:false}, estado={textContent:''};
  const form = {dataset:{}, checkValidity:()=>valido, addEventListener:(name,fn)=>form[name]=fn,
    querySelector:selector=>selector.startsWith('button') ? button : estado};
  return {form, button, estado};
}
test('primer envío permite navegación y bloquea el segundo, sin reintentar', ()=>{
  const {form,button,estado}=formulario(); prepararFormulario(form);
  let bloqueados=0; const event={preventDefault:()=>bloqueados++};
  form.submit(event); assert.equal(bloqueados,0); assert.equal(button.disabled,true);
  assert.match(estado.textContent,/confirmación del servidor/);
  form.submit(event); assert.equal(bloqueados,1);
});
test('entrada inválida no bloquea el botón ni anuncia éxito', ()=>{
  const {form,button,estado}=formulario(false); prepararFormulario(form);
  let bloqueados=0;form.submit({preventDefault:()=>bloqueados++});
  assert.equal(bloqueados,1);assert.equal(button.disabled,false);assert.equal(estado.textContent,'');
});
test('pageshow restablece envío al volver y conserva bloqueo por conflicto', ()=>{
  let restaurar;globalThis.addEventListener=(name,fn)=>restaurar=fn;
  const {form,button}=formulario();prepararFormulario(form);form.submit({preventDefault(){}});
  restaurar();assert.equal(button.disabled,false);
  form.dataset.bloqueado='true';button.disabled=true;restaurar();assert.equal(button.disabled,true);
  delete globalThis.addEventListener;
});
