#!/usr/bin/env python3
"""VideoFast Watchdog Edition"""
import json,os,sys,subprocess,threading,time,uuid,re,logging
from datetime import datetime;from pathlib import Path;from logging.handlers import RotatingFileHandler
from flask import Flask,request,jsonify
app=Flask(__name__)
PIPELINE_DIR=Path(r"C:\Users\zhaot\projects\remotion-video-platform\scripts")
ORDER_LOG=Path(r"C:\Users\zhaot\.claude\videofast-orders.jsonl")
LOG_DIR=Path(r"C:\Users\zhaot\.claude\logs");LOG_FILE=LOG_DIR/"videofast.log";PID_FILE=LOG_DIR/"videofast.pid"
LOG_DIR.mkdir(parents=True,exist_ok=True)
_handler=RotatingFileHandler(str(LOG_FILE),maxBytes=10*1024*1024,backupCount=7,encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",datefmt="%Y-%m-%d %H:%M:%S"));_handler.setLevel(logging.DEBUG)
app.logger.addHandler(_handler);app.logger.setLevel(logging.DEBUG)
_console=logging.StreamHandler(sys.stderr);_console.setFormatter(logging.Formatter("[videofast] %(message)s"));_console.setLevel(logging.INFO);app.logger.addHandler(_console)
log=app.logger
def write_pid():PID_FILE.write_text(str(os.getpid()))
def check_pid():
    if not PID_FILE.exists():return False
    try:
        pid=int(PID_FILE.read_text().strip())
        if os.name=="nt":
            import ctypes;h=ctypes.windll.kernel32.OpenProcess(0x0400,False,pid)
            if h:ctypes.windll.kernel32.CloseHandle(h);log.warning(f"已有实例运行中(PID {pid})");return True
    except:PID_FILE.unlink(missing_ok=True)
    return False
TEMPLATE_MAP={"口播干货":{"hook":"counterintuitive","theme":"midnight-galaxy","cta":"关注公众号「美好需要创造」"},"开箱带货":{"hook":"scroll-stopper","theme":"ocean-depths","cta":"公众号「美好需要创造」回复「工具」获取同款"},"数据报告":{"hook":"number-shock","theme":"sunset-boulevard","cta":"数据来源公开可查·公众号「美好需要创造」整理"}}
_render_queue=[];_render_lock=threading.Lock();_render_thread=None;_worker_state={"processed":set(),"failures":{},"max_retries":2};_shutdown_flag=False
def ensure_dir(p):p.parent.mkdir(parents=True,exist_ok=True)
def log_order(o):
    ensure_dir(ORDER_LOG)
    with open(str(ORDER_LOG),"a",encoding="utf-8") as f:f.write(json.dumps(o,ensure_ascii=False)+"\n")
def update_kv_status(oid,status,extra=None):
    import urllib.request as ur
    try:
        p=json.dumps({"order_id":oid,"status":status,**(extra or {})},ensure_ascii=False).encode()
        r=ur.Request(f"https://api.worldcorner.xyz/videofast/order/{oid}",data=p,headers={"Content-Type":"application/json; charset=utf-8"},method="PATCH")
        ur.urlopen(r,timeout=10);log.info(f"[kv]{oid}->{status}");return True
    except Exception as e:log.warning(f"[kv]update failed {oid}:{e}");return False
def send_email(to,subject,body):
    import smtplib;from email.mime.text import MIMEText
    try:
        msg=MIMEText(body,"plain","utf-8");msg["From"]="VideoFast<zhao818@gmail.com>";msg["To"]=to;msg["Subject"]=subject
        with smtplib.SMTP("smtp.gmail.com",587) as s:s.starttls();s.login("zhao818@gmail.com","xmpzabmpevuapgph");s.send_message(msg)
        log.info(f"[email]Sent:{subject}");return True
    except:
        log.warning(f"[email]SMTP失败")
        try:
            os.chdir(r"H:\anzhuo\deepseek-autogen-app");from composio import Composio;c=Composio()
            for a in getattr(c.connected_accounts.list(),"items",[]):
                if hasattr(a,"toolkit")and getattr(a.toolkit,"slug","")=="gmail"and a.status=="ACTIVE":
                    s=c.create(user_id="reasonix-user",toolkits=["gmail"])
                    for t in s.tools():
                        if"send"in t.get("name","").lower():s.execute(tool_name=t["name"],params={"to":to,"subject":subject,"body":body});return True
        except:pass
        return False
def render_video(order):
    oid=order["order_id"];t=order.get("title","");s=order.get("subtitle","");c=order.get("cards","");m=TEMPLATE_MAP.get(order.get("template",""),TEMPLATE_MAP["口播干货"])
    cmd=[sys.executable,str(PIPELINE_DIR/"video_pipeline.py"),t,"--subtitle",s or t,"--cards",c or f"评论:8%,粉丝:5k,点赞:3k","--feature",s or t,"--hook",m["hook"],"--theme",m["theme"],"--cta",m["cta"],"--auto"]
    log.info(f"[render]{oid}开始渲染")
    try:
        r=subprocess.run(cmd,cwd=str(PIPELINE_DIR),capture_output=True,text=True,timeout=600,encoding="utf-8",errors="replace");log.info(r.stdout[-500:])
        if r.stderr:log.warning(f"[render]STDERR:{r.stderr[:300]}")
        m2=re.search(r"(out[\\/][^\s]+\.mp4)",r.stdout)
        if m2:vp=str(PIPELINE_DIR.parent/m2.group(1));return{"success":True,"video_path":vp}if os.path.exists(vp)else{"success":True,"video_path":vp,"warning":"路径存在但待确认"}
        d=PIPELINE_DIR.parent/"out"
        if d.exists():
            mps=sorted(d.glob("*.mp4"),key=os.path.getmtime,reverse=True)
            if mps:return{"success":True,"video_path":str(mps[0])}
        return{"success":False,"error":f"未找到输出视频\n{r.stdout[-200:]}"}
    except subprocess.TimeoutExpired:return{"success":False,"error":"渲染超时(>10min)"}
    except Exception as e:return{"success":False,"error":str(e)}
def process_order(order):
    oid=order["order_id"];email=order.get("contact","");title=order.get("title","");log.info(f"[order]{oid}:{title}")
    order["status"]="processing";order["processing_at"]=datetime.now().isoformat();log_order(order);update_kv_status(oid,"processing")
    result=render_video(order)
    if result["success"]:
        order["status"]="done";order["video_path"]=result["video_path"];order["done_at"]=datetime.now().isoformat()
        log_order(order);update_kv_status(oid,"done",{"video_path":result["video_path"]})
        if email and"@"in email:
            b=f"你好！\n\n你的VideoFast视频「{title}」已生成完成。\n\n📹视频文件:{result['video_path']}\n\n下载链接:https://video.worldcorner.xyz\n\n——\n由VideoFastAI自动生成\n关注公众号「美好需要创造」获取更多免费次数"
            order["email_sent"]=send_email(email,f"🎬你的视频「{title}」已生成",b)
        else:order["email_sent"]=False
    else:
        order["status"]="failed";order["error"]=result["error"];order["failed_at"]=datetime.now().isoformat()
        log_order(order);update_kv_status(oid,"failed",{"error":result["error"]})
        if email and"@"in email:send_email(email,f"⚠️视频「{title}」生成遇到问题",f"抱歉，生成过程中遇到问题:{result['error']}\n我们会尽快处理。")
    log_order(order);log.info(f"[order]{oid}:{order['status']}")
def render_worker():
    import urllib.request as ur;U="https://api.worldcorner.xyz/videofast/queue"
    while not _shutdown_flag:
        try:
            for o in json.loads(ur.urlopen(ur.Request(U),timeout=10).read()):
                oid,st=o.get("order_id",""),o.get("status","")
                if not oid or st in("done","processing")or oid in _worker_state["processed"]:continue
                if st=="failed"and _worker_state["failures"].get(oid,0)>=_worker_state["max_retries"]:
                    if oid not in _worker_state["processed"]:_worker_state["processed"].add(oid)
                    continue
                if st!="queued":continue
                log.info(f"[worker]KV:{oid}");process_order(o)
                if o.get("status")=="done":_worker_state["processed"].add(oid);_worker_state["failures"].pop(oid,None)
                elif o.get("status")=="failed":_worker_state["failures"][oid]=_worker_state["failures"].get(oid,0)+1
        except Exception as e:log.warning(f"[worker]KV poll error:{e}")
        lo=None
        with _render_lock:
            if _render_queue:lo=_render_queue.pop(0)
        if lo and lo.get("status")=="queued":log.info(f"[worker]LOCAL:{lo.get('order_id')}");process_order(lo)
        time.sleep(5)
    log.info("[worker]退出")
@app.route("/videofast/health")
def health():return jsonify({"status":"ok","queue":len(_render_queue),"alive":_render_thread is not None and _render_thread.is_alive(),"done":len(_worker_state["processed"]),"fails":len(_worker_state["failures"])})
@app.route("/videofast/order",methods=["POST"])
def create_order():
    d=request.get_json(silent=True)or{}
    if not d.get("title"):return jsonify({"error":"缺少视频标题"}),400
    o={"order_id":f"vf_{uuid.uuid4().hex[:8]}","title":d.get("title",""),"subtitle":d.get("subtitle",""),"cards":d.get("cards",""),"template":d.get("template","口播干货"),"contact":d.get("contact",""),"status":"queued","created_at":datetime.now().isoformat()}
    log_order(o)
    with _render_lock:_render_queue.append(o);pos=len(_render_queue)
    return jsonify({"order_id":o["order_id"],"status":"queued","queue_position":pos,"message":f"订单已收到！预计{pos*5+3}分钟内发送到{o['contact']}"})
WATCHDOG_DELAY=5
def run_server(port):
    global _render_thread,_shutdown_flag;_shutdown_flag=False;write_pid()
    log.info(f"启动VideoFast(PID{os.getpid()})http://127.0.0.1:{port}/videofast/health")
    _render_thread=threading.Thread(target=render_worker,daemon=True);_render_thread.start()
    app.run(host="127.0.0.1",port=port,debug=False)
def run_with_watchdog(port):
    n=0
    while True:
        try:run_server(port);log.info("正常退出");break
        except KeyboardInterrupt:log.info("Ctrl+C退出");break
        except SystemExit:log.info("系统退出");break
        except Exception as e:n+=1;log.error(f"崩溃(第{n}次):{e}",exc_info=True);log.info(f"{WATCHDOG_DELAY}秒后重启...");time.sleep(WATCHDOG_DELAY);PID_FILE.unlink(missing_ok=True)
TASK_NAME="VideoFastServer";SCRIPT_PATH=Path(__file__).resolve();PYTHON_EXE=sys.executable
def install_service():
    import subprocess as sp
    c=sp.run(["powershell","-NoProfile","-Command",f"Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue"],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=15)
    if TASK_NAME in c.stdout:sp.run(["powershell","-NoProfile","-Command",f"Unregister-ScheduledTask -TaskName '{TASK_NAME}' -Confirm:$false"],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=15);time.sleep(1)
    # 使用schtasks命令创建计划任务
    python_exe_posix = str(PYTHON_EXE).replace('\\', '/')
    script_path_posix = str(SCRIPT_PATH).replace('\\', '/')
    ps = f"schtasks /create /tn '{TASK_NAME}' /tr '\"{python_exe_posix}\" \"{script_path_posix}\" --port 5001' /sc onstart /ru SYSTEM /rl HIGHEST /f"
    r=sp.run(["powershell","-NoProfile","-Command",ps],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30)
    if r.returncode==0:
        log.info(f"开机自启已注册:'{TASK_NAME}'");log.info(f"\"{PYTHON_EXE}\" \"{SCRIPT_PATH}\" --port 5001")
    else:
        log.error(f"注册失败:{r.stderr or r.stdout}")
        log.info("请以管理员身份运行: python videofast_server.py --install")
        return
def remove_service():
    import subprocess as sp
    r=sp.run(["powershell","-NoProfile","-Command",f"Unregister-ScheduledTask -TaskName '{TASK_NAME}' -Confirm:$false"],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=15)
    if r.returncode==0:log.info(f"已移除开机自启:'{TASK_NAME}'")
    else:log.warning(f"移除失败:{r.stderr or r.stdout}")
def show_status():
    import subprocess as sp;print(f"\n{'='*50}\n  VideoFast服务状态\n{'='*50}")
    r=sp.run(["powershell","-NoProfile","-Command",f"Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue|Format-List State,TaskPath,LastRunTime,LastTaskResult"],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=15)
    print(f"\n计划任务:")
    if TASK_NAME in r.stdout:
        for l in r.stdout.strip().splitlines():print(f"   {l}")
    else:print(f"   未注册")
    if PID_FILE.exists():
        try:
            pid=int(PID_FILE.read_text().strip());import ctypes;h=ctypes.windll.kernel32.OpenProcess(0x0400,False,pid)
            if h:
                ctypes.windll.kernel32.CloseHandle(h);print(f"\n运行中(PID{pid})")
                import urllib.request as ur
                try:j=json.loads(ur.urlopen(ur.Request("http://127.0.0.1:5001/videofast/health"),timeout=5).read());print(f"   健康:{json.dumps(j,indent=4,ensure_ascii=False)}")
                except:print(f"   进程存在但端口无响应")
            else:print(f"\n未运行");PID_FILE.unlink(missing_ok=True)
        except:print(f"\n未运行")
    else:print(f"\n未运行")
    sz=LOG_FILE.stat().st_size if LOG_FILE.exists()else 0;oc=0
    if ORDER_LOG.exists():
        try:
            with open(str(ORDER_LOG),"r",encoding="utf-8") as f:oc=sum(1 for _ in f)
        except:pass
    print(f"\n日志:{LOG_FILE}({sz/1024:.0f}KB)订单:{oc}")
    if LOG_FILE.exists():
        print(f"最后20行:")
        try:
            for l in LOG_FILE.read_text(encoding="utf-8").strip().splitlines()[-20:]:print(f"   {l}")
        except:pass
    print()
def main():
    import argparse
    p=argparse.ArgumentParser(description="VideoFast订单服务")
    p.add_argument("--port",type=int,default=5001);p.add_argument("--install",action="store_true");p.add_argument("--remove",action="store_true");p.add_argument("--status",action="store_true")
    a=p.parse_args()
    if a.install:install_service();return
    if a.remove:remove_service();return
    if a.status:show_status();return
    if check_pid():log.warning("退出--已有实例运行");sys.exit(1)
    run_with_watchdog(a.port)
if __name__=="__main__":main()