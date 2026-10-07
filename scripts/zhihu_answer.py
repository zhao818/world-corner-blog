#!/usr/bin/env python3
"""知乎智能回答: 问题→知识库→LLM(DeepSeek/Qwen)→去AI味→草稿/发布"""
import argparse,json,os,re,sys,requests
from pathlib import Path; from datetime import datetime; from typing import Dict,List,Optional

# LLM 配置：优先 DeepSeek，回退 DashScope Qwen
LLM_API_KEY=os.environ.get("DEEPSEEK_API_KEY","") or os.environ.get("DASHSCOPE_API_KEY","")
LLM_BASE_URL="https://api.deepseek.com/v1" if os.environ.get("DEEPSEEK_API_KEY") else "https://dashscope.aliyuncs.com/compatible-mode/v1"
LLM_MODEL=os.environ.get("LLM_MODEL","deepseek-chat" if os.environ.get("DEEPSEEK_API_KEY") else "qwen-max")

KB_PATH=os.path.expanduser("~/world-corner-blog/content/posts")
COOKIE_FILE=os.path.expanduser("~/.claude/platform-cookies.json")

# 草稿目录: 优先 Desktop, fallback 到 home
_desk=os.path.expanduser("~/Desktop/zhihu_drafts")
DRAFT_DIR=_desk if os.path.isdir(os.path.dirname(_desk)) else os.path.expanduser("~/zhihu_drafts")

if not LLM_API_KEY:print("⚠ DEEPSEEK_API_KEY 或 DASHSCOPE_API_KEY 未设置")

# ── 1. Playwright 抓问题（过 ZSE-CK 反爬） ──
def fetch_question(qid:str)->Optional[Dict]:
    """Playwright 抓问题 → requests 回退 → 手动输入"""
    try:
        return _fetch_pw(qid)
    except Exception as e:
        print(f"  Playwright 失败: {e}")
    try:
        return _fetch_req(qid)
    except Exception as e:
        print(f"  requests 也失败: {e}")
    title=input("  手动输入问题标题: ").strip()
    detail=input("  手动输入问题描述(可选): ").strip()
    return {"id":qid,"title":title or f"问题{qid}","detail":detail}

def _fetch_pw(qid:str)->Optional[Dict]:
    from playwright.sync_api import sync_playwright
    if not os.path.exists(COOKIE_FILE):return None
    zhihu=json.load(open(COOKIE_FILE,encoding="utf-8")).get("zhihu",{})
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,
            args=['--disable-blink-features=AutomationControlled'])
        ctx=browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        page=ctx.new_page()
        for k,v in zhihu.items():
            if k=="configured_at":continue
            ctx.add_cookies([{"name":k,"value":v,"domain":".zhihu.com","path":"/"}])
        url=f"https://www.zhihu.com/question/{qid}"
        print(f"  浏览器抓取: {url}")
        page.goto(url,wait_until="networkidle",timeout=20000)
        if "signin" in page.url or page.title().startswith("你似乎"):
            print(f"  拒绝访问: {page.title()}")
            browser.close();return None
        try:
            data=page.evaluate("""()=>{
                const el=document.getElementById('js-initialData');
                return el?JSON.parse(el.textContent):null;
            }""")
        except:
            data=None
        if data:
            q=data.get("initialState",{}).get("entities",{}).get("questions",{}).get(qid,{})
            if q:
                title=q.get("title","")
                detail=re.sub(r"<[^>]+>","",q.get("detail",""))
                print(f"  ✅ {title}")
                browser.close();return {"id":qid,"title":title,"detail":detail[:2000]}
        title=page.title().replace(" - 知乎","").strip()
        print(f"  (从标题) {title}")
        browser.close();return {"id":qid,"title":title,"detail":""}

def _fetch_req(qid:str)->Optional[Dict]:
    r=requests.get(f"https://www.zhihu.com/question/{qid}",
        headers={"User-Agent":"Mozilla/5.0 Chrome/125.0","Accept":"text/html"},timeout=15)
    r.encoding="utf-8"
    if r.status_code!=200:return None
    m=re.search(r'<script id="js-initialData" type="text/json">(.*?)</script>',r.text,re.DOTALL)
    if m:
        data=json.loads(m.group(1))
        q=data.get("initialState",{}).get("entities",{}).get("questions",{}).get(qid,{})
        if q:
            title=q.get("title","");detail=re.sub(r"<[^>]+>","",q.get("detail",""))
            print(f"  {title}");return {"id":qid,"title":title,"detail":detail[:2000]}
    t=re.search(r'<title>(.+?)- 知乎</title>',r.text)
    title=t.group(1).strip()if t else f"问题{qid}"
    print(f"  {title}");return {"id":qid,"title":title,"detail":""}

