"""
内容发布可视化仪表盘 + 内容索引系统
====================================
用法: python content_dashboard.py serve | list | add | mark | pending | summary | sync
HTML 模板从 dashboard_template.html 读取
"""
import sys, os, json, re, argparse, textwrap, webbrowser, threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(SCRIPT_DIR, "content_registry.json")
PUBLISH_LOG_PATH = os.path.expanduser("~/.claude/publish-log.json")
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "dashboard_template.html")

DEFAULT_PLATFORMS = ["wechat","juejin","zhihu","bilibili","douyin","kuaishou","channels","xiaohongshu","goofish","jike","tencent_cloud"]
PLATFORM_LABELS = {"wechat":"公众号","juejin":"掘金","zhihu":"知乎","bilibili":"B站","douyin":"抖音","kuaishou":"快手","channels":"视频号","xiaohongshu":"小红书","goofish":"闲鱼","jike":"即刻","tencent_cloud":"腾讯云"}
# 平台分类: text=直接发文, video=需视频
TEXT_PLATFORMS = ["wechat","juejin","zhihu","jike","tencent_cloud","goofish"]
VIDEO_PLATFORMS = ["douyin","kuaishou","channels","bilibili","xiaohongshu"]

STATUS_LABELS = {"not_planned":"不发布","pending":"待发","published":"已发","failed":"失败","skipped":"跳过"}
STATUS_ICONS = {"not_planned":"⬜","pending":"⏳","published":"✅","failed":"❌","skipped":"⊘"}

def _load_dashboard_html():
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH,"r",encoding="utf-8") as f:
            return f.read()
    return "<html><body><h1>Dashboard template not found</h1></body></html>"

VIDEO_STATS_PATH = os.path.expanduser("~/.claude/video-stats-summary.json")

