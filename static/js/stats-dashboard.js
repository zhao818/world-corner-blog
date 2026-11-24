(() => {
  const api = 'https://api.worldcorner.xyz/community/api/pv/stats';
  const form = document.getElementById('stats-auth');
  const field = document.getElementById('stats-token');
  const status = document.getElementById('stats-status');
  const dashboard = document.getElementById('stats-dashboard');
  const results = document.getElementById('stats-results');
  const ranges = dashboard.querySelectorAll('[data-days]');
  let token = '';
  let request;

  function element(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value != null) node.textContent = value;
    return node;
  }

  function number(value) {
    return Number(value ?? 0).toLocaleString('zh-CN');
  }

  function table(headers, rows) {
    if (!rows.length) return element('p', 'stats-meta', '这个时段暂无记录。');
    const grid = element('table');
    const header = grid.createTHead().insertRow();
    for (const label of headers) {
      const cell = element('th', '', label);
      cell.scope = 'col';
      header.append(cell);
    }
    const body = grid.createTBody();
    for (const row of rows) {
      const line = body.insertRow();
      for (const value of row) line.insertCell().textContent = value;
    }
    return grid;
  }

  function section(title, content) {
    const box = element('section', 'stats-box');
    box.append(element('h2', '', title), content);
    return box;
  }

  function render(data) {
    const byDay = new Map(data.by_day.map(row => [row.day, row]));
    const events = new Map(data.by_event.map(row => [row.event, row.cnt]));
    const totals = data.totals;
    const metrics = element('dl', 'stats-cards');
    for (const [label, value] of [
      ['页面浏览', totals.pv], ['独立会话', totals.uv],
      ['今日浏览', byDay.get(data.today)?.pv], ['进入静室', events.get('enter_inner')],
      ['播放音频', events.get('audio_play')], ['快手归因浏览', totals.ks_pv]
    ]) {
      const card = element('div', 'stats-card');
      card.append(element('dt', '', label), element('dd', '', number(value)));
      metrics.append(card);
    }

    const range = element('div', 'stats-range');
    range.append(
      element('span', '', data.sinceDay + ' 至 ' + data.today + ' · 北京时间'),
      element('span', '', byDay.size + ' / ' + data.days + ' 天有记录')
    );
    const trend = element('div');
    const plot = element('div', 'stats-plot');
    plot.style.setProperty('--days', data.days);
    plot.setAttribute('aria-hidden', 'true');
    const peak = Math.max(1, ...data.by_day.map(row => Number(row.pv) || 0));
    const firstDay = Date.parse(data.sinceDay + 'T00:00:00Z');
    const dailyRows = [];
    for (let i = 0; i < data.days; i += 1) {
      const date = new Date(firstDay + i * 86400000).toISOString().slice(0, 10);
      const row = byDay.get(date);
      const slot = element('div', 'stats-slot');
      const bar = element('div', row ? 'stats-bar' : 'stats-dot');
      slot.title = date + (row ? ' · 浏览 ' + number(row.pv) : ' · 暂无记录');
      if (row) {
        bar.style.setProperty('--height', 100 * (Number(row.pv) || 0) / peak + '%');
        if (row.pv) bar.append(element('span', '', number(row.pv)));
      }
      slot.append(bar);
      plot.append(slot);
      dailyRows.push([date, row ? number(row.pv) : '暂无记录', row ? number(row.uv) : '—']);
    }
    const dates = element('div', 'stats-dates');
    dates.append(element('span', '', data.sinceDay.slice(5)), element('span', '', data.today.slice(5)));
    const detail = element('details');
    detail.append(element('summary', '', '查看按日数据'), table(['日期', '浏览', '会话'], dailyRows));
    trend.append(element('p', 'stats-meta', '按自然日显示页面浏览，灰点表示当日暂无记录。'), plot, dates, detail);

    const grid = element('div', 'stats-grid');
    const devices = { mobile: '手机', desktop: '桌面', tablet: '平板' };
    const languages = { zh: '中文', en: '英文' };
    grid.append(
      section('热门页面', table(['页面', '浏览', '会话'], data.top_paths.map(row => [row.path, number(row.pv), number(row.uv)]))),
      section('访问来源', table(['渠道', '来源域名', '浏览'], data.by_source.map(row => [row.src || (row.ref_host ? '未标记' : '直接访问'), row.ref_host || '—', number(row.hits)]))),
      section('设备', table(['设备', '浏览'], data.by_device.map(row => [devices[row.device] || '未知', number(row.cnt)]))),
      section('语言', table(['语言', '浏览'], data.by_language.map(row => [languages[row.lang] || row.lang || '未知', number(row.cnt)])))
    );
    results.replaceChildren(range, metrics, section('访问趋势', trend), grid,
      element('p', 'stats-meta', '独立会话按会话标识去重。快手归因依赖来源标记或来源域名。'));
  }

  function lock(message = '') {
    request?.abort();
    token = '';
    field.value = '';
    results.replaceChildren();
    dashboard.hidden = true;
    form.hidden = false;
    status.textContent = message;
    field.focus();
  }

  async function load(days) {
    request?.abort();
    const pending = new AbortController();
    request = pending;
    results.replaceChildren();
    status.textContent = '正在读取统计…';
    try {
      const response = await fetch(api + '?days=' + days, {
        headers: { Authorization: 'Bearer ' + token },
        credentials: 'omit',
        cache: 'no-store',
        signal: pending.signal
      });
      if (pending.signal.aborted) return;
      if (response.status === 401) {
        lock('口令无效，或查数口令尚未配置。');
        return;
      }
      if (response.status === 404) throw new Error('统计接口尚未上线。');
      if (!response.ok) throw new Error('统计接口暂时无法读取，请稍后重试。');
      const data = await response.json();
      if (pending.signal.aborted) return;
      render(data);
      form.hidden = true;
      dashboard.hidden = false;
      for (const button of ranges) button.setAttribute('aria-pressed', String(Number(button.dataset.days) === days));
      status.textContent = '';
    } catch (error) {
      if (!pending.signal.aborted) status.textContent = error instanceof TypeError
        ? '连接统计接口失败，请重试。' : error.message;
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    token = field.value.trim();
    field.value = '';
    if (token) load(7);
  });
  for (const button of ranges) button.addEventListener('click', () => load(Number(button.dataset.days)));
  document.getElementById('stats-lock').addEventListener('click', () => lock());
})();
