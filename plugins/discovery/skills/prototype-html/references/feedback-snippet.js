/* 回饋面板：每個畫面一個留言框，留言存在瀏覽器；「複製回覆」輸出 Markdown，貼回給 agent 改原型。
   留言逐行加 > 引用，內容不會跟回覆的標題結構混淆。 */
(function () {
  var screens = Array.from(document.querySelectorAll('.screen'));
  if (!screens.length) screens = [document.querySelector('main') || document.body];
  var title = document.title || '原型';
  var read = function (k) { try { return localStorage.getItem(k) || ''; } catch (e) { return ''; } };
  var write = function (k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 無痕或封鎖儲存時只是不保留 */ } };

  var fields = screens.map(function (screen, i) {
    var id = screen.id || 'screen-' + (i + 1);
    var link = screen.id && document.querySelector('[data-target="' + CSS.escape(id) + '"]');
    var label = link || screen.querySelector('h1,h2,h3');
    var name = label ? label.textContent.trim() : '畫面 ' + (i + 1);
    var key = 'prototype-feedback:' + title + ':' + id;
    var box = document.createElement('div');
    box.innerHTML = '<div class="feedback" style="margin-top:24px;padding:12px;border:1px dashed var(--border,#999);border-radius:var(--radius,6px)">'
      + '<label style="display:block"><span style="display:block;font-weight:600;margin-bottom:4px"></span>'
      + '<textarea rows="3" style="width:100%;box-sizing:border-box"></textarea></label>'
      + '<div style="margin-top:8px"><button type="button" class="btn">複製回覆</button> <span role="status"></span></div></div>';
    var area = box.querySelector('textarea');
    box.querySelector('label span').textContent = '對「' + name + '」的回饋';
    area.name = key;
    area.value = read(key);
    area.addEventListener('input', function () { write(key, area.value); });
    box.querySelector('button').addEventListener('click', function () { copy(box.querySelector('[role=status]'), area); });
    screen.appendChild(box);
    return { name: name, area: area };
  });

  function reply() {
    var parts = fields.filter(function (f) { return f.area.value.trim(); }).map(function (f) {
      return '## ' + f.name + '\n' + f.area.value.trim().split(/\r?\n/).map(function (l) { return '> ' + l; }).join('\n');
    });
    return parts.length ? ['# Re: ' + title].concat(parts).join('\n\n') + '\n' : '';
  }

  function copy(status, area) {
    var text = reply();
    if (!text) { status.textContent = '還沒有留言'; return; }
    var done = function () { status.textContent = '已複製，貼回對話即可'; };
    var fallback = function () { // file:// 或舊瀏覽器沒有 clipboard API
      var t = document.createElement('textarea');
      t.value = text;
      area.parentNode.appendChild(t);
      t.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      if (ok) { t.remove(); done(); } else { status.textContent = '無法自動複製，請手動複製下面的文字'; }
    };
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, fallback);
    else fallback();
  }
})();
