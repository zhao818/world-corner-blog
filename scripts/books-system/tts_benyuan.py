# -*- coding: utf-8 -*-
"""《信任本源论》7 章 → 单文件有声书 mp3(edge-tts 晓晓女声, +2%)

复用 tts_quanti.py 的清洗、合成、合并逻辑,针对本文调整:
  章节   7 章,一级标题也朗读(本文是单篇长文,听众需要章边界,qunti 式 title 注入)
  表格   本文无 markdown 表格(TABLE_SPEECH 留空兜底)
  符号   箭头 → 读「到」;乘号 × → 顿号(正文虽未见 ×,保留与 qunti 一致)
  合成   edge-tts zh-CN-XiaoxiaoNeural, rate +2%, 3000 字/段, 6 并发, 失败重试 3 次
  合并   段间/章间 400ms 静音, ffmpeg concat -c copy → static/audio/benyuan.mp3
  时间   用 ffprobe 测每章时长,输出每章起始秒数供 audiobook.yaml chapters

用法:
    python tts_benyuan.py           # 合成全部 7 章并合并(已存在则跳过)
    python tts_benyuan.py 1         # 只合成第 1 章(冒烟),不合并 final
"""
import asyncio
import os
import re
import subprocess
import sys

import edge_tts

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "信任本源论-灵魂之觅版.md")
OUT_TMP = r"F:\xiaochenxukaifa\有声书-本源论\成品\_chapters"
FINAL = os.path.normpath(os.path.join(BASE, "..", "..", "static", "audio", "benyuan.mp3"))
VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "+2%"
CHUNK_CHARS = 3000
CONCURRENCY = 6
FFMPEG = r"H:\ffmpeg-2025-03-27-git-114fccc4a5-full_build\bin\ffmpeg.exe"
FFPROBE = r"H:\ffmpeg-2025-03-27-git-114fccc4a5-full_build\bin\ffprobe.exe"

# 章名(仅用于时间戳/展示;朗读用一级标题原文,见 main 中 title 注入;与 audiobook.yaml chapters 同名保持一致)
CHAPTER_NAMES = [
    "01-开卷", "02-本能推理", "03-崩塌",
    "04-分化", "05-固化", "06-反躬", "07-尾声",
]

# 表格 → 口语化朗读文本(本文无表格,留空兜底)
TABLE_SPEECH = [
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
    # 箭头 → 读「到」;乘号 × → 顿号;残留星号删除
    ln = re.sub(r"→", "到", ln)
    ln = re.sub(r"\s*×\s*", "、", ln)
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
    assert len(chapters) == 7, "章数 %d != 7" % len(chapters)

    only = None
    if len(sys.argv) > 1:
        only = int(sys.argv[1])

    os.makedirs(OUT_TMP, exist_ok=True)

    if only:
        # 冒烟:只合成第 1 章,打印清理文本供人工检查,不合并
        title, body = chapters[only - 1]
        cleaned = title + "\n\n" + clean_text(body)
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
            text = title + "\n\n" + clean_text(body)
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
