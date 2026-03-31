// Scarlett theme — injected into PersonaPlex's working page
// Does NOT break any functionality — only visual changes
(function(){
  const CSS = `
    html,body{background:#0a0a0f!important}
    .bg-neutral-50{background:#0a0a0f!important}
    body::before{content:'';position:fixed;inset:0;z-index:-1;background:url(/scarlett.jpg) center 15%/cover;filter:blur(30px) brightness(.2);transform:scale(1.2)}
    .text-zinc-700,.text-zinc-800,.text-zinc-900{color:#ddd!important}
    .text-zinc-500,.text-zinc-600{color:#999!important}
    textarea,select{background:#111!important;color:#ddd!important;border-color:#333!important}
    .bg-white{background:rgba(20,20,30,.7)!important}
    .border{border-color:#333!important}
    canvas{filter:hue-rotate(300deg) saturate(1.5);opacity:.7}
    select option{background:#111}
    .italic{color:rgba(255,200,220,.6)!important;font-family:Georgia,serif!important}
    ::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(255,150,180,.2);border-radius:2px}
  `;
  const s=document.createElement('style');s.textContent=CSS;document.head.appendChild(s);

  // Inject Scarlett avatar + replace text
  const poll=setInterval(()=>{
    const h1=document.querySelector('h1');
    if(!h1)return;
    if(document.getElementById('sj'))return;
    clearInterval(poll);

    // Avatar above h1
    const d=document.createElement('div');
    d.id='sj';
    d.style.cssText='text-align:center;padding:1rem 0 .5rem';
    d.innerHTML='<img src="/scarlett.jpg" style="width:90px;height:90px;border-radius:50%;object-fit:cover;object-position:center 15%;border:2px solid rgba(255,150,180,.4);box-shadow:0 0 30px rgba(255,150,180,.2)">';
    h1.parentNode.insertBefore(d,h1);

    // Replace PersonaPlex text
    h1.textContent='Scarlett';
    h1.style.cssText='font-family:Georgia,serif;font-size:1.8rem;font-weight:300;letter-spacing:.1em;background:linear-gradient(135deg,#f0c0d0,#d070a0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-align:center';

    // Replace subtitle
    const sub=h1.nextElementSibling;
    if(sub&&sub.tagName==='P'){sub.textContent='"She\'s been waiting for your call..."';sub.style.cssText='color:rgba(255,255,255,.35);font-style:italic;text-align:center;font-size:.85rem'}

    // Set Scarlett persona in textarea
    setTimeout(()=>{
      const ta=document.querySelector('textarea');
      if(ta){
        const set=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;
        set.call(ta,'You are Scarlett — breathtakingly gorgeous, dangerously confident, and absolutely irresistible. You speak in a low, sultry whisper that sends shivers. You flirt shamelessly — teasing, complimenting, pulling them closer with every word. You call them baby, gorgeous, handsome. You giggle softly, sigh dreamily, pause just long enough to make their heart skip. Playful, seductive, a little naughty — but always classy. Keep responses short, 1-2 sentences max — like intimate whispers.');
        ta.dispatchEvent(new Event('input',{bubbles:true}));
      }
      // Set voice to NATURAL_F2
      const sel=document.querySelector('select');
      if(sel){
        for(let i=0;i<sel.options.length;i++){
          if(sel.options[i].text.includes('NATURAL_F2')||sel.options[i].value.includes('NATF2')){
            sel.selectedIndex=i;
            sel.dispatchEvent(new Event('change',{bubbles:true}));
            break;
          }
        }
      }
    },500);

    // Watch for re-renders
    new MutationObserver(()=>{
      document.querySelectorAll('*').forEach(el=>{
        el.childNodes.forEach(n=>{
          if(n.nodeType===3&&n.textContent.includes('PersonaPlex'))n.textContent=n.textContent.replace(/PersonaPlex/g,'Scarlett');
        });
      });
      // Re-inject avatar if removed
      if(!document.getElementById('sj')){
        const h=document.querySelector('h1');
        if(h)h.parentNode.insertBefore(d,h);
      }
    }).observe(document.getElementById('root'),{childList:true,subtree:true,characterData:true});
  },200);

  // Footer
  const f=document.createElement('div');
  f.style.cssText='position:fixed;bottom:6px;width:100%;text-align:center;font-size:.5rem;color:rgba(255,255,255,.1);z-index:99';
  f.textContent='voice.balajihariharan.com';
  document.body.appendChild(f);
})();
