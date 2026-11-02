/**
 * anonymize-page.js — 截圖前把畫面上的敏感值換成假資料
 *
 * 貼進 chrome-devtools 的 `evaluate_script` 執行一次，之後用
 * `window.__anon.groups() / suggest() / apply() / verify()` 操作。
 *
 * ## 為什麼不用遮罩
 *
 * 遮罩會蓋掉版面——整欄變色塊、清單只剩圓圈，讀者看不出畫面原本長什麼樣；
 * 而且遮罩色、與紅框相交、整批一致性全都會出錯。
 * **換成假資料的畫面是完整的**，截圖出來就是一張正常畫面。
 *
 * ## 只換三類
 *
 * **姓名、客戶／租戶名稱、金額。** 設備代號與名稱、單據編號、型號、
 * 品項名稱、流程說明、群組名稱等業務資料**一律不換**——它們不是個資，
 * 換掉只會讓手冊失真。
 *
 * ## 核心：靠位置找，不要靠文字特徵猜
 *
 * 實測：用中文詞長度＋排除詞去猜姓名，
 * 前 12 名全是「閒置」「型號」「出貨」「庫存」這類業務詞，真姓名一個都沒中。
 * 改看 **parent 的 class**，`header-left header-meta-text` 底下 6 個值
 * 全部是人名、零誤判；同名的 `header-right header-meta-text` 則全是狀態文字。
 *
 * **同一類資料幾乎總是共用同一個 class。** 所以流程是：
 * 先 `groups()` 看哪個 class 底下裝的是敏感資料 → 對那個 selector 整群替換。
 * 新進的資料（新的承辦人員）會自動被涵蓋，不必每次重掃。
 */
