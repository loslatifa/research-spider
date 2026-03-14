# analyze_data.py - 支持 n-gram（复合词）词频统计完整智能分析版（唯一图像目录版本）

import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
try:
    from wordcloud import WordCloud
    HAVE_WORDCLOUD = True
except Exception:
    HAVE_WORDCLOUD = False
from sklearn.feature_extraction.text import CountVectorizer

# 加载外部停用词
with open("research_stop_words.txt") as f:
    stop_words = set(line.strip() for line in f if line.strip())

figures_root = "figures"
os.makedirs(figures_root, exist_ok=True)


def infer_domain_from_filename(filename: str) -> str:
    # 支持:
    # - result_<domain>_<YYYYMMDD>.csv
    # - result_<domain>_<YYYYMMDD>_<kw>.csv
    # - master_<domain>.csv
    base = filename.replace(".csv", "")
    parts = base.split("_")
    if not parts:
        return "general"
    if parts[0] in ("result", "master") and len(parts) >= 2:
        return parts[1]
    return "general"


def get_all_csv_files():
    return sorted(glob.glob("data/**/*.csv", recursive=True), key=os.path.getmtime, reverse=True)

def smart_column_mapping(df):
    # SCHEMA_AWARE_MAPPING: 将多种可能的文本/作者/标签列归并为单一列，避免重复列名导致 DataFrame 被当作多列
    df = df.copy()

    def merge_columns(col_matchers, target_name):
        cols = [c for c in df.columns if any(k in c.lower() for k in col_matchers)]
        if not cols:
            return
        # 如果只有一个列且已经是目标名，则无需合并
        if len(cols) == 1 and cols[0] == target_name:
            return
        # 将多个候选列合并为一列（按空格连接），并删除原列（保留已命名的目标列）
        df[target_name] = df[cols].fillna('').astype(str).agg(' '.join, axis=1).str.strip()
        for c in cols:
            if c != target_name:
                try:
                    df.drop(columns=c, inplace=True)
                except Exception:
                    pass

    merge_columns(['quote_text', 'title', 'paragraph', 'abstract', 'summary', 'text'], 'text')
    merge_columns(['author', 'authors'], 'authors')
    merge_columns(['tags', 'keywords', 'category', 'topic'], 'tags')

    return df

def extract_ngrams_frequency(texts, ngram_range=(2, 3), top_k=30):
    vectorizer = CountVectorizer(stop_words=list(stop_words), ngram_range=ngram_range, max_features=1000)
    X = vectorizer.fit_transform(texts)
    freqs = zip(vectorizer.get_feature_names_out(), X.sum(axis=0).tolist()[0])
    return sorted(freqs, key=lambda x: x[1], reverse=True)[:top_k]

def analyze_csv(file_path):
    df = pd.read_csv(file_path)
    filename = os.path.basename(file_path).replace(".csv", "")
    domain = infer_domain_from_filename(filename)
    fig_path = os.path.join(figures_root, domain, filename)
    os.makedirs(fig_path, exist_ok=True)

    # 如果已存在分析结果则跳过
    already_done = os.path.exists(os.path.join(fig_path, "ngram_wordcloud.png"))
    if already_done:
        print(f"⚠️ {filename} 已分析，跳过。")
        return

    df = smart_column_mapping(df)
    
    texts = df['text'].dropna().astype(str).tolist() if 'text' in df.columns else []
    tags = df['tags'].dropna().astype(str).tolist() if 'tags' in df.columns else []
    combined_text = texts + tags

    if not combined_text:
        print(f"❌ {filename} 中无可分析文本。")
        return

    ngram_freq = extract_ngrams_frequency(combined_text, ngram_range=(2, 3), top_k=30)

    if ngram_freq:
        ngrams_, counts = zip(*ngram_freq)
        plt.figure(figsize=(14, 7))
        plt.bar(ngrams_, counts)
        plt.title("Top 30 N-gram (2-3) Frequency")
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(fig_path, "ngram_frequency_bar.png"))

        if HAVE_WORDCLOUD:
            wc = WordCloud(width=1000, height=500, background_color='white').generate_from_frequencies(dict(ngram_freq))
            plt.figure(figsize=(12, 6))
            plt.imshow(wc, interpolation='bilinear')
            plt.axis('off')
            plt.tight_layout()
            plt.savefig(os.path.join(fig_path, "ngram_wordcloud.png"))
        else:
            print("⚠️ wordcloud 未安装，已跳过词云生成。可运行 `pip install wordcloud` 以启用此功能。")

        ngram_df = pd.DataFrame(ngram_freq, columns=['ngram', 'count'])
        ngram_df.to_csv(os.path.join(fig_path, "ngram_frequency_table.csv"), index=False)

        print(f"✅ 分析完成: {filename}，结果保存至 {fig_path}")
    else:
        print(f"⚠️ 未生成有效的 n-gram: {filename}")

if __name__ == "__main__":
    files = get_all_csv_files()
    if not files:
        print("❌ data 文件夹中无 CSV 文件。")
    else:
        for file in files:
            analyze_csv(file)