# ── 2. 知识库搜索 ──
def search_kb(question:Dict)->List[Dict]:
    if not os.path.isdir(KB_PATH):return[]
    kw=set()
    for en in re.findall(r"[a-zA-Z#+.\-]{2,}",question["title"]):kw.add(en.lower())
    cn=re.sub(r"[^一-鿿]","",question["title"]+question.get("detail",""))
    for L in range(2,7):
        for i in range(len(cn)-L+1):kw.add(cn[i:i+L])
    stop={"的","了","在","是","我","有","和","就","不","人","都","一","上","也","很","到","说","要","去","你","会","着","没有","看","好","自己","这","他","她","它","们","那","什么","怎么","为什么","如何","哪个"}
    kw=[k for k in kw if k not in stop and len(k)>1]
    print(f"  关键词: {', '.join(kw[:10])}")
    arts=[]
    for md in Path(KB_PATH).rglob("*.md"):
        if md.name=="_index.md":continue
        c=md.read_text(encoding="utf-8",errors="ignore")
        meta=parse_fm(c);score=0;tl=c.lower()
        for k in kw:
            cnt=tl.count(k)
            if cnt:
                mult=5 if k in meta.get("title","").lower()else 4 if any(k in t.lower()for t in meta.get("tags",[]))else 1
                score+=cnt*mult
        if score>0:arts.append({"path":str(md),"title":meta.get("title",md.stem),"score":score,"content":c})
    arts.sort(key=lambda x:x["score"],reverse=True)
    print(f"  匹配 {len(arts)} 篇")
    for a in arts[:3]:print(f"    [{a['score']}分] {a['title']}")
    return arts[:3]

def parse_fm(content:str)->dict:
    meta={"title":"","tags":[],"categories":[]}
    m=re.match(r"^---\s*\n(.*?)\n---",content,re.DOTALL)
    if not m:return meta
    for line in m.group(1).split("\n"):
        kv=re.match(r'^(\w+):\s*"(.+)"',line)
        if kv:meta[kv.group(1)]=kv.group(2)
        lv=re.match(r'^(\w+):\s*\[(.*)\]',line)
        if lv:meta[lv.group(1)]=[v.strip().strip("\"'")for v in lv.group(2).split(",")if v.strip()]
    return meta

# ── 3. LLM 生成 ──
def call_llm(messages:list,t=0.8)->Optional[str]:
    if not LLM_API_KEY:return None
    try:
        url=f"{LLM_BASE_URL}/chat/completions"
        body=json.dumps({"model":LLM_MODEL,"messages":messages,"temperature":t,"max_tokens":4096})
        r=requests.post(url,
            headers={"Authorization":f"Bearer {LLM_API_KEY}","Content-Type":"application/json"},
            data=body.encode("utf-8"),timeout=120)
        r.raise_for_status();return r.json()["choices"][0]["message"]["content"]
    except Exception as e:print(f"  LLM失败: {e}");return None

def build_prompt(q:Dict,kb:List[Dict])->str:
    p=f"你是一位知乎答主。需要回答一个问题。\n\n## 问题\n标题: {q['title']}\n"
    if q.get("detail"):p+=f"描述: {q['detail'][:500]}\n"
    if kb:
        p+="\n## 可参考的知识库\n"
        for i,a in enumerate(kb,1):
            body=re.sub(r"^---.*?---\n?","",a["content"],flags=re.DOTALL)[:1500]
            p+=f"\n### {i}. {a['title']}\n{body}\n"
    p+="""\n## 写作要求\n风格: 第一段就给核心观点, 用案例说话\n禁用: 不是A而是B/值得一提的是/总的来说/X是一种强大的工具/随着X的发展\n人味: 口语化, 偶尔自嘲, 直接给结论\n不写谢邀, 不写站外链接, 800-2500字"""
    return p

