/* 世界一隅 · 听书播放器核心 v3
 * 支持「书 = 章节列表」统一模型:
 *   - 单文件型(幸福在内):整本一个 mp3,各章节靠 t 时间定位,章节间同文件秒切
 *   - 多文件型(内心的修炼):每章节一个独立 mp3,靠 src 切换文件
 * 断点续播(localStorage 按 bookId)/ 倍速 / 睡眠定时 / 章节跳转 / ±15s / 自定义进度线 / 全局悬浮条
 * 依赖:听书页 .bp-shell 结构 + #floatPlayer
 */
(function () {
  'use strict';
  if (window.__wcPlayer) return;
  window.__wcPlayer = true;

  /* ---------- 一次性旧进度迁移 ----------
   * v1 按音频 src(绝对 URL)记录;v2 改按 bookId 记录(单文件/多文件均支持)。
   * 《幸福的内在》仍为单文件,t 全局有效,直接保留;《内心的修炼》旧为单文件、
   * 按全局秒存,需按旧章节起始时间折成新章节文件的 {idx, t_local}。
   * 仅当 v2 尚无该书记录时写入,避免覆盖新数据;迁移失败静默,不影响播放。
   */
  (function migrateProgress() {
    try {
      var oldKey = 'wc.audio.progress.v1';
      var newKey = 'wc.audio.progress.v2';
      var oldRaw = window.localStorage.getItem(oldKey);
      if (!oldRaw) return;
      var oldStore = JSON.parse(oldRaw);
      var next;
      try { var n = window.localStorage.getItem(newKey); next = n ? JSON.parse(n) : {}; }
      catch (e) { next = {}; }
      /* 旧《内心的修炼》整本单文件:各章节全局起始秒(与切分前 yaml 的 t 一致) */
      var NEIXIN_STARTS = [0, 199, 3647.9, 11909.7, 14622.9, 16825.5, 19693, 21797.9, 24462.7, 26577.3, 28701.9];
      var changed = false;
      Object.keys(oldStore).forEach(function (key) {
        var rec = oldStore[key];
        if (!rec || typeof rec.t !== 'number') return;
        var path;
        try { path = new URL(key, location.origin).pathname; } catch (e) { path = String(key); }
        var bookId = null, val = null;
        if (/happiness/i.test(path)) {
          bookId = 'xingfu';
          val = { t: rec.t, d: rec.d };
        } else if (/mind-practice/i.test(path)) {
          var gt = rec.t, idx = 0;
          for (var k = 0; k < NEIXIN_STARTS.length; k++) { if (NEIXIN_STARTS[k] <= gt) idx = k; else break; }
          bookId = 'neixin';
          val = { idx: idx, t: Math.max(0, gt - NEIXIN_STARTS[idx]) };
        }
        if (bookId && !next[bookId]) { next[bookId] = val; changed = true; }
      });
      if (changed) {
        window.localStorage.setItem(newKey, JSON.stringify(next));
        window.localStorage.removeItem(oldKey);
      }
    } catch (e) { /* 忽略 */ }
  })();

  var KEY_PROGRESS = 'wc.audio.progress.v2';
  var KEY_RATE = 'wc.audio.rate.v1';
  var RATES = [1, 1.25, 1.5, 2];
  var SAVE_INTERVAL = 5000;
  var SKIP_SEC = 15;

  var panels = Array.prototype.slice.call(document.querySelectorAll('.bp-shell'));
  if (!panels.length) return;

  /* ---------- 工具 ---------- */
  function read(key, fallback) {
    try {
      var raw = window.localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) { return fallback; }
  }
  function write(key, val) {
    try { window.localStorage.setItem(key, JSON.stringify(val)); } catch (e) { /* 隐私模式静默 */ }
  }
  function pad(n) { return n < 10 ? '0' + n : '' + n; }
  function fmt(sec) {
    if (!isFinite(sec) || sec < 0) sec = 0;
    var s = Math.round(sec);
    var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = s % 60;
    return (h ? h + ':' + pad(m) : pad(m)) + ':' + pad(ss);
  }
  function chapterIndex(chs, t) {
    var i = 0;
    for (var k = 0; k < chs.length; k++) { if (chs[k].t <= t) i = k; else break; }
    return i;
  }
  /* 归一化 src,统一成 pathname 便于比较(浏览器会把相对 src 解析成绝对 URL) */
  function normSrc(s) {
    if (!s) return '';
    try { var u = new URL(s, location.origin); return u.pathname + u.search; }
    catch (e) { return String(s); }
  }

  /* ---------- 章节定位 ----------
   * chs: [{ t, src, el, name }] src 已归一化;分单文件(时间索引)与多文件(src 索引)
   */
  /* ---------- 自定义进度线 ----------
   * getAudio: () => audio 或 null —— 拖动/键盘时取当前真 audio
   */
  function bindSeekline(lineEl, fillEl, knobEl, getAudio, onSeek) {
    var max = Number(lineEl.getAttribute('aria-valuemax') || 1000);
    var paint = function (t, d) {
      var pct = d && t >= 0 ? Math.min(1, t / d) : 0;
      fillEl.style.width = (pct * 100) + '%';
      knobEl.style.left = (pct * 100) + '%';
      lineEl.setAttribute('aria-valuenow', String(Math.round(pct * max)));
    };
    var seekFromEvent = function (e) {
      var au = getAudio();
      if (!au) return;
      var rect = lineEl.getBoundingClientRect();
      var ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
      var t = ratio * (au.duration || 0);
      if (onSeek) onSeek(t);
      paint(t, au.duration);
    };
    var dragging = false;
    lineEl.addEventListener('pointerdown', function (e) {
      dragging = true;
      if (lineEl.setPointerCapture) lineEl.setPointerCapture(e.pointerId);
      seekFromEvent(e);
    });
    lineEl.addEventListener('pointermove', function (e) { if (dragging) seekFromEvent(e); });
    lineEl.addEventListener('pointerup', function (e) { if (dragging) { dragging = false; seekFromEvent(e); } });
    lineEl.addEventListener('pointercancel', function () { dragging = false; });
    lineEl.addEventListener('keydown', function (e) {
      var au = getAudio();
      if (!au || !au.duration) return;
      var step = au.duration / 20;
      if (e.key === 'ArrowRight') { au.currentTime = Math.min(au.duration, au.currentTime + step); }
      else if (e.key === 'ArrowLeft') { au.currentTime = Math.max(0, au.currentTime - step); }
      else return;
      e.preventDefault();
    });
    return paint;
  }

  /* ---------- 全局状态 ---------- */
  var store = read(KEY_PROGRESS, {});
  var rate = read(KEY_RATE, 1);
  var sleepMin = 0;            /* 0 = 未定时;>0 = 定时分钟数 */
  var sleepDeadline = 0;
  var sleepTimer = null;
  var toastTimer = null;

  function toast(panel, text) {
    var t = panel.querySelector('.bp-toast');
    t.textContent = text;
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.hidden = true; }, 3200);
  }
  function syncButtons() {
    panels.forEach(function (p) {
      var a = p.querySelector('.bp-audio');
      p.classList.toggle('is-playing', !a.paused);
    });
  }
  function applyRate() {
    panels.forEach(function (p) {
      p.querySelector('.bp-audio').playbackRate = rate;
      p.querySelector('.bp-rate').textContent = rate + 'x';
    });
  }
  function paintSleepBtn(p) {
    var b = p.querySelector('.bp-sleep');
    var label = p.querySelector('.bp-sleep-label');
    if (sleepMin > 0) {
      var remain = Math.max(0, Math.ceil((sleepDeadline - Date.now()) / 1000));
      label.textContent = remain >= 3600
        ? (Math.floor(remain / 3600) + 'h' + pad(Math.floor((remain % 3600) / 60)))
        : pad(Math.floor(remain / 60)) + ':' + pad(remain % 60);
      b.classList.add('is-on');
    } else {
      label.textContent = '☾';
      b.classList.remove('is-on');
    }
  }
  function clearSleep() {
    clearInterval(sleepTimer);
    sleepTimer = null;
    sleepMin = 0;
  }
  function setSleep(p, minutes) {
    clearSleep();
    sleepMin = minutes;
    sleepDeadline = Date.now() + minutes * 60000;
    sleepTimer = setInterval(function () {
      if (sleepDeadline - Date.now() <= 0) {
        clearSleep();
        panels.forEach(function (o) { o.querySelector('.bp-audio').pause(); });
        syncButtons();
        toast(p, '睡眠定时到,已暂停 ☾');
      }
      panels.forEach(function (o) { paintSleepBtn(o); });
    }, 1000);
    panels.forEach(function (o) { paintSleepBtn(o); });
  }

  /* ---------- 面板初始化 ---------- */
  panels.forEach(function (p) {
    var a = p.querySelector('.bp-audio');
    var seekline = p.querySelector('.bp-seekline');
    var cur = p.querySelector('.bp-cur');
    var durEl = p.querySelector('.bp-dur');
    var chapEl = p.querySelector('.bp-chap');
    var drawer = p.querySelector('.bp-drawer');
    var listBtn = p.querySelector('.bp-listbtn');

    var bookId = p.dataset.book || 'book';
    var bookSrc = normSrc(p.dataset.src);
    var chapters = Array.prototype.slice.call(p.querySelectorAll('.bp-marks li button')).map(function (b) {
      return {
        t: Number(b.dataset.t) || 0,
        src: normSrc(b.dataset.src) || bookSrc,
        el: b,
        name: b.querySelector('.m-name') ? b.querySelector('.m-name').textContent : ''
      };
    });
    /* 单文件型 = 所有章节共用书本同一个 src;多文件型 = 各章节 src 不同 */
    var singleSrc = chapters.every(function (c) { return c.src === bookSrc; });

    var paintLine = bindSeekline(seekline, p.querySelector('.bp-fill'), p.querySelector('.bp-knob'), function () { return a; }, function (t) {
      a.currentTime = t;
    });

    function loadedIdx() {
      var s = normSrc(a.src);
      for (var k = 0; k < chapters.length; k++) { if (chapters[k].src === s) return k; }
      return -1;
    }
    function currentIdx() {
      if (singleSrc) return chapterIndex(chapters, a.currentTime);
      var i = loadedIdx();
      return i < 0 ? 0 : i;
    }

    /* 切集:跳转到第 i 集。跨文件时换 a.src,由 loadedmetadata 吃 pendingSeek;同文件直接 seek */
    var pendingSeek = null;
    function setChapter(i, autoplay) {
      var c = chapters[i];
      if (!c) return;
      var t = c.t;
      var needLoad = normSrc(a.src) !== c.src;
      if (needLoad) {
        pendingSeek = t;
        a.src = c.src;
      } else {
        a.currentTime = t + 0.05;
      }
      if (autoplay) a.play().catch(function () { toast(p, '播放失败,请检查网络后重试'); });
      paintChap(t);
    }

    function paintChap(t) {
      if (!chapters.length) { chapEl.textContent = ''; return; }
      var i = singleSrc ? chapterIndex(chapters, t) : loadedIdx();
      if (i < 0) i = 0;
      var c = chapters[i];
      chapEl.textContent = '第 ' + (i + 1) + ' 集 · ' + (c.name || '');
      chapters.forEach(function (ch, k) { ch.el.classList.toggle('is-current', k === i); });
    }

    /* 断点续播:按 bookId 恢复。单文件直接定位;多文件先切到存档那一集 */
    var resumed = false;
    function resumeIfNeeded() {
      if (resumed) return;
      resumed = true;
      var rec = store[bookId];
      if (!rec) return;
      if (singleSrc) {
        var d = rec.d || a.duration;
        if (rec.t > 5 && (d ? rec.t < d - 10 : true)) {
          a.currentTime = rec.t;
          toast(p, '已续播 ' + fmt(rec.t));
        }
      } else {
        var i = (rec.idx != null && rec.idx >= 0 && rec.idx < chapters.length) ? rec.idx : 0;
        var c = chapters[i];
        if (normSrc(a.src) !== c.src) {
          pendingSeek = rec.t;      /* 跨文件:换 src 后由 loadedmetadata 吃到精确位置 */
          a.src = c.src;
        } else {
          var dd = rec.d || a.duration;
          if (rec.t > 5 && (dd ? rec.t < dd - 10 : true)) a.currentTime = rec.t;
        }
        paintChap(rec.t);
        toast(p, '已续播 第 ' + (i + 1) + ' 集');
      }
    }

    p.querySelector('.bp-play').addEventListener('click', function () {
      if (a.paused) { a.play().catch(function () { toast(p, '播放失败,请检查网络后重试'); }); }
      else a.pause();
    });
    p.querySelector('.bp-rev').addEventListener('click', function () {
      a.currentTime = Math.max(0, a.currentTime - SKIP_SEC);
    });
    p.querySelector('.bp-fwd').addEventListener('click', function () {
      a.currentTime = Math.min((a.duration || 0) || Number.MAX_SAFE_INTEGER, a.currentTime + SKIP_SEC);
    });
    p.querySelector('.bp-prev').addEventListener('click', function () {
      if (!chapters.length) return;
      var i = currentIdx();
      /* 单文件型:已是第一集但听到中段,退回到开头;否则切上一集 */
      if (singleSrc && i === 0 && a.currentTime > 4) {
        a.currentTime = 0; paintChap(0); a.play();
      } else if (i > 0) {
        setChapter(i - 1, true);
      }
    });
    p.querySelector('.bp-next').addEventListener('click', function () {
      if (!chapters.length) return;
      var i = currentIdx();
      if (i < chapters.length - 1) setChapter(i + 1, true);
    });

    if (listBtn && drawer) {
      listBtn.setAttribute('aria-expanded', 'false');
      listBtn.addEventListener('click', function () {
        drawer.hidden = !drawer.hidden;
        listBtn.setAttribute('aria-expanded', drawer.hidden ? 'false' : 'true');
      });
      p.querySelector('.bp-drawer-close').addEventListener('click', function () { drawer.hidden = true; });
      document.addEventListener('click', function (e) {
        if (!drawer.hidden && !drawer.contains(e.target) && !listBtn.contains(e.target)) drawer.hidden = true;
      });
      chapters.forEach(function (c) {
        c.el.addEventListener('click', function () {
          setChapter(chapters.indexOf(c), true);
          drawer.hidden = true;
        });
      });
    }

    p.querySelector('.bp-rate').addEventListener('click', function () {
      var i = RATES.indexOf(rate);
      rate = RATES[(i + 1) % RATES.length];
      write(KEY_RATE, rate);
      applyRate();
    });

    var sleepBtn = p.querySelector('.bp-sleep');
    var sleepPop = p.querySelector('.bp-sleep-pop');
    if (sleepBtn && sleepPop) {
      sleepBtn.addEventListener('click', function () {
        sleepPop.hidden = !sleepPop.hidden;
        if (!sleepPop.hidden) {
          var inp = sleepPop.querySelector('.bp-sleep-input');
          if (inp) { inp.value = ''; inp.focus(); }
        }
      });
      sleepPop.querySelector('.bp-sleep-close').addEventListener('click', function () {
        sleepPop.hidden = true;
      });
      var applySleep = function (minutes) {
        setSleep(p, minutes);
        sleepPop.hidden = true;
        toast(p, '睡眠定时 ' + minutes + ' 分钟,到点自动暂停');
      };
      sleepPop.querySelectorAll('.bp-sleep-quicks button').forEach(function (b) {
        b.addEventListener('click', function () { applySleep(Number(b.dataset.min)); });
      });
      var sleepInput = sleepPop.querySelector('.bp-sleep-input');
      var sleepSet = sleepPop.querySelector('.bp-sleep-set');
      var sleepCustom = function () {
        var v = Math.round(Number(sleepInput.value));
        if (!isFinite(v) || v < 1 || v > 240) { toast(p, '请输入 1-240 分钟'); return; }
        applySleep(v);
      };
      sleepSet.addEventListener('click', sleepCustom);
      sleepInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') sleepCustom(); });
      sleepPop.querySelector('.bp-sleep-off').addEventListener('click', function () {
        clearSleep();
        panels.forEach(function (o) { paintSleepBtn(o); });
        sleepPop.hidden = true;
        toast(p, '睡眠定时已取消');
      });
      document.addEventListener('click', function (e) {
        if (!sleepPop.hidden && !sleepPop.contains(e.target) && !sleepBtn.contains(e.target)) {
          sleepPop.hidden = true;
        }
      });
    }

    a.addEventListener('loadedmetadata', function () {
      durEl.textContent = fmt(a.duration);
      a.playbackRate = rate;
      if (pendingSeek != null) {
        a.currentTime = pendingSeek; pendingSeek = null;
        paintChap(a.currentTime);
      } else {
        resumeIfNeeded();
      }
      paintLine(a.currentTime, a.duration);
    });
    a.addEventListener('timeupdate', function () {
      cur.textContent = fmt(a.currentTime);
      paintChap(a.currentTime);
      paintLine(a.currentTime, a.duration);
    });

    a.addEventListener('play', function () {
      panels.forEach(function (o) {
        var oa = o.querySelector('.bp-audio');
        if (oa !== a && !oa.paused) oa.pause();
      });
      syncButtons();
    });
    a.addEventListener('pause', function () { syncButtons(); });

    /* 连播:本集播完自动接下一集;最后一集播完清进度 */
    a.addEventListener('ended', function () {
      var i = currentIdx();
      if (i < chapters.length - 1) {
        setChapter(i + 1, true);
        toast(p, '已连续播放下一集');
      } else {
        delete store[bookId];
        write(KEY_PROGRESS, store);
        toast(p, '全书播放完成,进度已清零');
      }
    });

    function saveNow() {
      var i = currentIdx();
      if (!a.duration) { write(KEY_PROGRESS, store); return; }
      var rec = { t: a.currentTime, d: a.duration };
      if (!singleSrc) rec.idx = i;
      store[bookId] = rec;
      write(KEY_PROGRESS, store);
    }
    setInterval(function () {
      if (!a.paused && a.duration) saveNow();
    }, SAVE_INTERVAL);
    document.addEventListener('visibilitychange', function () { if (document.hidden) saveNow(); });
    window.addEventListener('pagehide', saveNow);
  });

  applyRate();
})();
