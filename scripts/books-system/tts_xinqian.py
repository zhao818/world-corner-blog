# -*- coding: utf-8 -*-
"""《信任危机·前置条件论》12 章 → 单文件有声书 mp3(edge-tts 晓晓女声, +2%)

复用 tts_xiangjian.py 的清洗、合成、合并逻辑,并增强表格处理:
  清洗  clean_text/clean_inline —— 去 markdown 符号、填空线→「请自行填写」、
        箭头→「到」、去 emoji/表格线/带圈数字→中文数字(防 edge-tts 读出乱字符)
  表格  preprocess_tables —— 本文 4 张表(5.3 镜像/5.4 替身/8.1 修复/8.2 崩溃)
        按表头关键词分发为手写口语段落(逗号连接读起来太碎,朗读效果差)
  合成  edge-tts zh-CN-XiaoxiaoNeural, rate +2%, 3000 字/段, 6 并发, 失败重试 3 次
  合并  段间/章间 400ms 静音, ffmpeg concat -c copy → static/audio/xinqian.mp3
  时间  用 ffprobe 测每章时长,输出每章起始秒数供 audiobook.yaml chapters

用法:
    python tts_xinqian.py           # 合成全部 12 章并合并(已存在则跳过)
    python tts_xinqian.py 1         # 只合成第 1 章(冒烟),不合并 final
"""
import asyncio
import os
import re
import subprocess
import sys

import edge_tts

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "信任危机·前置条件论-灵魂之觅版.md")
OUT_TMP = r"F:\xiaochenxukaifa\有声书-信任危机\成品\_chapters"
FINAL = os.path.normpath(os.path.join(BASE, "..", "..", "static", "audio", "xinqian.mp3"))
VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "+2%"
CHUNK_CHARS = 3000
CONCURRENCY = 6
FFMPEG = r"H:\ffmpeg-2025-03-27-git-114fccc4a5-full_build\bin\ffmpeg.exe"
FFPROBE = r"H:\ffmpeg-2025-03-27-git-114fccc4a5-full_build\bin\ffprobe.exe"

# 章名(仅用于时间戳/展示,朗读不含章标题;name 进 audiobook.yaml chapters,
# 模板按 "-" 拆成序号 + 名称)
CHAPTER_NAMES = [
    "01-开卷声明", "02-哲学的天梯五问", "03-前置条件论", "04-反躬",
    "05-时代坐标", "06-时代的利弊", "07-避坑", "08-借势",
    "09-未来推演", "10-落点", "11-被抛弃的学术误区", "12-尾声",
]

# 表格 → 口语化朗读文本(trigger 匹配表头第一格)
TABLE_SPEECH = [
    ("贬值的",
     "旧信任货币贬值,新信任货币升值——人设、口碑、形象,换成记录、作品、可验证的产出;"
     "高调话术、权威叙事,换成平视、实证、可复现的过程;"
     "口头承诺、情感善意,换成契约、流程、第三方核验;"
     "大而空的关注、粉丝,换成小而深的信任、关系;"
     "信息不对称的我懂你不懂,换成主动透明的你随时可查。"),
    ("位置",
     "挨打的名单。亲密层,燕冬萍案——情感、付出、婚姻契约,可被叙事全盘抹除;"
     "2024年末北京离婚案,单方叙事全网反转。"
     "商业层,许家印——万亿级承诺崩塌,商业信任基石松动;2021年恒大债务爆雷。"
     "符号层,郭德纲、余承东——大师口碑回落、遥遥领先被解构;口碑近年持续回落,发布会口头禅被全网解构。"
     "组织层,韩红——善意机构被持续质疑;2020年疫情捐赠起被反复质疑。"
     "叙事层,孙宇晨——小作文成为通用博弈工具;币圈人物,以长篇小作文闻名。"),
    ("途径",
     "修复的途径有四条。第一条,制度重建,把证据、契约、流程制度化,"
     "改掉的是新信任土壤未建成这个前置条件,历史参照是镀金时代到进步主义,纯净食品法、美联储、穆迪、邓白氏,"
     "对应借势一和势五。"
     "第二条,共同经历重塑信任基线,改掉的是防御心态的普遍性,"
     "历史参照是罗马奥古斯都,和平与稳定本身重建信任,对应借势二、真诚稀缺放大。"
     "第三条,经济修复、预期松弛,改掉的是经济结构性不确定,"
     "历史参照是反复出现的经济周期,对应借势三和势四。"
     "第四条,平台被反逼治理,改掉的是平台逐利的纯成本面,"
     "历史参照是2008年危机后的多德弗兰克法案,对应势五、核验权争夺。"),
    ("可能",
     "崩溃的可能也有四种。第一种,塔西佗陷阱化,公信力归零、任何解释被反向解读,"
     "触发条件是信任跌破临界点、自我强化,历史参照是罗马帝国末期和明末,"
     "对应避坑一,越辩解越糟,不如让结果说话。"
     "第二种,全面原子化,不崩,但长期低效、高防备,"
     "触发条件是新信任范式长期不成型,历史参照是1970年代的美国,低信任但制度照常运转,"
     "对应坑六、单点叙事最脆,和势四、小信任圈。"
     "第三种,叙事武器化升级,AI伪造加小作文规模化,"
     "触发条件是制度滞后持续,历史参照是舆论构陷的逐级扩散,"
     "对应坑六,多源证据链是唯一防线。"
     "第四种,危机被利用,既得利益者收割真空,"
     "触发条件是信任真空长期存在,历史参照是每次大规模失信后都有投机者,"
     "对应坑二、坑三,人设与道德高地是收割者最爱的皮。"),
]


