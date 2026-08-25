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

  /* ---------- 章节定位 ----------
   * chs: [{ t, ... }] 对象数组,按 t 递增;找最后一个 t <= 时刻的下标
   */
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
      var i = chapterIndex(chapters, t);
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
      var i = chapterIndex(chapters, a.currentTime);
      if (i > 0) {
        a.currentTime = chapters[i - 1].t;
        paintChap(a.currentTime);
        a.play();
      }
    });
    p.querySelector('.bp-next').addEventListener('click', function () {
      if (!chapters.length) return;
      var i = chapterIndex(chapters, a.currentTime);
      if (i < chapters.length - 1) {
        a.currentTime = chapters[i + 1].t;
        paintChap(a.currentTime);
        a.play();
      }
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
          paintChap(a.currentTime);
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
    });

    a.addEventListener('play', function () {
      panels.forEach(function (o) {
        var oa = o.querySelector('.bp-audio');
        if (oa !== a && !oa.paused) oa.pause();
      });
      syncButtons();
    });
    a.addEventListener('pause', function () { syncButtons(); });

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

  applyRate();
})();
