# 访问统计读取接口（Worker 端）

看板页 `content/stats/` 读的是这个接口：

```text
GET https://api.worldcorner.xyz/community/api/pv/stats?days=30
Authorization: Bearer <STATS_TOKEN>
```

## 部署

代码在 `F:\xiaochenxukaifa\worldcorner-api`，不在 GitHub 上。
部署前先设置口令（只存在 Worker 密钥里，不要写进代码）：

```bash
cd F:\xiaochenxukaifa\worldcorner-api
npx wrangler secret put STATS_TOKEN
npx wrangler deploy
```

## 接口代码

加到 `src/index.js` 的路由里，和现有的 `POST /community/api/pv` 放在一起。
下面假设访问记录存在 D1 表 `pageviews`，字段和埋点上报的一致：

```text
pageviews(ts INTEGER, path TEXT, src TEXT, campaign TEXT,
          ref_host TEXT, lang TEXT, device TEXT, event TEXT, sid TEXT)
```

如果上报接口用的表名或字段不一样，只改下面 `PV_TABLE` 这一处，
看板页不用动。

```javascript
const PV_TABLE = 'pageviews'; // 上报接口实际用的表名

// GET /community/api/pv/stats?days=30
async function handlePvStats(request, env) {
  const token = (request.headers.get('Authorization') || '').replace(/^Bearer\s+/i, '');
  if (!env.STATS_TOKEN || token !== env.STATS_TOKEN) {
    return json({ error: 'unauthorized' }, 401);
  }
  const days = Math.min(90, Math.max(1, parseInt(new URL(request.url).searchParams.get('days') || '30', 10)));
  const since = Date.now() - days * 86400000;
  const todayStart = new Date(); todayStart.setHours(0, 0, 0, 0);

  const q = async (sql, args) => (await env.DB.prepare(sql).bind(...args).all()).results || [];
  const one = async (sql, args) => (await env.DB.prepare(sql).bind(...args).first()) || {};

  const total = await one(`SELECT COUNT(*) c FROM ${PV_TABLE} WHERE event = 'pv' AND ts >= ?`, [since]);
  const today = await one(`SELECT COUNT(*) c FROM ${PV_TABLE} WHERE event = 'pv' AND ts >= ?`, [todayStart.getTime()]);
  const uv = await one(`SELECT COUNT(DISTINCT sid) c FROM ${PV_TABLE} WHERE event = 'pv' AND ts >= ?`, [since]);
  const audio = await one(`SELECT COUNT(*) c FROM ${PV_TABLE} WHERE event = 'audio_play' AND ts >= ?`, [since]);
  const inner = await one(`SELECT COUNT(*) c FROM ${PV_TABLE} WHERE event = 'enter_inner' AND ts >= ?`, [since]);
  const byDay = await q(`SELECT date(ts / 1000, 'unixepoch', '+8 hours') day, COUNT(*) pv, COUNT(DISTINCT sid) uv FROM ${PV_TABLE} WHERE event = 'pv' AND ts >= ? GROUP BY day ORDER BY day`, [since]);
  const bySrc = await q(`SELECT COALESCE(NULLIF(src, ''), '(直接打开)') src, COUNT(*) pv, COUNT(DISTINCT sid) uv FROM ${PV_TABLE} WHERE event = 'pv' AND ts >= ? GROUP BY src ORDER BY pv DESC LIMIT 10`, [since]);
  const byPage = await q(`SELECT path, COUNT(*) pv, COUNT(DISTINCT sid) uv FROM ${PV_TABLE} WHERE event = 'pv' AND ts >= ? GROUP BY path ORDER BY pv DESC LIMIT 10`, [since]);
  const byDevice = await q(`SELECT device, COUNT(*) pv FROM ${PV_TABLE} WHERE event = 'pv' AND ts >= ? GROUP BY device ORDER BY pv DESC`, [since]);
  const byLang = await q(`SELECT lang, COUNT(*) pv FROM ${PV_TABLE} WHERE event = 'pv' AND ts >= ? GROUP BY lang ORDER BY pv DESC`, [since]);

  return json({
    days,
    total_pv: total.c || 0,
    today_pv: today.c || 0,
    unique_visitors: uv.c || 0,
    audio_plays: audio.c || 0,
    enter_inner: inner.c || 0,
    by_day: byDay, by_src: bySrc, by_page: byPage, by_device: byDevice, by_lang: byLang,
  });
}
```

路由里加一行（按现有 `json()` 辅助函数的写法）：

```javascript
if (url.pathname === '/community/api/pv/stats' && request.method === 'GET') {
  return handlePvStats(request, env);
}
```

## 注意

- `ts` 按毫秒存；如果上报时存的是秒，把 `ts >= ?` 的 `since` 除以 1000，
  `date(ts / 1000, ...)` 改成 `date(ts, ...)`。
- 日期按北京时间（+8 小时）分组，和埋点口径一致。
- 看板页在 `/stats/`，首页不展示；没有口令打不开数据。