def cells_of(ln):
    return [c.strip() for c in ln.strip().strip("|").split("|")]


def table_block_to_speech(block):
    header_cells = cells_of(block[0])
    key = header_cells[0] if header_cells else ""
    for trigger, text in TABLE_SPEECH:
        if trigger in key:
            return [text]
    # 未识别的表格:fallback 逗号连接(表头跳过,数据行照旧)
    out = []
    for ln in block[2:]:
        out.append(clean_inline("，".join(c for c in cells_of(ln) if c)))
    return out


def preprocess_tables(text):
    """把 markdown 表格块替换为口语段落,供 clean_text 统一清洗"""
    out = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            out.extend(table_block_to_speech(block))
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


def clean_inline(ln):
    """行内符号统一清理:所有分支(标题/表格/正文)共用"""
    ln = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", ln)
    ln = re.sub(r"\*\*(.+?)\*\*", r"\1", ln)
    ln = re.sub(r"`(.+?)`", r"\1", ln)
    # 英文斜体 _word_ → word(先于填空线处理)
    ln = re.sub(r"_([^_]+)_", r"\1", ln)
    # 填空线 ______ / ＿＿＿ → 「请自行填写」,避免 edge-tts 读成「下划线」
    ln = re.sub(r"_{2,}", "请自行填写", ln)
    ln = re.sub(r"＿{2,}", "请自行填写", ln)
    # 装饰符号/emoji 残留直接删除
    ln = re.sub(r"[☀-➿️⃣\U0001F000-\U0001FAFF]", "", ln)
    # 箭头 → 读「到」;残留星号删除;不换行连字符转普通连字符
    ln = re.sub(r"→", "到", ln)
    ln = re.sub(r"\*+", "", ln)
    ln = re.sub(r"‑", "-", ln)
    # 带圈数字 → 中文数字
    ln = ln.replace("①", "一、").replace("②", "二、").replace("③", "三、")
    return ln


def clean_text(text):
    """markdown → 适合朗读的纯文本"""
    text = preprocess_tables(text)
    lines = []
    for raw in text.splitlines():
        ln = raw.rstrip()
        if not ln.strip():
            lines.append("")
            continue
        if re.fullmatch(r"-{3,}\s*", ln.strip()) or re.fullmatch(r"\*{1,3}\s*", ln.strip()):
            continue
        m = re.match(r"^#{1,6}\s+(.*)$", ln)
        if m:
            lines.append(clean_inline(m.group(1)).strip())
            lines.append("")
            continue
        if "|" in ln and ln.strip().startswith("|"):
            cells = cells_of(ln)
            if all(re.fullmatch(r":?-{2,}:?", c or "-") for c in cells if c):
                continue
            lines.append(clean_inline("，".join(c for c in cells if c)))
            continue
        ln = re.sub(r"^\s*>\s?", "", ln)
        ln = re.sub(r"^\s*[-*+]\s+", "", ln)
        lines.append(clean_inline(ln).strip())
    return "\n".join(lines)


# 多音字术语 → 括号拼音注音。
# zh-CN-XiaoxiaoNeural 对"重排/降权"读错(重→zhòng、降→xiáng),无上下文消歧。
# 实测"字(拼音)"注音可纠正读音(按拼音读、括号本身不读出),每个注音约增 0.35s。
PHONETIC_FIX = {
    "重排": "重(chóng)排",
    "降权": "降(jiàng)权",
}


def apply_phonetic_fix(text):
    for w, fx in PHONETIC_FIX.items():
        text = text.replace(w, fx)
    return text


def split_paragraphs(text, limit):
    chunks, cur = [], ""
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            cur += "\n"
            continue
        if cur and len(cur) + len(para) + 1 > limit:
            chunks.append(cur.strip())
            cur = para + "\n"
        else:
            cur += para + "\n"
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


async def synth_chunk(text, out_path, sem, label=""):
    async with sem:
        for attempt in range(3):
            try:
                tts = edge_tts.Communicate(text, VOICE, rate=RATE)
                await tts.save(out_path)
                return True
            except Exception as e:
                print("  %s合成失败(第%s次): %s" % (label, attempt + 1, e))
                await asyncio.sleep(2 * (attempt + 1))
        return False


