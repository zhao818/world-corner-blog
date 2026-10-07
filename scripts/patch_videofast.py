#!/usr/bin/env python3
"""Patch videofast_server.py — fix 3 bugs without touching credential lines"""
import sys, os

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'videofast_server.py')

with open(TARGET, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 2: process_order — add KV status update + state machine
old_p1 = '''def process_order(order: dict):
    """异步处理订单：渲染 → 发邮件"""
    oid = order["order_id"]
    email = order.get("contact", "")
    title = order.get("title", "")

    result = render_video(order)

    if result["success"]:
        order["status"] = "done"
        order["video_path"] = result["video_path"]
        log_order(order)

        # 发邮件
        if email and "@" in email:'''

new_p1 = '''def process_order(order: dict):
    """处理订单：标记 processing → 渲染 → 发邮件 → done/failed"""
    oid = order["order_id"]
    email = order.get("contact", "")
    title = order.get("title", "")

    print(f"[order] {oid}: {title}")

    # 标记 processing
    order["status"] = "processing"
    order["processing_at"] = datetime.now().isoformat()
    log_order(order)
    update_kv_status(oid, "processing")

    result = render_video(order)

    if result["success"]:
        order["status"] = "done"
        order["video_path"] = result["video_path"]
        order["done_at"] = datetime.now().isoformat()
        log_order(order)
        update_kv_status(oid, "done", {"video_path": result["video_path"]})

        # 发邮件
        if email and "@" in email:'''

if old_p1 not in content:
    print('ERROR: Fix 2a pattern not found')
    sys.exit(1)
content = content.replace(old_p1, new_p1)
print('Fix 2a: process_order header + processing state')

# Fix 2b
old_p2 = '''            send_email(email, f"🎬 你的视频「{title}」已生成", body)
            order["email_sent"] = True'''
new_p2 = '''            email_ok = send_email(email, f"🎬 你的视频「{title}」已生成", body)
            order["email_sent"] = email_ok'''
content = content.replace(old_p2, new_p2)
print('Fix 2b: email_sent tracking')

# Fix 2c
old_p3 = '''    else:
        order["status"] = "failed"
        order["error"] = result["error"]
        log_order(order)'''
new_p3 = '''    else:
        order["status"] = "failed"
        order["error"] = result["error"]
        order["failed_at"] = datetime.now().isoformat()
        log_order(order)
        update_kv_status(oid, "failed", {"error": result["error"]})'''
content = content.replace(old_p3, new_p3)
print('Fix 2c: failed state + KV update')

# Fix 2d
old_p4 = '''    log_order(order)


def render_worker():'''
new_p4 = '''    log_order(order)
    print(f"[order] {oid}: {order['status']}")


def render_worker():'''
content = content.replace(old_p4, new_p4)
print('Fix 2d: status print')

# Fix 3: render_worker
old_w = '''def render_worker():
    """后台渲染线程 — 轮询 KV 队列"""
    import urllib.request as ur
    KV_QUEUE_URL = "https://api.worldcorner.xyz/videofast/queue"

    processed = set()
    while True:
        try:
            resp = json.loads(ur.urlopen(ur.Request(KV_QUEUE_URL), timeout=5).read())
            for order in resp:
                oid = order.get("order_id", "")
                if oid and oid not in processed and order.get("status") == "queued":
                    processed.add(oid)
                    process_order(order)
        except Exception as e:
            print(f"[poll] {e}")

        time.sleep(5)  # 每5秒轮询一次'''

new_w = '''def render_worker():
    """后台渲染线程 — 轮询 KV 队列 + 消费本地队列"""
    import urllib.request as ur
    KV_QUEUE_URL = "https://api.worldcorner.xyz/videofast/queue"

    max_retries = _worker_state["max_retries"]
    while True:
        # 1. 轮询 KV 队列
        try:
            resp = json.loads(ur.urlopen(ur.Request(KV_QUEUE_URL), timeout=10).read())
            for order in resp:
                oid = order.get("order_id", "")
                status = order.get("status", "")
                if not oid:
                    continue
                if status in ("done", "processing"):
                    continue
                if oid in _worker_state["processed"]:
                    continue
                retries = _worker_state["failures"].get(oid, 0)
                if status == "failed" and retries >= max_retries:
                    if oid not in _worker_state["processed"]:
                        print(f"[worker] SKIP {oid}: max retries")
                        _worker_state["processed"].add(oid)
                    continue
                if status != "queued":
                    continue
                print(f"[worker] KV: {oid}")
                process_order(order)
                if order.get("status") == "done":
                    _worker_state["processed"].add(oid)
                    _worker_state["failures"].pop(oid, None)
                elif order.get("status") == "failed":
                    _worker_state["failures"][oid] = _worker_state["failures"].get(oid, 0) + 1
        except Exception as e:
            print(f"[worker] KV poll error: {e}")
        # 2. 消费本地队列
        local_order = None
        with _render_lock:
            if _render_queue:
                local_order = _render_queue.pop(0)
        if local_order and local_order.get("status") == "queued":
            print(f"[worker] LOCAL: {local_order.get('order_id')}")
            process_order(local_order)
        time.sleep(5)'''

if old_w not in content:
    print('ERROR: Fix 3 pattern not found')
    idx = content.find('def render_worker():')
    if idx >= 0:
        print('Found at', idx, repr(content[idx:idx+200]))
    sys.exit(1)
content = content.replace(old_w, new_w)
print('Fix 3: render_worker with local queue + retry')

# Fix 4: health endpoint
old_h = '''    return jsonify({"status": "ok", "queue": len(_render_queue)})'''
new_h = '''    return jsonify({
        "status": "ok",
        "local_queue": len(_render_queue),
        "worker_alive": _render_thread is not None and _render_thread.is_alive(),
        "kv_processed": len(_worker_state["processed"]),
        "kv_failures": len(_worker_state["failures"]),
    })'''
content = content.replace(old_h, new_h)
print('Fix 4: health endpoint enhanced')

with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(content)
print('All fixes applied successfully!')
