/* 世界一隅 · 听书播放器核心
 * 断点续播(localStorage 静默恢复)/ 倍速 / 睡眠定时 / 全局悬浮条
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
  var SAVE_INTERVAL = 5000;   // 进度写盘节流

  var panels = Array.prototype.slice.call(document.querySelectorAll('.bp-shell'));
  if (!panels.length) return;

  var floatPlayer = document.getElementById('floatPlayer');
  var fpJump = document.getElementById('fpJump');
  var fpCover = document.getElementById('fpCover');
  var fpTitle = document.getElementById('fpTitle');
  var fpTimes = document.getElementById('fpTimes');
  var fpPlay = document.getElementById('fpPlay');
  var fpBar = document.getElementById('fpBar');
  var hasFloat = !!(floatPlayer && fpPlay && fpBar);

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
  function iconPlay(state) { return state ? '❚❚' : '▶'; }

  /* ---------- 每个书卡面板 ---------- */
  var store = read(KEY_PROGRESS, {});       // { src: {t,d} }
  var rate = read(KEY_RATE, 1);
  var sleepIdx = 0;                          // SLEEP_MIN 下标,0=关
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
      p.querySelector('.bp-play').textContent = iconPlay(a.paused);
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
    var btn = p.querySelector('.bp-sleep');
    if (sleepIdx > 0) {
      var remain = Math.max(0, Math.ceil((sleepDeadline - Date.now()) / 1000));
      btn.textContent = '☾ ' + (remain >= 3600 ? Math.floor(remain / 3600) + 'h' + pad(Math.floor((remain % 3600) / 60)) : pad(Math.floor(remain / 60)) + ':' + pad(remain % 60));
    } else {
      btn.textContent = '☾';
    }
  }

  function clearSleep() {
    clearInterval(sleepTimer);
    sleepTimer = null;
    sleepIdx = 0;
  }

  /* ---------- 悬浮条 ---------- */
  var active = null; // 当前挂的 audio

  function paintFloat(a) {
    if (!hasFloat || !a) return;
    active = a;
    var panel = a.closest('.bp-shell');
    fpCover.src = panel.dataset.cover;
    fpTitle.textContent = panel.dataset.title;
    fpPlay.textContent = iconPlay(a.paused);
    fpTimes.textContent = fmt(a.currentTime) + ' / ' + fmt(a.duration || 0);
    var max = fpBar.max;
    var ratio = a.duration ? a.currentTime / a.duration : 0;
    fpBar.value = String(Math.round(ratio * max));
    floatPlayer.hidden = false;
  }

  function bindFloat() {
    floatPlayer.addEventListener('click', function (e) {
      // 悬浮条内部按钮、进度条之外点击 = 面板反而不是打开;只有"回到播放器"按钮做滚动
    });
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
    fpBar.addEventListener('input', function () {
      if (!active || !active.duration) return;
      active.currentTime = (Number(fpBar.value) / Number(fpBar.max)) * active.duration;
      paintFloat(active);
    });
  }

  /* ---------- 面板事件 ---------- */
  panels.forEach(function (p) {
    var a = p.querySelector('.bp-audio');
    var bar = p.querySelector('.bp-bar');
    var cur = p.querySelector('.bp-cur');

    p.querySelector('.bp-play').addEventListener('click', function () {
      if (a.paused) a.play().catch(function () { toast(p, '播放失败,请检查网络后重试'); });
      else a.pause();
    });

    bar.addEventListener('input', function () {
      if (a.duration) a.currentTime = (Number(bar.value) / Number(bar.max)) * a.duration;
    });

    /* 倍速:循环 1 → 1.25 → 1.5 → 2 */
    p.querySelector('.bp-rate').addEventListener('click', function () {
      var i = RATES.indexOf(rate);
      rate = RATES[(i + 1) % RATES.length];
      write(KEY_RATE, rate);
      applyRate();
    });

    /* 睡眠定时:0 → 15 → 30 → 45 → 60 → 0 */
    p.querySelector('.bp-sleep').addEventListener('click', function () {
      clearSleep();
      sleepIdx = (sleepIdx + 1) % SLEEP_MIN.length;
      if (sleepIdx > 0) {
        sleepDeadline = Date.now() + SLEEP_MIN[sleepIdx] * 60000;
        sleepTimer = setInterval(function () {
          var remain = sleepDeadline - Date.now();
          if (remain <= 0) {
            clearSleep();
            panels.forEach(function (o) { o.querySelector('.bp-audio').pause(); });
            syncButtons();
            paintFloat(active);
            toast(p, '睡眠定时到,已暂停 ☾');
            return;
          }
          paintSleepBtn(p);
          if (hasFloat) paintFloat(active);
        }, 1000);
      }
      paintSleepBtn(p);
    });

    a.addEventListener('loadedmetadata', function () {
      cur.textContent = fmt(a.currentTime);
      p.querySelector('.bp-dur').textContent = fmt(a.duration);
      a.playbackRate = rate;

      /* 断点续播:记录在且没听完 → 静默恢复 + 一条轻提示 */
      var rec = store[a.src];
      if (rec && rec.t && rec.t > 5 && rec.t < rec.d - 10) {
        a.currentTime = rec.t;
        toast(p, '已续播 ' + fmt(rec.t));
      }
    });

    a.addEventListener('timeupdate', function () {
      cur.textContent = fmt(a.currentTime);
      bar.value = String(a.duration ? Math.round((a.currentTime / a.duration) * Number(bar.max)) : 0);
      if (hasFloat && active === a) paintFloat(a);
    });

    a.addEventListener('play', function () {
      /* 同时只播一本:播放新书时暂停其他面板 */
      panels.forEach(function (o) {
        var oa = o.querySelector('.bp-audio');
        if (oa !== a && !oa.paused) oa.pause();
      });
      syncButtons(); paintFloat(a);
    });
    a.addEventListener('pause', function () { syncButtons(); paintFloat(a); });

    a.addEventListener('ended', function () {
      delete store[a.src];
      write(KEY_PROGRESS, store);
      toast(p, '播放完成,进度已清零');
    });

    /* 定时写进度(播放中才值得写) */
    setInterval(function () {
      if (!a.paused && a.duration) {
        store[a.src] = { t: a.currentTime, d: a.duration };
        write(KEY_PROGRESS, store);
      }
    }, SAVE_INTERVAL);

    /* 暂停/切换页面时也写一次 */
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