async def synth_chapter(chunks, idx):
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = []
    for i, chunk in enumerate(chunks):
        p = os.path.join(OUT_TMP, "ch%02d_%03d.mp3" % (idx, i))
        tasks.append((i, chunk, p))
    results = await asyncio.gather(*[synth_chunk(c, p, sem, "段%03d " % i) for i, c, p in tasks])
    failed = [i for ok, (i, _, _) in zip(results, tasks) if not ok]
    if failed:
        print("  失败段序号: %s" % failed)
    return [p for ok, (_, _, p) in zip(results, tasks) if ok]


def merge_mp3(parts, final):
    if len(parts) == 1:
        os.replace(parts[0], final)
        return
    sil = os.path.join(OUT_TMP, "_silence.mp3")
    if not os.path.exists(sil):
        subprocess.run(
            [FFMPEG, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
             "-t", "0.4", "-c:a", "libmp3lame", "-b:a", "48k", "-ar", "24000", "-ac", "1", sil],
            check=True, capture_output=True,
        )
    lst = final + ".list.txt"
    with open(lst, "w", encoding="utf-8") as f:
        for i, p in enumerate(parts):
            f.write("file '%s'\n" % p.replace("\\", "/"))
            if i < len(parts) - 1:
                f.write("file '%s'\n" % sil.replace("\\", "/"))
    subprocess.run(
        [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", final],
        check=True, capture_output=True,
    )
    os.remove(lst)


def probe_dur(mp3):
    out = subprocess.run(
        [FFPROBE, "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", mp3],
        capture_output=True, text=True)
    return float(out.stdout.strip())


def split_chapters(src):
    text = open(src, encoding="utf-8").read()
    parts = re.split(r"(?m)^# (.+)$", text)
    return [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts), 2)]


def fmt(sec):
    m, s = int(sec) // 60, int(sec) % 60
    return "%02d:%02d" % (m, s)


def main():
    chapters = split_chapters(SRC)
    assert len(chapters) == 12, "章数 %d != 12" % len(chapters)

    only = None
    if len(sys.argv) > 1:
        only = int(sys.argv[1])

    os.makedirs(OUT_TMP, exist_ok=True)

    if only:
        # 冒烟:只合成第 1 章,打印清理文本供人工检查,不合并
        title, body = chapters[only - 1]
        cleaned = apply_phonetic_fix(clean_text(body))
        print("== 章%s · %s ==" % (only, title))
        print("清理后字数:", len(cleaned))
        print("---- 清理文本(前 800 字)----")
        print(cleaned[:800])
        chunks = split_paragraphs(cleaned, CHUNK_CHARS)
        print("分段数:", len(chunks))
        tmp = os.path.join(OUT_TMP, "ch%02d.mp3" % only)
        parts_ok = asyncio.run(synth_chapter(chunks, only))
        if len(parts_ok) != len(chunks):
            print("⚠ 有段失败,跳过")
            return
        merge_mp3(parts_ok, tmp)
        print("✅ 章mp3:", tmp, "(%.1f MB)" % (os.path.getsize(tmp) / 1024 / 1024), "时长", fmt(probe_dur(tmp)))
        return

    total_chars = 0
    chapter_mp3s = []
    starts = []
    acc = 0.0
    for idx, ((title, body), name) in enumerate(zip(chapters, CHAPTER_NAMES), start=1):
        tmp = os.path.join(OUT_TMP, "ch%02d.mp3" % idx)
        if os.path.exists(tmp):
            print("[%02d] %s 已有章节,跳过合成" % (idx, name))
        else:
            text = apply_phonetic_fix(clean_text(body))
            total_chars += len(text)
            chunks = split_paragraphs(text, CHUNK_CHARS)
            print("[%02d] %s: %d 字, %d 段,合成中..." % (idx, name, len(text), len(chunks)))
            parts_ok = asyncio.run(synth_chapter(chunks, idx))
            if len(parts_ok) != len(chunks):
                print("  ⚠ %d/%d 段失败,中止" % (len(parts_ok), len(chunks)))
                return
            merge_mp3(parts_ok, tmp)
            for p in parts_ok:
                try:
                    os.remove(p)
                except OSError:
                    pass
        dur = probe_dur(tmp)
        starts.append((name, round(acc, 1), round(dur, 1)))
        acc += dur + 0.4
        chapter_mp3s.append(tmp)
        print("  ✅ %s 起点 %s 时长 %s" % (name, fmt(starts[-1][1]), fmt(dur)))

    if os.path.exists(FINAL):
        print("final 已存在:", FINAL, "覆盖重合成前请确认")
        os.remove(FINAL)
    merge_mp3(chapter_mp3s, FINAL)
    print("✅ 合并完成:", FINAL, "(%.1f MB, 总时长 %s)" % (
        os.path.getsize(FINAL) / 1024 / 1024, fmt(probe_dur(FINAL))))

    print("\n== 每章起始时间戳(写入 audiobook.yaml chapters)==")
    for name, t, d in starts:
        print("- {t: %s, name: \"%s\", len: \"%s\"}" % (t, name, fmt(d)))

    print("\n总字数:", total_chars)


if __name__ == "__main__":
    main()
