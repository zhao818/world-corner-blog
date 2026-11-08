/**
 * zen-graph.js
 * 世界一隅 · 知识星图 (Thought Constellation)
 * 原生 HTML5 Canvas 高性能力导向图引擎，完全自包含、零外部依赖。
 */

(function() {
  'use strict';

  function initZenGraph() {
    var canvas = document.getElementById('zen-graph-canvas');
    var container = document.getElementById('zen-graph-container');
    if (!canvas || !container) return;

    var ctx = canvas.getContext('2d');
    var isEn = document.documentElement.lang === 'en' || window.location.pathname.indexOf('/en/') === 0;

    // 状态机
    var width = container.clientWidth || 900;
    var height = container.clientHeight || 650;
    var dpr = window.devicePixelRatio || 1;

    var nodes = [];
    var links = [];
    var nodeMap = {};
    var activeFilter = 'all';
    var searchQuery = '';
    var showTags = true;
    var showLabels = true;

    // 视角变换 (平移与缩放)
    var transform = { x: width / 2, y: height / 2, k: 1 };
    var isDragging = false;
    var dragNode = null;
    var dragStart = { x: 0, y: 0 };
    var hoveredNode = null;
    var selectedNode = null;
    var focusedNodeId = null;

    // 物理仿真参数
    var alpha = 1;
    var alphaMin = 0.005;
    var alphaDecay = 0.022;
    var animFrameId = null;

    // 读取 URL 初始焦点
    var params = new URLSearchParams(window.location.search);
    if (params.get('focus')) {
      focusedNodeId = params.get('focus').replace(/\/+$/, '') + '/';
    }

    // 调整 Canvas 尺寸与高清屏适配
    function resize() {
      width = container.clientWidth || 900;
      height = Math.max(500, window.innerHeight - 200);
      container.style.height = height + 'px';
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = width + 'px';
      canvas.style.height = height + 'px';
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);
      restartSim();
    }

    // 主题色彩检测 (WCAG AA/AAA 对齐)
    function isDarkMode() {
      return document.body.classList.contains('dark') || 
             document.documentElement.getAttribute('data-theme') === 'dark';
    }

    function getThemePalette() {
      var dark = isDarkMode();
      return {
        bg: dark ? '#141816' : '#fbfcfb',
        text: dark ? '#e2e8e5' : '#2c3330',
        textSub: dark ? '#8fa39a' : '#6b7a73',
        textHalo: dark ? 'rgba(20, 24, 22, 0.85)' : 'rgba(251, 252, 251, 0.9)',
        edgeDefault: dark ? 'rgba(95, 203, 167, 0.16)' : 'rgba(36, 75, 62, 0.14)',
        edgeActive: dark ? 'rgba(95, 203, 167, 0.85)' : 'rgba(36, 75, 62, 0.85)',
        edgeTag: dark ? 'rgba(231, 205, 140, 0.16)' : 'rgba(201, 165, 92, 0.16)',
        nodeArticle: dark ? '#5FCBA7' : '#244b3e',
        nodeArticleHover: dark ? '#7FE0C0' : '#1a372d',
        nodeTag: dark ? '#e7cd8c' : '#c9a55c',
        nodeTagHover: dark ? '#f5dfa8' : '#a8863f',
        nodePulse: dark ? 'rgba(95, 203, 167, 0.35)' : 'rgba(36, 75, 62, 0.22)'
      };
    }

    // 加载数据
    function loadData() {
      fetch('/data/graph-data.json')
        .then(function(res) { return res.json(); })
        .then(function(data) {
          initGraph(data);
        })
        .catch(function(err) {
          console.error('星图数据加载失败:', err);
        });
    }

    // 初始化图谱结构
    function initGraph(data) {
      nodes = (data.nodes || []).map(function(d, i) {
        var angle = (i / data.nodes.length) * 2 * Math.PI;
        var radius = 120 + Math.random() * 260;
        return {
          id: d.id,
          title: d.title,
          type: d.type,
          url: d.url,
          lang: d.lang,
          section: d.section,
          sectionKey: d.sectionKey,
          tags: d.tags || [],
          date: d.date || '',
          description: d.description || '',
          val: d.val || 8,
          x: Math.cos(angle) * radius + (Math.random() - 0.5) * 40,
          y: Math.sin(angle) * radius + (Math.random() - 0.5) * 40,
          vx: 0,
          vy: 0,
          neighbors: new Set(),
          links: []
        };
      });

      nodeMap = {};
      nodes.forEach(function(n) { nodeMap[n.id] = n; });

      links = [];
      (data.links || []).forEach(function(l) {
        var sourceNode = nodeMap[l.source];
        var targetNode = nodeMap[l.target];
        if (sourceNode && targetNode) {
          var linkObj = {
            source: sourceNode,
            target: targetNode,
            type: l.type,
            weight: l.weight || 1
          };
          links.push(linkObj);
          sourceNode.neighbors.add(targetNode);
          targetNode.neighbors.add(sourceNode);
          sourceNode.links.push(linkObj);
          targetNode.links.push(linkObj);
        }
      });

      updateStatsUI(data.stats);
      restartSim();

      // 若有聚焦参数，居中并高亮该节点
      if (focusedNodeId && nodeMap[focusedNodeId]) {
        selectNode(nodeMap[focusedNodeId]);
        centerOnNode(nodeMap[focusedNodeId]);
      }
    }

    function updateStatsUI(stats) {
      var badge = document.getElementById('zen-graph-stats');
      if (badge && stats) {
        badge.textContent = isEn ?
          (stats.articlesCount + ' essays · ' + stats.linksCount + ' links') :
          (stats.articlesCount + ' 篇思考 · ' + stats.linksCount + ' 条思想交织');
      }
    }

    // 简单高效的力学迭代 (Verlet / Spring Repulsion)
    function tickPhysics() {
      if (alpha < alphaMin) return false;

      var kRepulse = 180;
      var kSpring = 0.045;
      var kCenter = 0.015;

      // 1. 节点间斥力 (简化的空间网格/全节点排斥)
      for (var i = 0; i < nodes.length; i++) {
        var n1 = nodes[i];
        if (!isNodeVisible(n1)) continue;

        for (var j = i + 1; j < nodes.length; j++) {
          var n2 = nodes[j];
          if (!isNodeVisible(n2)) continue;

          var dx = n2.x - n1.x;
          var dy = n2.y - n1.y;
          var distSq = dx * dx + dy * dy || 1;
          var dist = Math.sqrt(distSq);

          if (dist < 320) {
            var f = (kRepulse * (n1.val + n2.val)) / (distSq + 30);
            var fx = (dx / dist) * f;
            var fy = (dy / dist) * f;

            n1.vx -= fx;
            n1.vy -= fy;
            n2.vx += fx;
            n2.vy += fy;
          }
        }

        // 向心微引力
        n1.vx -= n1.x * kCenter;
        n1.vy -= n1.y * kCenter;
      }

      // 2. 弹簧引力 (沿连线)
      for (var l = 0; l < links.length; l++) {
        var link = links[l];
        var s = link.source;
        var t = link.target;
        if (!isNodeVisible(s) || !isNodeVisible(t)) continue;

        var ldx = t.x - s.x;
        var ldy = t.y - s.y;
        var lDist = Math.sqrt(ldx * ldx + ldy * ldy) || 1;
        var targetDist = (link.type === 'tag-link' ? 70 : 100);
        var force = (lDist - targetDist) * kSpring * link.weight;

        var sfx = (ldx / lDist) * force;
        var sfy = (ldy / lDist) * force;

        s.vx += sfx;
        s.vy += sfy;
        t.vx -= sfx;
        t.vy -= sfy;
      }

      // 3. 更新位置与阻尼
      var damping = 0.82;
      for (var m = 0; m < nodes.length; m++) {
        var node = nodes[m];
        if (node === dragNode) continue; // 被拖拽的节点固定

        node.vx *= damping;
        node.vy *= damping;
        node.x += node.vx * alpha;
        node.y += node.vy * alpha;
      }

      alpha -= alpha * alphaDecay;
      return true;
    }

    function isNodeVisible(n) {
      if (!showTags && n.type === 'tag') return false;
      if (activeFilter !== 'all') {
        if (activeFilter === 'tag' && n.type !== 'tag') return false;
        if (activeFilter !== 'tag') {
          if (n.type === 'tag') return false;
          if (n.sectionKey !== activeFilter && n.section !== activeFilter) return false;
        }
      }
      return true;
    }

    function isNodeMatchSearch(n) {
      if (!searchQuery) return true;
      var q = searchQuery.toLowerCase();
      if (n.title.toLowerCase().indexOf(q) !== -1) return true;
      if (n.tags && n.tags.some(function(t) { return t.toLowerCase().indexOf(q) !== -1; })) return true;
      return false;
    }

    // 绘制循环
    function draw() {
      var palette = getThemePalette();

      ctx.clearRect(0, 0, width, height);
      ctx.save();
      ctx.translate(transform.x, transform.y);
      ctx.scale(transform.k, transform.k);

      var activeNode = hoveredNode || selectedNode;

      // 1. 绘制连线
      for (var i = 0; i < links.length; i++) {
        var l = links[i];
        var s = l.source;
        var t = l.target;
        if (!isNodeVisible(s) || !isNodeVisible(t)) continue;

        var isConnected = activeNode && (s === activeNode || t === activeNode);
        var hasActive = activeNode !== null;

        if (hasActive && !isConnected) {
          ctx.strokeStyle = palette.edgeDefault;
          ctx.globalAlpha = 0.05;
        } else if (isConnected) {
          ctx.strokeStyle = palette.edgeActive;
          ctx.globalAlpha = 0.9;
        } else {
          ctx.strokeStyle = l.type === 'tag-link' ? palette.edgeTag : palette.edgeDefault;
          ctx.globalAlpha = 0.6;
        }

        ctx.lineWidth = (isConnected ? 1.8 : 0.9) / transform.k;
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(t.x, t.y);
        ctx.stroke();
      }

      ctx.globalAlpha = 1;

      // 2. 绘制节点
      for (var j = 0; j < nodes.length; j++) {
        var n = nodes[j];
        if (!isNodeVisible(n)) continue;

        var isMatch = isNodeMatchSearch(n);
        var isHov = (n === activeNode);
        var isNeighbor = activeNode && activeNode.neighbors.has(n);
        var dim = (activeNode && !isHov && !isNeighbor) || (!isMatch);

        var radius = (n.val || 8);
        var baseColor = n.type === 'tag' ? palette.nodeTag : palette.nodeArticle;
        if (isHov) baseColor = n.type === 'tag' ? palette.nodeTagHover : palette.nodeArticleHover;

        ctx.globalAlpha = dim ? 0.12 : 1;

        // 光晕脉冲
        if (isHov || n === selectedNode || (focusedNodeId && n.id === focusedNodeId)) {
          ctx.beginPath();
          ctx.arc(n.x, n.y, radius + 7 / transform.k, 0, Math.PI * 2);
          ctx.fillStyle = palette.nodePulse;
          ctx.fill();
        }

        // 实体核心
        ctx.beginPath();
        ctx.arc(n.x, n.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = baseColor;
        ctx.fill();

        // 边框微光
        ctx.lineWidth = 1.2 / transform.k;
        ctx.strokeStyle = isDarkMode() ? 'rgba(255,255,255,0.4)' : 'rgba(0,0,0,0.15)';
        ctx.stroke();

        // 绘制文字标签 (在缩放合适或高亮时显示)
        var shouldShowLabel = showLabels && (transform.k > 0.85 || isHov || isNeighbor || isMatch || n.val > 14);
        if (shouldShowLabel && !dim) {
          var fontSize = Math.max(10, Math.min(14, 12 / transform.k));
          ctx.font = (n.type === 'tag' ? 'italic ' : '') + (isHov ? '600 ' : '500 ') + fontSize + 'px sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';

          var labelY = n.y + radius + 4 / transform.k;
          var titleStr = n.title;
          if (titleStr.length > 14 && !isHov) titleStr = titleStr.substring(0, 13) + '…';

          // 光晕文字阴影保证可读性
          ctx.fillStyle = palette.textHalo;
          for (var dx = -1; dx <= 1; dx++) {
            for (var dy = -1; dy <= 1; dy++) {
              ctx.fillText(titleStr, n.x + dx, labelY + dy);
            }
          }
          ctx.fillStyle = palette.text;
          ctx.fillText(titleStr, n.x, labelY);
        }
      }

      ctx.restore();
    }

    function loop() {
      var running = tickPhysics();
      draw();
      if (running || isDragging) {
        animFrameId = requestAnimationFrame(loop);
      } else {
        cancelAnimationFrame(animFrameId);
        animFrameId = null;
      }
    }

    function restartSim() {
      alpha = Math.max(alpha, 0.4);
      if (!animFrameId) {
        animFrameId = requestAnimationFrame(loop);
      }
    }

    // 坐标换算 (屏幕坐标 -> 图谱坐标)
    function screenToWorld(sx, sy) {
      return {
        x: (sx - transform.x) / transform.k,
        y: (sy - transform.y) / transform.k
      };
    }

    function findNodeAt(sx, sy) {
      var world = screenToWorld(sx, sy);
      for (var i = nodes.length - 1; i >= 0; i--) {
        var n = nodes[i];
        if (!isNodeVisible(n)) continue;
        var dx = world.x - n.x;
        var dy = world.y - n.y;
        var r = (n.val || 8) + 4 / transform.k;
        if (dx * dx + dy * dy <= r * r) {
          return n;
        }
      }
      return null;
    }

    // 聚焦某一节点并平滑移至中心
    function centerOnNode(node) {
      transform.k = 1.35;
      transform.x = width / 2 - node.x * transform.k;
      transform.y = height / 2 - node.y * transform.k;
      restartSim();
    }

    // 打开节点详情侧边栏抽屉
    function selectNode(node) {
      selectedNode = node;
      var drawer = document.getElementById('zen-graph-drawer');
      if (!drawer) return;

      var titleEl = document.getElementById('zen-drawer-title');
      var secEl = document.getElementById('zen-drawer-sec');
      var dateEl = document.getElementById('zen-drawer-date');
      var descEl = document.getElementById('zen-drawer-desc');
      var linkBtn = document.getElementById('zen-drawer-link');
      var neighborsList = document.getElementById('zen-drawer-neighbors');

      if (titleEl) titleEl.textContent = node.title;
      if (secEl) secEl.textContent = node.section || (node.type === 'tag' ? (isEn ? 'Tag' : '标签星宿') : '');
      if (dateEl) dateEl.textContent = node.date || '';
      if (descEl) descEl.textContent = node.description || (isEn ? 'Exploring the interconnected thoughts across World Corner.' : '点击下方按钮进入篇章，探索思想的完整脉络。');

      if (linkBtn) {
        if (node.type === 'tag') {
          linkBtn.href = (isEn ? '/en/search/?q=' : '/search/?q=') + encodeURIComponent(node.name || node.title);
          linkBtn.textContent = isEn ? 'Search all with this tag →' : '搜索该标签全部文章 →';
        } else {
          linkBtn.href = node.url;
          linkBtn.textContent = isEn ? 'Read full essay →' : '进入阅读全文 →';
        }
        linkBtn.style.display = 'inline-flex';
      }

      if (neighborsList) {
        var nbHtml = '';
        node.neighbors.forEach(function(nb) {
          if (!isNodeVisible(nb)) return;
          nbHtml += '<li class="zen-drawer-nb-item" data-id="' + nb.id + '">' +
            '<span class="zen-drawer-nb-type">' + (nb.type === 'tag' ? '🏷️' : '📄') + '</span>' +
            '<span class="zen-drawer-nb-title">' + nb.title + '</span>' +
          '</li>';
        });
        neighborsList.innerHTML = nbHtml || ('<li style="color:var(--zen-sub)">' + (isEn ? 'No direct connections' : '暂无近邻关联') + '</li>');

        // 抽屉内关联项点击快速跳转并聚焦
        neighborsList.querySelectorAll('.zen-drawer-nb-item').forEach(function(item) {
          item.addEventListener('click', function() {
            var targetId = this.getAttribute('data-id');
            if (nodeMap[targetId]) {
              selectNode(nodeMap[targetId]);
              centerOnNode(nodeMap[targetId]);
            }
          });
        });
      }

      drawer.classList.add('open');
      restartSim();
    }

    // 交互监听 (鼠标 / 滚轮 / 触摸)
    canvas.addEventListener('mousedown', function(e) {
      var rect = canvas.getBoundingClientRect();
      var sx = e.clientX - rect.left;
      var sy = e.clientY - rect.top;
      var hit = findNodeAt(sx, sy);

      if (hit) {
        isDragging = true;
        dragNode = hit;
        hit.vx = 0;
        hit.vy = 0;
      } else {
        isDragging = true;
        dragNode = null;
        dragStart.x = e.clientX - transform.x;
        dragStart.y = e.clientY - transform.y;
      }
    });

    window.addEventListener('mousemove', function(e) {
      var rect = canvas.getBoundingClientRect();
      var sx = e.clientX - rect.left;
      var sy = e.clientY - rect.top;

      if (isDragging) {
        if (dragNode) {
          var world = screenToWorld(sx, sy);
          dragNode.x = world.x;
          dragNode.y = world.y;
          restartSim();
        } else {
          transform.x = e.clientX - dragStart.x;
          transform.y = e.clientY - dragStart.y;
          restartSim();
        }
      } else {
        var hit = findNodeAt(sx, sy);
        if (hit !== hoveredNode) {
          hoveredNode = hit;
          canvas.style.cursor = hit ? 'pointer' : 'default';
          restartSim();
        }
      }
    });

    window.addEventListener('mouseup', function(e) {
      if (isDragging && dragNode) {
        dragNode = null;
      }
      isDragging = false;
    });

    canvas.addEventListener('click', function(e) {
      var rect = canvas.getBoundingClientRect();
      var sx = e.clientX - rect.left;
      var sy = e.clientY - rect.top;
      var hit = findNodeAt(sx, sy);
      if (hit) {
        selectNode(hit);
      }
    });

    // 滚轮缩放
    canvas.addEventListener('wheel', function(e) {
      e.preventDefault();
      var rect = canvas.getBoundingClientRect();
      var sx = e.clientX - rect.left;
      var sy = e.clientY - rect.top;

      var factor = e.deltaY < 0 ? 1.12 : 0.89;
      var newK = Math.max(0.3, Math.min(3.5, transform.k * factor));

      // 缩放中心对齐鼠标
      transform.x = sx - (sx - transform.x) * (newK / transform.k);
      transform.y = sy - (sy - transform.y) * (newK / transform.k);
      transform.k = newK;
      restartSim();
    }, { passive: false });

    // 控件按钮
    var btnZoomIn = document.getElementById('zen-graph-zoomin');
    var btnZoomOut = document.getElementById('zen-graph-zoomout');
    var btnReset = document.getElementById('zen-graph-reset');
    var btnToggleTags = document.getElementById('zen-graph-toggletags');
    var searchInput = document.getElementById('zen-graph-search');
    var drawerClose = document.getElementById('zen-drawer-close');

    if (btnZoomIn) {
      btnZoomIn.addEventListener('click', function() {
        transform.k = Math.min(3.5, transform.k * 1.25);
        restartSim();
      });
    }
    if (btnZoomOut) {
      btnZoomOut.addEventListener('click', function() {
        transform.k = Math.max(0.3, transform.k * 0.8);
        restartSim();
      });
    }
    if (btnReset) {
      btnReset.addEventListener('click', function() {
        transform = { x: width / 2, y: height / 2, k: 1 };
        selectedNode = null;
        focusedNodeId = null;
        var drawer = document.getElementById('zen-graph-drawer');
        if (drawer) drawer.classList.remove('open');
        restartSim();
      });
    }
    if (btnToggleTags) {
      btnToggleTags.addEventListener('click', function() {
        showTags = !showTags;
        this.classList.toggle('active', showTags);
        restartSim();
      });
    }
    if (searchInput) {
      searchInput.addEventListener('input', function() {
        searchQuery = this.value.trim();
        restartSim();
      });
    }
    if (drawerClose) {
      drawerClose.addEventListener('click', function() {
        var drawer = document.getElementById('zen-graph-drawer');
        if (drawer) drawer.classList.remove('open');
        selectedNode = null;
        restartSim();
      });
    }

    // 栏目药丸筛选
    document.querySelectorAll('.zen-filter-chip').forEach(function(chip) {
      chip.addEventListener('click', function() {
        document.querySelectorAll('.zen-filter-chip').forEach(function(c) { c.classList.remove('active'); });
        this.classList.add('active');
        activeFilter = this.getAttribute('data-filter') || 'all';
        restartSim();
      });
    });

    // 窗口尺寸自适应
    window.addEventListener('resize', resize);
    resize();
    loadData();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initZenGraph);
  } else {
    initZenGraph();
  }
})();