(() => {
  const ATTRS = ['title', 'aria-label', 'placeholder', 'alt', 'value'];

  const NAME_POOL = ['王小明', '李美華', '陳志強', '林淑芬', '張大同',
                     '黃雅婷', '吳建宏', '劉怡君', '蔡明哲', '鄭佳穎'];
  // 客戶／廠商名。**池子要夠大**：suggest() 用完會退化成「長興實業2」「長興實業3」，
  // 一眼看得出是假的。實測 5 個不夠——訂單與出貨清單一次就吃掉十幾家。
  const ORG_POOL  = ['青禾商行', '長興實業', '大川貿易', '順遠科技', '義和企業',
                     '鼎昕物流', '晨光文創', '日朗食品', '協安五金', '冠宇國際',
                     '振遠生技', '台禾電子', '國晟實業', '欣光材料', '正和資訊',
                     '華禾零售', '立群顧問', '祥和餐飲', '瑞展能源', '安和服務'];

  // 登入中的那家公司（租戶）**固定**換成這個，不從 ORG_POOL 抽。
  // 手冊裡「我這家公司」永遠是示範公司，跨功能、跨批次都一樣。
  //
  // ⚠ 它不是客戶。同一張圖上「客戶：長興實業」那種欄位走 ORG_POOL，兩者不要混。
  // ⚠ 位置每個系統不同——導覽列、頁首、頁尾、document.title、列印抬頭都出現過。
  //    **靠「它代表登入的公司」判斷，不要靠「它在導覽列」**。
  const TENANT = '示範公司';

  function textNodes(root) {
    root = root || document.body;
    const out = [];
    const walk = (r) => {
      const w = document.createTreeWalker(r, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = w.nextNode())) {
        const p = n.parentElement;
        if (!p) continue;
        const tag = p.tagName;
        if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT') continue;
        if (n.nodeValue && n.nodeValue.trim()) out.push(n);
      }
      if (r.querySelectorAll) {
        r.querySelectorAll('*').forEach((el) => { if (el.shadowRoot) walk(el.shadowRoot); });
      }
    };
    walk(root);
    return out;
  }

  /**
   * groups() — 按 parent class 分群列出畫面上的文字值。
   * **這是判讀的起點**：人看一眼就知道哪一群是姓名、哪一群是金額。
   * `maxDistinct` 過濾掉值太多的群（那通常是內文不是欄位）。
   */
  function groups(maxDistinct) {
    maxDistinct = maxDistinct || 40;
    const g = new Map();
    for (const n of textNodes()) {
      const t = n.nodeValue.trim();
      if (!t || t.length > 40) continue;
      const p = n.parentElement;
      const cls = (p.className || p.tagName || '').toString().trim().slice(0, 60);
      if (!g.has(cls)) g.set(cls, new Set());
      g.get(cls).add(t);
    }
    return [...g.entries()]
      .map(([cls, v]) => ({ cls, distinct: v.size, sample: [...v].slice(0, 10) }))
      .filter((e) => e.distinct >= 1 && e.distinct <= maxDistinct)
      .sort((a, b) => a.distinct - b.distinct);
  }

  /**
   * suggest(selector, kind) — 對一個 selector 底下的值產生「真值 → 假值」建議對照表。
   * kind: 'name' | 'org'。金額請用 suggestMoney()。
   * **回傳的表要由呼叫端保存並重複使用**，才能保證同一個人在每張圖都是同一個假名。
   */
  function suggest(selector, kind) {
    const pool = kind === 'org' ? ORG_POOL : NAME_POOL;
    const vals = new Set();
    document.querySelectorAll(selector).forEach((el) => {
      const t = (el.textContent || '').trim();
      if (t && t.length <= 40) vals.add(t);
    });
    const map = {};
    let i = 0;
    for (const v of vals) {
      const base = pool[i % pool.length];
      map[v] = i >= pool.length ? base + (Math.floor(i / pool.length) + 1) : base;
      i++;
    }
    return map;
  }

  /** suggestMoney(selector) — 金額換成同位數的假數字，保留千分位與小數格式。 */
  function suggestMoney(selector) {
    const map = {};
    document.querySelectorAll(selector).forEach((el) => {
      const t = (el.textContent || '').trim();
      if (!t || map[t]) return;
      map[t] = t.replace(/\d/g, () => String(Math.floor(Math.random() * 9) + 1));
    });
    return map;
  }

  /**
   * apply(map) — 套用替換，回傳每筆的**實際替換次數**。
   * 某筆是 0 就是沒生效，要查（選錯 selector、或該值此刻不在畫面上）。
   * SPA 重新渲染會還原，**每次導航或切換狀態後都要重跑**。
   */
  function apply(map) {
    const pairs = Object.entries(map).sort((a, b) => b[0].length - a[0].length);
    const hits = Object.fromEntries(pairs.map(([k]) => [k, 0]));
    const sub = (s) => {
      let out = s;
      for (const [real, fake] of pairs) {
        if (out.includes(real)) {
          hits[real] += out.split(real).length - 1;
          out = out.split(real).join(fake);
        }
      }
      return out;
    };
    for (const n of textNodes()) {
      const t = n.nodeValue;
      const r = sub(t);
      if (r !== t) n.nodeValue = r;
    }
    for (const el of document.querySelectorAll('*')) {
      for (const a of ATTRS) {
        const v = el.getAttribute && el.getAttribute(a);
        if (v) { const r = sub(v); if (r !== v) el.setAttribute(a, r); }
      }
      if ('value' in el && typeof el.value === 'string' && el.value) {
        const r = sub(el.value);
        if (r !== el.value) el.value = r;
      }
    }
    document.title = sub(document.title);
    return hits;
  }

  /**
   * verify(reals) — **截圖前的最後一道**：這些真值還在畫面上嗎？
   * 回傳仍找得到的那些。**必須是空陣列才可以截圖。**
   */
  function verify(reals) {
    const hay = [];
    for (const n of textNodes()) hay.push(n.nodeValue);
    for (const el of document.querySelectorAll('*')) {
      for (const a of ATTRS) {
        const v = el.getAttribute && el.getAttribute(a);
        if (v) hay.push(v);
      }
      if ('value' in el && typeof el.value === 'string') hay.push(el.value);
    }
    hay.push(document.title);
    const blob = hay.join(' ');
    return reals.filter((r) => blob.includes(r));
  }

  window.__anon = { groups, suggest, suggestMoney, apply, verify, textNodes, TENANT };
  return 'anonymize-page.js ready — __anon.groups() 先看分群，再 suggest()／apply()／verify()';
})();