def generate(q:Dict,kb:List[Dict])->Optional[str]:
    print("  生成中...")
    a=call_llm([
        {"role":"system","content":"你是知乎答主，回答有个人风格，绝不像AI写的。"},
        {"role":"user","content":build_prompt(q,kb)}])
    if not a:return None
    a=re.sub(r"^谢邀[，。!！\s]*","",a)
    for p in [r"某种意义上[^。]*",r"值得一提[^。]*",r"毫无疑问[^。]*",
              r"不得不说[^。]*",r"总的来说[^。]*",r"综上所述[^。]*",
              r"首先[^，,]*[，,]\s*其次",r"是一种强大的[^。]*",r"随着[^。]*不断发展"]:
        for m in re.findall(p,a):
            if m.strip():print(f"    AI句式: {m[:50]}")
    print(f"  生成 {len(a)} 字\n"+"-"*30+f"\n{a[:300]}{'...' if len(a)>300 else ''}\n"+"-"*30)
    return a.strip()

# ── 4. 存稿 ──
def save_draft(q:Dict,ans:str)->str:
    os.makedirs(DRAFT_DIR,exist_ok=True)
    safe=re.sub(r"[^\w一-鿿]","_",q["title"])[:30]
    p=os.path.join(DRAFT_DIR,f"answer_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe}.md")
    with open(p,"w",encoding="utf-8")as f:
        f.write(f"# {q['title']}\n链接: https://www.zhihu.com/question/{q['id']}\n---\n\n{ans}")
    print(f"  📝 草稿: {p}");return p

# ── 5. 发布（知乎 API, 7天限制期会 403） ──
def publish(qid:str,ans:str)->bool:
    if not os.path.exists(COOKIE_FILE):print("  无cookie");return False
    with open(COOKIE_FILE,encoding="utf-8")as f:creds=json.load(f).get("zhihu",{})
    zc,xs=creds.get("z_c0",""),creds.get("_xsrf","")
    if not zc or not xs:print("  cookie不完整");return False
    def _fmt(l):
        l=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',l)
        l=re.sub(r'`([^`]+)`',r'<code>\1</code>',l);return l
    h="".join(f"<p>{_fmt(line)}</p>"if line.strip()else""for line in ans.split("\n"))
    r=requests.post(f"https://www.zhihu.com/api/v4/questions/{qid}/answers",
        headers={"User-Agent":"Mozilla/5.0 Chrome/125.0","Cookie":f"z_c0={zc}; _xsrf={xs}",
                 "x-xsrftoken":xs,"Content-Type":"application/json;charset=utf-8"},
        json={"content":h,"reshipment_settings":"allowed","comment_permission":"all","reward_setting":{"can_reward":False}},timeout=30)
    if r.status_code in(200,201):
        a_id=r.json().get("id","")
        print(f"  🚀 发布成功! https://www.zhihu.com/question/{qid}/answer/{a_id}")
        return True
    print(f"  ❌ 发布失败 HTTP {r.status_code}")
    if r.status_code==403:
        try:
            err=r.json().get("error",{})
            print(f"    原因: {err.get('message','')}")
        except:pass
    return False

# ── 主入口 ──
def main():
    ap=argparse.ArgumentParser(description="知乎智能回答",epilog="示例: python zhihu_answer.py https://www.zhihu.com/question/XXXXX")
    ap.add_argument("url",nargs="?",help="问题链接 (URL 或 qid)")
    ap.add_argument("--question-id")
    ap.add_argument("--publish",action="store_true",help="生成后直接发布")
    ap.add_argument("--interactive","-i",action="store_true",help="交互模式 (默认)")
    args=ap.parse_args()

    if args.interactive or len(sys.argv)==1:
        q=input("  问题链接/ID: ").strip()
        m=re.search(r"question/(\d+)",q);qid=m.group(1)if m else q
        qq=fetch_question(qid)
        if not qq:print("  无法获取问题");return
        kb=search_kb(qq);ans=generate(qq,kb)
        if not ans:return
        p=save_draft(qq,ans)
        inp=input("发布？(y/N): ").strip().lower()
        if inp=="y":
            if not publish(qid,ans):
                print(f"  发布失败，草稿保留: {p}")
        return

    qid=args.question_id
    if args.url:
        m=re.search(r"question/(\d+)",args.url)
        if m:qid=m.group(1)
    if not qid:print("需提供问题链接或 --question-id");return

    qq=fetch_question(qid)
    if not qq:
        qq={"id":qid,"title":input("  问题标题: ").strip(),"detail":input("  问题描述(可选): ").strip()}
    kb=search_kb(qq);ans=generate(qq,kb)
    if not ans:return
    p=save_draft(qq,ans)
    if args.publish:
        if not publish(qid,ans):print(f"  发布失败，草稿保留: {p}")
    else:print(f"  草稿: {p} (加 --publish 自动发布 / 交互模式可发布)")

if __name__=="__main__":main()
