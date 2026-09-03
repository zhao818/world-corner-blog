/**
 * 世界一隅 · 听书页面推广与小程序生态承接控制器
 * 支持：微信小程序码浮层、金句海报与社交文案浏览、一键复制到剪贴板、书籍金句快速定位
 */
(function () {
  'use strict';

  var POSTERS = [
    {
      title: '海报 1 · 核心命题',
      quote: '文明每一级真实的跃迁，都是一场“喂饱”的革命。',
      desc: '先喂饱身体，再喂饱思想。我们这一代人，身体不挨饿了，思想却在饿肚子。',
      img: '/images/文明阶梯-海报1-喂养革命_1787839950.png',
      bookId: 'wenming'
    },
    {
      title: '海报 2 · 精神饥饿',
      quote: '信息过载、意义缺失、停不下来的刷——这就是当代的“饿肚子”。',
      desc: '当身体不再挨饿，饥饿会升到哪里？升到心智层。下一场跃迁，必然发生在精神喂养。',
      img: '/images/文明阶梯-海报2-精神饥饿_1787839982.png',
      bookId: 'wenming'
    },
    {
      title: '海报 3 · 幸福真相',
      quote: '一个人的幸福锁在人群里。',
      desc: '你心修得再好，身边都是被消耗的人，你不可能独善其身地幸福。一群人的幸福，才是文明真正站上的那一级阶梯。',
      img: '/images/文明阶梯-海报3-幸福真相_1787840008.png',
      bookId: 'xingfu'
    },
    {
      title: '海报 4 · 灯塔意象',
      quote: '我们做的所有事，本质是一件事——亮着，给方向。',
      desc: '不劝善、不指摘、不呼吁“利他”；只把焦点放到人面前，他自己会走。就像海上迷路的人，看见远处有盏灯塔。',
      img: '/images/文明阶梯-海报4-灯塔意象_1787840047.png',
      bookId: 'wenming'
    },
    {
      title: '海报 5 · 传灯概念',
      quote: '不是靠一个人成圣，是靠每个人做一束光。',
      desc: '让身边足够多的人开始思考同一件事。文明的火种，是一盏灯点亮另一盏灯。',
      img: '/images/文明阶梯-海报5-传灯概念_1787840122.png',
      bookId: 'shendu'
    },
    {
      title: '海报 6 · 历史跃迁',
      quote: '一万年前种麦子，两百年前蒸汽机，今天精神喂养。',
      desc: '文明每一次跃迁的本质，不是工具变了，而是人从某种生存重负里被解放了出来。',
      img: '/images/文明阶梯-海报6-喂养革命历史_1787840145.png',
      bookId: 'tianjian'
    },
    {
      title: '海报 7 · 升级即幸福',
      quote: '文明每一级真实的跃迁，本质都是脱离本能绑架一步。',
      desc: '向搞钱党、情爱党各路人马摆下擂台：物欲的瘾、情爱的执、生死的畏，本能的设限，也是觉醒的考题。',
      img: '/images/文明阶梯-海报7-升级即幸福_1787840169.png',
      bookId: 'xingfu'
    },
    {
      title: '海报 8 · 每日必修',
      quote: '知行合一：喂身 · 喂脑 · 觉察心 · 传灯。',
      desc: '把庞大的思想体系落到每天能上手做的四件事上。给精神喂主食，在日常里筑牢内心地基。',
      img: '/images/文明阶梯-海报8-每日必修_1787840190.png',
      bookId: 'shendu'
    }
  ];

  function initPromo() {
    var modal = document.getElementById('promo-modal');
    if (!modal) return;

    var btnOpenMp = document.getElementById('btn-open-mp-modal');
    var btnOpenShare = document.getElementById('btn-open-share-modal');
    var btnClose = document.getElementById('btn-close-promo');
    var tabMp = document.getElementById('tab-btn-mp');
    var tabPosters = document.getElementById('tab-btn-posters');
    var panelMp = document.getElementById('panel-mp');
    var panelPosters = document.getElementById('panel-posters');

    var posterSelect = document.getElementById('poster-select');
    var posterImg = document.getElementById('poster-display-img');
    var posterQuote = document.getElementById('poster-quote-text');
    var posterDesc = document.getElementById('poster-quote-desc');
    var btnViewFull = document.getElementById('btn-view-full-poster');
    var btnCopyQuote = document.getElementById('btn-copy-quote');
    var btnCopyWebUrl = document.getElementById('btn-copy-web-url');
    var toast = document.getElementById('promo-toast');

    function showToast(msg) {
      if (!toast) return;
      toast.textContent = msg;
      toast.hidden = false;
      toast.classList.add('visible');
      clearTimeout(toast.__timer);
      toast.__timer = setTimeout(function () {
        toast.classList.remove('visible');
        toast.hidden = true;
      }, 2500);
    }

    function openModal(tab) {
      modal.removeAttribute('hidden');
      modal.classList.add('is-active');
      modal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
      switchTab(tab || 'mp');
    }

    function closeModal(e) {
      if (e && e.preventDefault) e.preventDefault();
      modal.setAttribute('hidden', '');
      modal.classList.remove('is-active');
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }

    function switchTab(tab) {
      if (tab === 'mp') {
        tabMp.classList.add('active');
        tabPosters.classList.remove('active');
        panelMp.hidden = false;
        panelMp.classList.add('active');
        panelPosters.hidden = true;
        panelPosters.classList.remove('active');
      } else {
        tabPosters.classList.add('active');
        tabMp.classList.remove('active');
        panelPosters.hidden = false;
        panelPosters.classList.add('active');
        panelMp.hidden = true;
        panelMp.classList.remove('active');
      }
    }

    function updatePoster(idx) {
      var item = POSTERS[idx] || POSTERS[0];
      if (posterImg) posterImg.src = item.img;
      if (posterQuote) posterQuote.textContent = item.quote;
      if (posterDesc) posterDesc.textContent = item.desc;
      if (btnViewFull) btnViewFull.href = item.img;
    }

    if (btnOpenMp) {
      btnOpenMp.addEventListener('click', function () {
        openModal('mp');
      });
    }

    if (btnOpenShare) {
      btnOpenShare.addEventListener('click', function () {
        openModal('posters');
      });
    }

    // 绑定右上角及底部所有关闭按钮（支持 click 和 touchend）
    var closeButtons = modal.querySelectorAll('[data-close-promo]');
    closeButtons.forEach(function (btn) {
      btn.addEventListener('click', closeModal);
    });
    if (btnClose) {
      btnClose.addEventListener('click', closeModal);
    }

    modal.addEventListener('click', function (e) {
      if (e.target === modal || e.target.classList.contains('promo-modal-backdrop')) {
        closeModal(e);
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeModal();
    });

    if (tabMp) {
      tabMp.addEventListener('click', function () { switchTab('mp'); });
    }
    if (tabPosters) {
      tabPosters.addEventListener('click', function () { switchTab('posters'); });
    }

    if (posterSelect) {
      posterSelect.addEventListener('change', function () {
        var idx = parseInt(this.value, 10) || 0;
        updatePoster(idx);
      });
    }

    // 复制金句文案
    if (btnCopyQuote) {
      btnCopyQuote.addEventListener('click', function () {
        var idx = posterSelect ? (parseInt(posterSelect.value, 10) || 0) : 0;
        var item = POSTERS[idx] || POSTERS[0];
        var text = '【世界一隅 · 金句分享】\n' + item.quote + '\n\n' + item.desc + '\n\n完整连播有声书请访问：' + window.location.origin + '/audiobook/';
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(function () {
            showToast('✓ 金句文案已复制，可去朋友圈/小红书粘贴！');
          }).catch(function () {
            fallbackCopy(text);
          });
        } else {
          fallbackCopy(text);
        }
      });
    }

    // 复制网页链接
    if (btnCopyWebUrl) {
      btnCopyWebUrl.addEventListener('click', function () {
        var url = window.location.origin + '/audiobook/';
        var text = '世界一隅 · 听书 | 完整连播版（免登录、无广告、带睡眠定时）：' + url;
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(function () {
            showToast('✓ 听书网址已复制，可分享给微信好友！');
          }).catch(function () {
            fallbackCopy(text);
          });
        } else {
          fallbackCopy(text);
        }
      });
    }

    function fallbackCopy(str) {
      var ta = document.createElement('textarea');
      ta.value = str;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand('copy');
        showToast('✓ 已复制到剪贴板！');
      } catch (err) {
        showToast('请手动复制本页网址');
      }
      document.body.removeChild(ta);
    }

    // 为每本书的“提取金句”按钮绑定事件
    var quoteBtns = document.querySelectorAll('.book-quote-btn');
    quoteBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var bookId = btn.getAttribute('data-book-id');
        // 查找与该书最匹配的海报索引
        var targetIdx = 0;
        for (var i = 0; i < POSTERS.length; i++) {
          if (POSTERS[i].bookId === bookId) {
            targetIdx = i;
            break;
          }
        }
        if (posterSelect) {
          posterSelect.value = String(targetIdx);
          updatePoster(targetIdx);
        }
        openModal('posters');
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPromo);
  } else {
    initPromo();
  }
})();
