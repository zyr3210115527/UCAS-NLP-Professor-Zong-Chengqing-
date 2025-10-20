import os
import re
import math
import csv
from collections import Counter
from tqdm import tqdm

try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except Exception:
    HAS_MPL = False

###############################################################################
# 配置
###############################################################################
# 当前目录（包含人民日报子文件夹）
CORPUS_ROOT = "."
SUBDIR_PATTERN = re.compile(r".*")             # 匹配所有子文件夹
TXT_PATTERN = re.compile(r".*\.txt$", re.IGNORECASE)
SCALING_STEP = 10                              # 每隔多少个文件记录一次扩容
OUT_DIR = "analysis_output"                    # 输出目录

###############################################################################
# 读取与清洗
###############################################################################
def iter_txt_files(root):
    if not os.path.isdir(root):
        raise SystemExit(f"未找到目录：{root}")
    items = []
    for ent in os.scandir(root):
        if ent.is_dir() and SUBDIR_PATTERN.match(ent.name):
            for sub in os.scandir(ent.path):
                if sub.is_file() and TXT_PATTERN.match(sub.name):
                    items.append((ent.name, sub.name, sub.path))
    items.sort(key=lambda x: (x[0], x[1]))
    return [p for _, _, p in items]

def read_text(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        txt = f.read()
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = re.sub(r"[ \t\u00A0]+", " ", txt)
    txt = txt.replace("\u3000", " ")
    txt = "".join(ch for ch in txt if (ch == "\n" or (ord(ch) >= 32 and ch != "\x7f")))
    txt = txt.replace("\ufffd", "")
    return txt

def extract_chinese_chars(text):
    """提取所有汉字（用于统计概率与熵）"""
    return "".join(ch for ch in text if "\u4e00" <= ch <= "\u9fff")

###############################################################################
# 统计与拟合
###############################################################################
def probs_and_entropy(counter):
    total = sum(counter.values())
    if total == 0:
        return 0, {}, 0.0
    prob = {k: v / total for k, v in counter.items()}
    entropy = -sum(p * math.log(p, 2) for p in prob.values() if p > 0)
    return total, prob, entropy

def rank_freq(counter):
    return [(i, tok, f) for i, (tok, f) in enumerate(counter.most_common(), start=1)]

def linear_fit_loglog(rank_freq_list):
    xs, ys = [], []
    for r, _, f in rank_freq_list:
        if r > 0 and f > 0:
            xs.append(math.log(r))
            ys.append(math.log(f))
    n = len(xs)
    if n < 2:
        return 0.0, 0.0, 0.0
    mx, my = sum(xs)/n, sum(ys)/n
    sxx = sum((x - mx)**2 for x in xs)
    sxy = sum((x - mx)*(y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        return 0.0, 0.0, 0.0
    b = sxy / sxx
    a = my - b * mx
    syy = sum((y - my)**2 for y in ys)
    r2 = (sxy**2) / (sxx * syy) if syy > 0 else 0.0
    return a, b, r2

###############################################################################
# 输出与绘图
###############################################################################
def ensure_outdir():
    os.makedirs(OUT_DIR, exist_ok=True)

def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

def plot_zipf(rank_freq_list, title, out_png):
    if not HAS_MPL:
        print(f"[INFO] 未安装 matplotlib，跳过绘图：{out_png}")
        return
    ranks = [r for r, _, _ in rank_freq_list]
    freqs = [f for _, _, f in rank_freq_list]
    plt.figure()
    plt.loglog(ranks, freqs, marker='o', linestyle='None', markersize=3)
    plt.xlabel("Rank")
    plt.ylabel("Frequency")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_png, dpi=180)
    plt.close()

def plot_scaling(xs, entropies, slopes, out_png):
    if not HAS_MPL:
        print(f"[INFO] 未安装 matplotlib，跳过绘图：{out_png}")
        return
    fig, ax1 = plt.subplots()
    ax1.plot(xs, entropies, marker="o", label="Entropy")
    ax1.set_xlabel("Number of files (cumulative)")
    ax1.set_ylabel("Entropy (bits)")

    ax2 = ax1.twinx()
    ax2.plot(xs, slopes, marker="x", color='orange', label="Zipf slope")
    ax2.set_ylabel("Zipf slope (log-log)")
    fig.suptitle("Scaling analysis: Chinese Entropy & Zipf slope")
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)

###############################################################################
# 主流程
###############################################################################
def main():
    ensure_outdir()
    files = iter_txt_files(CORPUS_ROOT)
    if not files:
        raise SystemExit("[WARN] 未找到任何 txt 文件，请检查路径与命名。")

    print(f"[INFO] 发现 {len(files)} 个文件，开始读取与清洗 …")
    cn_all = []

    # 读取所有文本
    for p in tqdm(files, desc="Reading & Cleaning", ncols=80):
        txt = read_text(p)
        cn = extract_chinese_chars(txt)
        if cn:
            cn_all.append(cn)

    cn_text = "".join(cn_all)
    cn_counter = Counter(cn_text)
    total, prob, entropy = probs_and_entropy(cn_counter)

    print(f"[中文统计] 汉字总数: {total:,}；唯一汉字: {len(cn_counter):,}；信息熵: {entropy:.4f} bits")

    # 输出频率和概率表
    rows = [[ch, freq, prob[ch]] for ch, freq in cn_counter.most_common()]
    write_csv(os.path.join(OUT_DIR, "cn_char_probabilities.csv"),
              ["char", "frequency", "probability"],
              rows)

    # 齐夫定律验证
    rank_freq_data = rank_freq(cn_counter)
    a, b, r2 = linear_fit_loglog(rank_freq_data)
    print(f"[Zipf定律] log(freq) = {a:.4f} + {b:.4f} * log(rank)，R² = {r2:.4f}（理想斜率≈ -1）")

    write_csv(os.path.join(OUT_DIR, "zipf_cn_rank_freq.csv"),
              ["rank", "char", "frequency"],
              rank_freq_data)
    plot_zipf(rank_freq_data, "Zipf's Law (Chinese characters)",
              os.path.join(OUT_DIR, "zipf_cn_loglog.png"))

    # 扩容对比：累积文件数 vs 熵 & 斜率
    print("[INFO] 开始扩容分析 …")
    scaling_rows, xs, entropies, slopes = [], [], [], []
    cn_acc = []

    for i, p in enumerate(tqdm(files, desc="Scaling analysis", ncols=80), start=1):
        txt = read_text(p)
        cn = extract_chinese_chars(txt)
        if cn:
            cn_acc.append(cn)
        cn_counter_i = Counter("".join(cn_acc))
        _, _, h_i = probs_and_entropy(cn_counter_i)
        rf = rank_freq(cn_counter_i)
        _, slope_i, r2_i = linear_fit_loglog(rf)

        if (i % SCALING_STEP == 0) or (i == len(files)):
            scaling_rows.append([i, len(cn_counter_i), sum(cn_counter_i.values()), h_i, slope_i, r2_i])
            xs.append(i)
            entropies.append(h_i)
            slopes.append(slope_i)

    write_csv(os.path.join(OUT_DIR, "scaling_results.csv"),
              ["files_cumulative", "unique_chars", "total_chars", "entropy_bits", "zipf_slope", "zipf_r2"],
              scaling_rows)
    plot_scaling(xs, entropies, slopes, os.path.join(OUT_DIR, "scaling_entropy_slope.png"))

    print(f"[DONE] 结果已输出至 ./{OUT_DIR}/")
    print("  - cn_char_probabilities.csv：汉字概率与频次")
    print("  - zipf_cn_rank_freq.csv：齐夫定律排名与频率")
    print("  - zipf_cn_loglog.png：Zipf 双对数图")
    print("  - scaling_results.csv：扩容结果（熵与斜率）")
    print("  - scaling_entropy_slope.png：扩容分析图")

if __name__ == "__main__":
    main()
