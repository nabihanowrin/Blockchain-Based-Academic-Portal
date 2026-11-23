/*
  The "Ask our AI?" button and chat panel for the TEACHER and OFFICE pages.
  (The student page has its own copy inside app.html.) Each page sets up what the
  panel says, then calls it once the person is signed in:

      eeeAssistant({ enabled: me.assistant, title: "...", subtitle: "...",
                     can: [...], cant: [...], tries: [...], placeholder: "..." });

  Everything the AI writes is added as plain text, plus links built here, never as
  HTML, so an answer can't put code on the page. Nothing from the chat is stored.
  The server (assistant.py) decides what the AI is told; this file only shows the chat.
*/
function eeeAssistant(cfg){
  const css = `
#askBtn{position:fixed;right:24px;bottom:24px;z-index:60;border:none;border-radius:999px !important;padding:13px 22px;
  background:var(--card);color:var(--ink);font-family:inherit;font-weight:600;font-size:14.5px;cursor:pointer;display:flex;align-items:center;gap:8px;
  box-shadow:0 8px 24px rgba(48,43,49,.16),0 2px 6px rgba(48,43,49,.08);transition:transform .15s ease,box-shadow .15s ease,opacity .2s ease}
#askBtn:hover{transform:translateY(-2px);box-shadow:0 12px 28px rgba(48,43,49,.2),0 3px 8px rgba(48,43,49,.1)}
#askBtn .spark{color:var(--accent);font-size:16px}
#askBtn.away{opacity:0;pointer-events:none}
#askBox{position:fixed;top:0;right:0;bottom:0;z-index:61;width:min(400px,100vw);
  background:var(--card);border-left:1px solid var(--line);display:flex;flex-direction:column;
  box-shadow:-12px 0 32px rgba(48,43,49,.12);transform:translateX(100%);transition:transform .28s ease,visibility .28s;visibility:hidden}
#askBox.open{transform:none;visibility:visible}
#askBox header{display:flex;align-items:center;gap:10px;padding:18px 18px 14px;border-bottom:1px solid var(--line)}
#askBox header b{font-size:15px}
#askBox header small{color:var(--grey);font-size:12px;display:block}
#askBox header button{margin-left:auto;border:none;background:none;font-size:20px;cursor:pointer;color:var(--grey)}
#askLog{flex:1;overflow-y:auto;padding:14px 16px;display:flex;flex-direction:column;gap:10px;font-size:14px;line-height:1.5}
#askLog .me{align-self:flex-end;background:var(--accent-wash);border-radius:14px 14px 4px 14px;padding:9px 12px;max-width:85%;white-space:pre-wrap}
#askLog .ai{align-self:flex-start;background:#F6F2EE;border-radius:14px 14px 14px 4px;padding:9px 12px;max-width:90%;white-space:pre-wrap}
#askLog .ai a{color:var(--accent);text-decoration:underline;word-break:break-all}
#askLog .note{color:var(--grey);font-size:12.5px}
#askLog .guide{font-size:13px;color:var(--grey);line-height:1.55;border-top:1px solid var(--line);padding-top:10px}
#askLog .guide b{color:var(--ink);font-weight:600}
#askLog .guide ul{margin:3px 0 8px 18px;padding:0}
#askLog .tries{display:flex;flex-wrap:wrap;gap:6px;margin-top:2px}
#askLog .tries button{border:1px solid var(--line);background:var(--card);color:var(--ink);font:inherit;font-size:12.5px;padding:6px 10px;cursor:pointer}
#askLog .tries button:hover{border-color:var(--accent);color:var(--accent)}
#askForm{display:flex;gap:8px;padding:12px;border-top:1px solid var(--line)}
#askForm input{flex:1;padding:10px 12px;border:1px solid var(--line);border-radius:10px;font-size:14px;font-family:inherit}
#askForm button{border:none;border-radius:10px;padding:0 16px;background:var(--accent);color:#fff;font-weight:600;cursor:pointer}
#askForm button:disabled{opacity:.5;cursor:wait}`;
  const style = document.createElement('style'); style.textContent = css; document.head.appendChild(style);

  const el = (tag, props = {}, kids = []) => {
    const e = Object.assign(document.createElement(tag), props);
    kids.forEach(k => e.appendChild(typeof k === 'string' ? document.createTextNode(k) : k));
    return e;
  };
  const list = items => el('ul', {}, items.map(t => el('li', {}, [t])));

  const btn = el('button', {id: 'askBtn', type: 'button'}, [el('span', {className: 'spark', textContent: '✦'}), ' Ask our AI?']);
  const log = el('div', {id: 'askLog'});
  const input = el('input', {id: 'askIn', maxLength: 800, autocomplete: 'off', placeholder: cfg.placeholder || ''});
  const go = el('button', {id: 'askGo', textContent: 'Send'});
  const form = el('form', {id: 'askForm'}, [input, go]);
  const close = el('button', {type: 'button', textContent: '×'}); close.setAttribute('aria-label', 'Close');
  const box = el('div', {id: 'askBox'}, [
    el('header', {}, [el('div', {}, [el('b', {textContent: cfg.title}), el('small', {textContent: cfg.subtitle})]), close]),
    log, form]);
  box.setAttribute('role', 'dialog'); box.setAttribute('aria-hidden', 'true');
  document.body.append(btn, box);

  let history = [], told = false;

  // web addresses in the AI's answer become links; everything else stays plain text
  function addLinked(target, text){
    const url = /https?:\/\/[^\s<>"')\]]+/g;
    let last = 0, m;
    while ((m = url.exec(text)) !== null){
      const href = m[0].replace(/[.,;:!?]+$/, '');
      target.appendChild(document.createTextNode(text.slice(last, m.index)));
      target.appendChild(el('a', {href, textContent: href, target: '_blank', rel: 'noopener noreferrer'}));
      last = m.index + href.length; url.lastIndex = last;
    }
    target.appendChild(document.createTextNode(text.slice(last)));
  }
  function line(cls, text){
    const div = el('div', {className: cls});
    if (cls === 'ai') addLinked(div, text); else div.textContent = text;
    log.appendChild(div); log.scrollTop = log.scrollHeight;
    return div;
  }

  const tries = el('div', {className: 'tries'}, (cfg.tries || []).map(q =>
    el('button', {type: 'button', textContent: q, onclick: () => { input.value = q; form.requestSubmit(); }})));
  log.appendChild(el('div', {className: 'ai', textContent: 'Hi! What can I help you with?'}));
  log.appendChild(el('div', {className: 'guide'}, [
    el('b', {textContent: 'I can help with'}), list(cfg.can || []),
    el('b', {textContent: "I can't"}), list(cfg.cant || []),
    'English or Bangla both work. Try:', tries]));

  function toggle(){
    const open = !box.classList.contains('open');
    box.classList.toggle('open', open);
    box.setAttribute('aria-hidden', String(!open));
    btn.classList.toggle('away', open);
    if (open && !cfg.enabled && !told){
      line('note', "The assistant isn't switched on yet: the site's AI key still needs adding."); told = true;
    }
    if (open) setTimeout(() => input.focus(), 280);
  }
  btn.onclick = toggle; close.onclick = toggle;
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && box.classList.contains('open')) toggle(); });

  form.onsubmit = async e => {
    e.preventDefault();
    const message = input.value.trim();
    if (!message || go.disabled) return;
    input.value = ''; line('me', message);
    const wait = line('note', 'Thinking…'); go.disabled = true;
    try {
      const r = await fetch('/api/assistant', {method: 'POST',
        headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + token()},
        body: JSON.stringify({message, history})});
      if (r.status === 401) return toLanding();
      let res;
      try { res = await r.json(); }
      catch (err) { res = {ok: false, why: `The server sent back an error page (${r.status}). Please try again in a minute.`}; }
      wait.remove();
      if (!res.ok){ line('note', res.why); return; }
      line('ai', res.text);
      history.push({role: 'user', text: message}, {role: 'model', text: res.text});
      history = history.slice(-8);
      if (res.left_today <= 3) line('note', `${res.left_today} question${res.left_today === 1 ? '' : 's'} left today.`);
    } catch (err) {
      wait.remove();
      line('note', "Couldn't reach the website (" + (err.message || 'no connection') + '). Check your internet and try again.');
    } finally { go.disabled = false; input.focus(); }
  };
}
