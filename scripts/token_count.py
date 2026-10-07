"""DeepSeek V3 Token计数 CLI"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "deepseek_tokenizer", "deepseek_v3_tokenizer"))

from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained(
    os.path.join(os.path.dirname(__file__), "deepseek_tokenizer", "deepseek_v3_tokenizer"),
    trust_remote_code=True
)

text = sys.stdin.read().strip() if not sys.stdin.isatty() else " ".join(sys.argv[1:])
if not text:
    print("用法: echo '你的文本' | python token_count.py")
    print("      python token_count.py '你的文本'")

tokens = tokenizer.encode(text)
print(f"字数: {len(text)}   Token数: {len(tokens)}   比例: {len(tokens)/max(len(text),1):.2f} tok/字")
