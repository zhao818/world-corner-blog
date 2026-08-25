/* 世界一隅 · 听书播放器核心 v2
 * 断点续播(localStorage 静默恢复)/ 倍速 / 睡眠定时 / 章节跳转 / ±15s / 自定义进度线 / 全局悬浮条
 * 依赖:听书页 .bp-shell 结构 + #floatPlayer
 */
(function () {
  'use strict';
  if (window.__wcPlayer) return;
  window.__wcPlayer = true;

  var KEY_PROGRESS = 'wc.audio.progress.v1';
  var KEY_RATE = 'wc.audio.rate.v1';
  var RATES = [1, 1.25, 1.5, 2];
  var SLEEP_MIN = [0, 15, 30, 45, 60];
  var SAVE_INTERVAL = 5000;
  var SKIP_SEC = 15;

  var panels = Array.prototype.slice.call(document.querySelectorAll('.bp-shell'));
  if (!panels.length) return;

  var floatPlayer = document.getElementById('floatPlayer');
  var fpJump = document.getElementById('fpJump');
  var fpCover = document.getElementById('fpCover');
  var fpTitle = document.getElementById('fpTitle');
  var fpTimes = document.getElementById('fpTimes');
  var fpPlay = document.getElementById('fpPlay');
  var fpPrev = document.getElementById('fpPrev');
  var fpNext = document.getElementById('fpNext');
  var fpSeek = document.getElementById('fpSeek');
  var fpFill = document.getElementById('fpFill');
  var fpKnob = document.getElementById('fpKnob');
  var hasFloat = !!(floatPlayer && fpPlay && fpSeek);

  var active = null;   // 悬浮条当前关联的 audio
  var fpPaint = null;  // 浮条进度线绘制函数

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

  /* ---------- 自定义进度线 ----------
   * getAudio: () => audio 或 null  —— 拖动/键盘时取当前真 audio
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
  var sleepIdx = 0;
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
    var label = p.querySelector('.bp-sleep-label');
    if (sleepIdx > 0) {
      var remain = Math.max(0, Math.ceil((sleepDeadline - Date.now()) / 1000));
      label.textContent = remain >= 3600
        ? (Math.floor(remain / 3600) + 'h' + pad(Math.floor((remain % 3600) / 60)))
        : pad(Math.floor(remain / 60)) + ':' + pad(remain % 60);
    } else {
      label.textContent = '☾';
    }
  }
  function clearSleep() {
    clearInterval(sleepTimer);
    sleepTimer = null;
    sleepIdx = 0;
  }

  /* ---------- 悬浮条 ---------- */
  function paintFloat(a) {
    if (!hasFloat || !a) return;
    active = a;
    var panel = a.closest('.bp-shell');
    fpCover.src = panel.dataset.cover;
    fpTitle.textContent = panel.dataset.title;
    fpTimes.textContent = fmt(a.currentTime) + ' / ' + fmt(a.duration || 0);
    fpPlay.classList.toggle('is-playing', !a.paused);
    var chs = Array.prototype.slice.call(panel.querySelectorAll('.bp-marks li button')).map(function (b) { return Number(b.dataset.t); });
    fpPrev.hidden = fpNext.hidden = chs.length < 2;
    if (fpPaint) fpPaint(a.currentTime, a.duration);
    floatPlayer.hidden = false;
  }

  function bindFloat() {
    fpJump.addEventListener('click', function () {
      if (active) {
        var card = active.closest('.book-card');
        if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });
    fpPlay.addEventListener('click', function () {
      if (!active) return;
      if (active.paused) active.play(); else active.pause();
    });
    fpPrev.addEventListener('click', function () {
      if (!active) return;
      var panel = active.closest('.bp-shell');
      var chs = Array.prototype.slice.call(panel.querySelectorAll('.bp-marks li button')).map(function (b) { return Number(b.dataset.t); });
      var i = chapterIndex(chs, active.currentTime);
      if (i > 0) { active.currentTime = chs[i - 1]; active.play(); }
    });
    fpNext.addEventListener('click', function () {
      if (!active) return;
      var panel = active.closest('.bp-shell');
      var chs = Array.prototype.slice.call(panel.querySelectorAll('.bp-marks li button')).map(function (b) { return Number(b.dataset.t); });
      var i = chapterIndex(chs, active.currentTime);
      if (i < chs.length - 1) { active.currentTime = chs[i + 1]; active.play(); }
    });
    fpPaint = bindSeekline(fpSeek, fpFill, fpKnob, function () { return active; }, function (t) {
      if (active) active.currentTime = t;
    });
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
    var chapters = Array.prototype.slice.call(p.querySelectorAll('.bp-marks li button')).map(function (b) {
      return {
        t: Number(b.dataset.t),
        el: b,
        name: b.querySelector('.m-name') ? b.querySelector('.m-name').textContent : ''
      };
    });
    var paintLine = bindSeekline(seekline, p.querySelector('.bp-fill'), p.querySelector('.bp-knob'), function () { return a; }, function (t) {
      a.currentTime = t;
    });

    function paintChap(t) {
      if (!chapters.length) { chapEl.textContent = ''; return; }
      var i = chapterIndex(chapters.map(function (c) { return c.t; }), t);
      chapEl.textContent = '第 ' + (i + 1) + ' 集 · ' + chapters[i].name;
      chapters.forEach(function (c, k) { c.el.classList.toggle('is-current', k === i); });
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
      var i = chapterIndex(chapters.map(function (c) { return c.t; }), a.currentTime);
      if (i > 0) { a.currentTime = chapters[i - 1].t; a.play(); }
    });
    p.querySelector('.bp-next').addEventListener('click', function () {
      if (!chapters.length) return;
      var i = chapterIndex(chapters.map(function (c) { return c.t; }), a.currentTime);
      if (i < chapters.length - 1) { a.currentTime = chapters[i + 1].t; a.play(); }
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
          a.currentTime = c.t + 0.05;
          a.play();
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

    p.querySelector('.bp-sleep').addEventListener('click', function () {
      clearSleep();
      sleepIdx = (sleepIdx + 1) % SLEEP_MIN.length;
      if (sleepIdx > 0) {
        sleepDeadline = Date.now() + SLEEP_MIN[sleepIdx] * 60000;
        sleepTimer = setInterval(function () {
          if (sleepDeadline - Date.now() <= 0) {
            clearSleep();
            panels.forEach(function (o) { o.querySelector('.bp-audio').pause(); });
            syncButtons();
            paintFloat(active);
            toast(p, '睡眠定时到,已暂停 ☾');
            return;
          }
          panels.forEach(function (o) { paintSleepBtn(o); });
        }, 1000);
      }
      panels.forEach(function (o) { paintSleepBtn(o); });
    });

    a.addEventListener('loadedmetadata', function () {
      durEl.textContent = fmt(a.duration);
      a.playbackRate = rate;
      var rec = store[a.src];
      if (rec && rec.t && rec.t > 5 && rec.t < rec.d - 10) {
        a.currentTime = rec.t;
        toast(p, '已续播 ' + fmt(rec.t));
      }
      paintChap(a.currentTime);
    });
    a.addEventListener('timeupdate', function () {
      cur.textContent = fmt(a.currentTime);
      paintChap(a.currentTime);
      paintLine(a.currentTime, a.duration);
      if (hasFloat && active === a) paintFloat(a);
    });

    a.addEventListener('play', function () {
      panels.forEach(function (o) {
        var oa = o.querySelector('.bp-audio');
        if (oa !== a && !oa.paused) oa.pause();
      });
      syncButtons();
      paintFloat(a);
    });
    a.addEventListener('pause', function () { syncButtons(); paintFloat(a); });

    a.addEventListener('ended', function () {
      delete store[a.src];
      write(KEY_PROGRESS, store);
      toast(p, '播放完成,进度已清零');
    });

    setInterval(function () {
      if (!a.paused && a.duration) {
        store[a.src] = { t: a.currentTime, d: a.duration };
        write(KEY_PROGRESS, store);
      }
    }, SAVE_INTERVAL);
    function saveNow() {
      if (a.duration) store[a.src] = { t: a.currentTime, d: a.duration };
      write(KEY_PROGRESS, store);
    }
    document.addEventListener('visibilitychange', function () { if (document.hidden) saveNow(); });
    window.addEventListener('pagehide', saveNow);
  });

  if (hasFloat) bindFloat();
  applyRate();
})();