def _get_video_stats(piece_id=None):
    """Read video stats from collected data, cross-reference with registry."""
    reg = RegistryManager()
    data = reg.load()

    # Load collected stats if available
    collected = {}
    if os.path.exists(VIDEO_STATS_PATH):
        try:
            with open(VIDEO_STATS_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for r in raw.get("results", []):
                key = f"{r.get('piece_id','')}:{r.get('platform','')}"
                collected[key] = r.get("result", {})
        except Exception:
            pass

    # Build per-piece video stats
    pieces_stats = []
    for piece in data["pieces"]:
        if piece.get("type") != "video":
            continue
        has_published = any(
            piece.get("platforms", {}).get(p, {}).get("status") == "published"
            for p in VIDEO_PLATFORMS
        )
        if not has_published:
            continue
        if piece_id and piece["id"] != piece_id[0]:
            continue

        platforms_data = {}
        for plat in VIDEO_PLATFORMS:
            status = piece.get("platforms", {}).get(plat, {}).get("status")
            if status == "published":
                key = f"{piece['id']}:{plat}"
                platforms_data[plat] = {
                    "status": status,
                    "url": piece["platforms"][plat].get("url", ""),
                    "stats": collected.get(key, {}),
                }

        pieces_stats.append({
            "id": piece["id"],
            "title": piece["title"],
            "hook_type": piece.get("hook_type", ""),
            "variant": piece.get("video_variant", ""),
            "file_path": piece.get("file_path", ""),
            "platforms": platforms_data,
        })

    # Aggregate summary
    total_views = 0
    total_likes = 0
    platform_counts = {}
    for ps in pieces_stats:
        for plat, pdata in ps["platforms"].items():
            s = pdata.get("stats", {})
            if s.get("success"):
                total_views += s.get("views", 0) or 0
                total_likes += s.get("likes", 0) or 0
                platform_counts[plat] = platform_counts.get(plat, 0) + 1

    video_stats_file = os.path.exists(VIDEO_STATS_PATH)
    raw_data = raw if video_stats_file else {}

    return {
        "updated_at": raw_data.get("collected_at", "") if collected else "",
        "total_videos": len(pieces_stats),
        "total_views": total_views,
        "total_likes": total_likes,
        "platforms_collected": platform_counts,
        "pieces": pieces_stats,
    }

class RegistryManager:
    def __init__(self, path=REGISTRY_PATH):
        self.path = path
    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path,"r",encoding="utf-8") as f:
                    data = json.load(f)
                data.setdefault("platforms",list(DEFAULT_PLATFORMS))
                data.setdefault("pieces",[])
                data.setdefault("version",1)
                return data
            except: pass
        return {"version":1,"updated_at":"","platforms":list(DEFAULT_PLATFORMS),"pieces":[]}
    def save(self, data):
        data["updated_at"] = datetime.now().isoformat()
        tmp = self.path + ".tmp"
        with open(tmp,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
        os.replace(tmp, self.path)
    def get_piece(self, piece_id):
        for p in self.load()["pieces"]:
            if p["id"] == piece_id: return p
        return None
    def find_by_title(self, title, prefix_len=20):
        key = title.strip().lower()[:prefix_len]
        for p in self.load()["pieces"]:
            if p["title"].strip().lower()[:prefix_len] == key: return p
        return None
    def list_pieces(self, filters=None):
        data = self.load()
        pieces = data["pieces"]
        if not filters: return pieces
        if filters.get("pending_only"):
            pieces = [p for p in pieces if any(s.get("status")=="pending" for s in p.get("platforms",{}).values())]
        if filters.get("platform"):
            pieces = [p for p in pieces if filters["platform"] in p.get("platforms",{})]
        if filters.get("series"):
            pieces = [p for p in pieces if p.get("series")==filters["series"]]
        if filters.get("type"):
            pieces = [p for p in pieces if p.get("type")==filters["type"]]
        if filters.get("status"):
            st = filters["status"]
            pieces = [p for p in pieces if any(s.get("status")==st for s in p.get("platforms",{}).values())]
        return pieces
    def get_pending(self):
        data = self.load()
        pending = []
        for p in data["pieces"]:
            for plat in data["platforms"]:
                if p.get("platforms",{}).get(plat,{}).get("status") == "pending":
                    pending.append((p, plat))
        return pending
    def add_piece(self, piece):
        data = self.load()
        if not piece.get("id"):
            piece["id"] = self._title_to_id(piece.get("title","untitled"))
        base_id = piece["id"]
        counter = 1
        while self.get_piece(piece["id"]):
            piece["id"] = f"{base_id}-{counter}"
            counter += 1
        platforms = {}
        for plat in data["platforms"]:
            platforms[plat] = {"status":"not_planned","url":"","date":None}
        piece["platforms"] = platforms
        piece.setdefault("type","article")
        piece.setdefault("digest","")
        piece.setdefault("file_path","")
        piece.setdefault("created_date",datetime.now().strftime("%Y-%m-%d"))
        piece.setdefault("topics",[])
        piece.setdefault("series","")
        piece.setdefault("video_path","")
        data["pieces"].append(piece)
        self.save(data)
        return piece["id"]
    def update_platform(self, piece_id, platform, status, url="", date=""):
        data = self.load()
        for p in data["pieces"]:
            if p["id"] == piece_id:
                if platform not in p["platforms"]:
                    p["platforms"][platform] = {"status":"not_planned","url":"","date":None}
                p["platforms"][platform]["status"] = status
                if url: p["platforms"][platform]["url"] = url
                p["platforms"][platform]["date"] = date or datetime.now().strftime("%Y-%m-%d")
                self.save(data)
                return True
        return False
    def update_piece(self, piece_id, updates):
        data = self.load()
        for p in data["pieces"]:
            if p["id"] == piece_id:
                updates.pop("platforms",None)
                p.update(updates)
                self.save(data)
                return True
        return False
    def sync_from_publish_log(self, log_path=PUBLISH_LOG_PATH):
        if not os.path.exists(log_path): return 0
        try:
            with open(log_path,"r",encoding="utf-8") as f:
                log_entries = json.load(f)
        except: return 0
        synced = 0
        for entry in log_entries:
            title = entry.get("title","")
            platform = entry.get("platform","")
            if not title or not platform: continue
            piece = self.find_by_title(title)
            if piece:
                if piece["platforms"].get(platform,{}).get("status") != "published":
                    self.update_platform(piece["id"], platform, "published",
                        url=entry.get("url",""), date=(entry.get("date",""))[:10])
                    synced += 1
            else:
                new_piece = {
                    "id": self._title_to_id(title),
                    "title": title,
                    "digest": "",
                    "type": entry.get("type","article"),
                    "file_path": entry.get("source",""),
                    "created_date": (entry.get("date",""))[:10] or datetime.now().strftime("%Y-%m-%d"),
                    "topics": [],
                    "series": entry.get("series",""),
                }
                self.add_piece(new_piece)
                self.update_platform(new_piece["id"], platform, "published",
                    url=entry.get("url",""), date=(entry.get("date",""))[:10])
                synced += 1
        return synced
    def get_summary(self):
        data = self.load()
        pieces = data["pieces"]
        platforms = data["platforms"]
        lines = [f"=== Content Registry Summary ({datetime.now().strftime('%Y-%m-%d')}) ===",
                 f"{len(pieces)} pieces tracked across {len(platforms)} platforms", ""]
        for i, p in enumerate(pieces, 1):
            ptype = p.get("type","article")
            icon = "📹" if ptype == "video" else "📝"
            series = f", {p['series']}" if p.get("series") else ""
            lines.append(f"[{i}] {icon} {p['title']} ({ptype}{series})")
            lines.append(f"    file: {p.get('file_path', 'N/A')}")
            vpath = p.get("video_path","")
            if vpath: lines.append(f"    🎬 video: {vpath}")
            published, pending, failed, skipped, not_planned = [], [], [], [], []
            for plat in platforms:
                info = p.get("platforms",{}).get(plat,{"status":"not_planned"})
                status = info.get("status","not_planned")
                {"published":published,"pending":pending,"failed":failed,"skipped":skipped}.get(status,not_planned).append(plat)
            if published: lines.append(f"    ✅ {', '.join(published)}")
            if pending: lines.append(f"    ⏳ {', '.join(pending)}")
            if failed: lines.append(f"    ❌ {', '.join(failed)}")
            if skipped: lines.append(f"    ⊘ {', '.join(skipped)}")
            if not_planned:
                n = len(not_planned)
                lines.append(f"    ⬜ {', '.join(not_planned[:3])}{'... (+'+str(n-3)+')' if n>3 else ''}")
            # Smart video detection
            pending_v = [pl for pl in platforms if p.get("platforms",{}).get(pl,{}).get("status")=="pending" and pl in VIDEO_PLATFORMS]
            published_v = [pl for pl in platforms if p.get("platforms",{}).get(pl,{}).get("status")=="published" and pl in VIDEO_PLATFORMS]
            if pending_v:
                has_video = bool(vpath or published_v)
                if has_video:
                    lines.append(f"    🎬 视频就绪 | 待分发: {', '.join(pending_v)}")
                else:
                    lines.append(f"    🎬 需生成视频 | 待发: {', '.join(pending_v)}")
            lines.append("")
        all_pending = self.get_pending()
        if all_pending:
            text_pending = [(p,pl) for p,pl in all_pending if pl in TEXT_PLATFORMS]
            video_pending = [(p,pl) for p,pl in all_pending if pl in VIDEO_PLATFORMS]
            lines.append(f"=== PENDING ({len(all_pending)} items) ===")
            if text_pending:
                lines.append(f"  📝 图文直发 ({len(text_pending)}):")
                for i,(piece,plat) in enumerate(text_pending,1):
                    label = PLATFORM_LABELS.get(plat,plat)
                    lines.append(f"     {i}. {piece['title']} → {label}")
            if video_pending:
                lines.append(f"  📹 视频平台 ({len(video_pending)}):")
                for i,(piece,plat) in enumerate(video_pending,1):
                    label = PLATFORM_LABELS.get(plat,plat)
                    vp = piece.get("video_path","")
                    has_v = bool(vp or any(
                        piece.get("platforms",{}).get(p,{}).get("status")=="published"
                        for p in VIDEO_PLATFORMS
                    ))
                    tag = "视频就绪" if has_v else "🎬需生成视频"
                    lines.append(f"     {i}. {piece['title']} → {label} [{tag}]")
        else:
            lines.append("=== PENDING: None ===")
        return "\n".join(lines)
    @staticmethod
    def _title_to_id(title):
        slug = re.sub(r'[^\w\s-]','',title.strip().lower())
        slug = re.sub(r'[-\s]+','-',slug)
        return slug[:50] if slug else "untitled"

_registry = None
def _get_registry():
    global _registry
    if _registry is None: _registry = RegistryManager()
    return _registry

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass
    def _send_json(self, data, status=200):
        body = json.dumps(data,ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",len(body))
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()
        self.wfile.write(body)
    def _send_html(self, html, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",len(body))
        self.end_headers()
        self.wfile.write(body)
    def _send_text(self, text, status=200):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","text/plain; charset=utf-8")
        self.send_header("Content-Length",len(body))
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()
        self.wfile.write(body)
    def _send_error(self, msg, status=400):
        self._send_json({"error":msg}, status)
    def _read_body(self):
        length = int(self.headers.get("Content-Length",0))
        if length == 0: return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))
    def _parse_path(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        parts = [unquote(p) for p in path.split("/") if p]
        return parts, parse_qs(parsed.query)
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,PATCH,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()
    def do_GET(self):
        parts, query = self._parse_path()
        reg = _get_registry()
        if not parts:
            self._send_html(_load_dashboard_html()); return
        if parts == ["api","summary"]:
            self._send_text(reg.get_summary()); return
        if parts == ["api","pending"]:
            pending = reg.get_pending()
            self._send_json([{"piece":p[0],"platform":p[1]} for p in pending]); return
        if parts == ["api","video","stats"]:
            self._send_json(_get_video_stats(query.get("piece_id"))); return
        if parts == ["api","platforms"]:
            data = reg.load()
            self._send_json([{"name":p,"label":PLATFORM_LABELS.get(p,p)} for p in data["platforms"]]); return
        if parts == ["api","registry"]:
            filters = {}
            if query.get("pending_only"): filters["pending_only"] = True
            if query.get("status"): filters["status"] = query["status"][0]
            pieces = reg.list_pieces(filters if filters else None)
            self._send_json({"platforms":reg.load()["platforms"],"pieces":pieces}); return
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "registry":
            piece = reg.get_piece(parts[2])
            if piece: self._send_json(piece)
            else: self._send_error("Piece not found",404)
            return
        self._send_error("Not found",404)
    def do_POST(self):
        parts, _ = self._parse_path()
        reg = _get_registry()
        if parts == ["api","registry"]:
            body = self._read_body()
            if not body or "title" not in body:
                self._send_error("Missing 'title' field",400); return
            piece_id = reg.add_piece(body)
            self._send_json(reg.get_piece(piece_id),201); return
        if parts == ["api","sync"]:
            count = reg.sync_from_publish_log()
            self._send_json({"synced":count}); return
        self._send_error("Not found",404)
    def do_PATCH(self):
        parts, _ = self._parse_path()
        reg = _get_registry()
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "registry":
            piece_id, platform = parts[2], parts[3]
            body = self._read_body()
            status = body.get("status","published")
            if status not in STATUS_LABELS:
                self._send_error(f"Invalid status: {status}",400); return
            if reg.update_platform(piece_id, platform, status, url=body.get("url",""), date=body.get("date","")):
                self._send_json(reg.get_piece(piece_id))
            else:
                self._send_error(f"Piece '{piece_id}' not found",404)
            return
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "registry":
            piece_id = parts[2]
            body = self._read_body()
            if reg.update_piece(piece_id, body):
                self._send_json(reg.get_piece(piece_id))
            else:
                self._send_error(f"Piece '{piece_id}' not found",404)
            return
        self._send_error("Not found",404)

def cmd_serve(port=5000):
    server = HTTPServer(("127.0.0.1", port), DashboardHandler)
    url = f"http://localhost:{port}"
    print(f"\n🔷 世界一隅 · 发布仪表盘\n   {url}\n   按 Ctrl+C 停止\n")
    # 自动打开浏览器
    def _open_browser():
        import time; time.sleep(0.8)
        webbrowser.open(url)
    threading.Thread(target=_open_browser, daemon=True).start()
    try: server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
        server.shutdown()

def cmd_list(pending_only=False):
    reg = RegistryManager()
    pieces = reg.list_pieces({"pending_only":True} if pending_only else None)
    if not pieces:
        print("📭 暂无内容" if not pending_only else "✅ 无待发布内容"); return
    data = reg.load()
    print(f"\n{'='*70}\n  {'待发布' if pending_only else '全部'}内容 ({len(pieces)} 篇)\n{'='*70}")
    for p in pieces:
        icon = "📹" if p.get("type")=="video" else "📝"
        series = f"[{p['series']}]" if p.get("series") else ""
        print(f"\n  {icon} {p['title']} {series}\n     ID: {p['id']}")
        if p.get("file_path"): print(f"     文件: {p['file_path']}")
        for plat in data["platforms"]:
            info = p.get("platforms",{}).get(plat,{})
            status = info.get("status","not_planned")
            if pending_only and status != "pending": continue
            label = PLATFORM_LABELS.get(plat,plat)
            url = info.get("url","")
            extra = f" → {url}" if url else ""
            print(f"     {STATUS_ICONS.get(status,'?')} {label}{extra}")
    pending_count = sum(1 for p in pieces for s in p.get("platforms",{}).values() if s.get("status")=="pending")
    if pending_count: print(f"\n  ⏳ 共 {pending_count} 项待发布")

def cmd_add(filepath):
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}"); return
    title = os.path.basename(filepath).replace(".md","")
    digest = ""; series = ""
    with open(filepath,"r",encoding="utf-8") as f:
        content = f.read()
    if content.startswith("---"):
        parts = content.split("---",2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                line = line.strip()
                if line.startswith("title:"): title = line.split(":",1)[1].strip().strip('"').strip("'")
                elif line.startswith("digest:"): digest = line.split(":",1)[1].strip().strip('"').strip("'")
                elif line.startswith("series:") or line.startswith("category:"): series = line.split(":",1)[1].strip().strip('"').strip("'")
    reg = RegistryManager()
    reg.add_piece({"id":os.path.basename(filepath).replace(".md",""),"title":title,"digest":digest,"type":"article","file_path":filepath,"series":series})
    print(f"✅ 已添加: {title}")

def cmd_mark(piece_id, platform, status):
    reg = RegistryManager()
    if status not in STATUS_LABELS:
        print(f"❌ 无效状态: {status}. 有效值: {list(STATUS_LABELS.keys())}"); return
    if reg.update_platform(piece_id, platform, status):
        print(f"✅ {piece_id} → {PLATFORM_LABELS.get(platform,platform)} {STATUS_ICONS.get(status,'?')} {status}")
    else:
        print(f"❌ 未找到内容: {piece_id}")

def cmd_pending():
    reg = RegistryManager()
    pending = reg.get_pending()
    if not pending:
        print("✅ 无待发布内容"); return
    print(f"\n⏳ 待发布 ({len(pending)} 项):\n{'-'*60}")
    for piece, plat in pending:
        print(f"  {'📹' if piece.get('type')=='video' else '📝'} {piece['title']}\n     → {PLATFORM_LABELS.get(plat,plat)}  |  id={piece['id']}")

def cmd_summary():
    print(RegistryManager().get_summary())

def cmd_sync():
    reg = RegistryManager()
    count = reg.sync_from_publish_log()
    print(f"✅ 同步完成：{count} 条记录从 publish-log.json 导入\n")
    print(reg.get_summary())

def main():
    parser = argparse.ArgumentParser(description="内容发布可视化仪表盘 + 内容索引系统")
    sub = parser.add_subparsers(dest="cmd")
    p_serve = sub.add_parser("serve", help="启动仪表盘 HTTP 服务器")
    p_serve.add_argument("--port", type=int, default=5000)
    p_list = sub.add_parser("list", help="列出内容")
    p_list.add_argument("--pending", action="store_true")
    p_add = sub.add_parser("add", help="从 .md 文件添加内容")
    p_add.add_argument("file")
    p_mark = sub.add_parser("mark", help="手动标记平台状态")
    p_mark.add_argument("id"); p_mark.add_argument("platform"); p_mark.add_argument("status")
    sub.add_parser("pending"); sub.add_parser("summary"); sub.add_parser("sync")
    args = parser.parse_args()
    if args.cmd == "serve": cmd_serve(port=args.port)
    elif args.cmd == "list": cmd_list(pending_only=args.pending)
    elif args.cmd == "add": cmd_add(args.file)
    elif args.cmd == "mark": cmd_mark(args.id, args.platform, args.status)
    elif args.cmd == "pending": cmd_pending()
    elif args.cmd == "summary": cmd_summary()
    elif args.cmd == "sync": cmd_sync()
    else: parser.print_help()

if __name__ == "__main__":
    main()