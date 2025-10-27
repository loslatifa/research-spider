# analyze_data.py - 支持 n-gram（复合词）词频统计完整智能分析版（唯一图像目录版本）

import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
from wordcloud import WordCloud
from sklearn.feature_extraction.text import CountVectorizer

# 加载外部停用词
with open("research_stop_words.txt") as f:
    stop_words = set(line.strip() for line in f if line.strip())

figures_root = "figures"
os.makedirs(figures_root, exist_ok=True)

def get_all_csv_files():
    return sorted(glob.glob("data/**/*.csv", recursive=True), key=os.path.getmtime, reverse=True)

def smart_column_mapping(df):
    rename_map = {}
    for col in df.columns:
        col_lower = col.lower()
        if any(k in col_lower for k in ['quote_text', 'title', 'paragraph', 'text']):
            rename_map[col] = 'text'
        elif any(k in col_lower for k in ['author', 'authors']):
            rename_map[col] = 'authors'
        elif any(k in col_lower for k in ['tags', 'keywords', 'category']):
            rename_map[col] = 'tags'
    return df.rename(columns=rename_map)

def extract_ngrams_frequency(texts, ngram_range=(2, 3), top_k=30):
    vectorizer = CountVectorizer(stop_words=list(stop_words), ngram_range=ngram_range, max_features=1000)
    X = vectorizer.fit_transform(texts)
    freqs = zip(vectorizer.get_feature_names_out(), X.sum(axis=0).tolist()[0])
    return sorted(freqs, key=lambda x: x[1], reverse=True)[:top_k]

def analyze_csv(file_path):
    df = pd.read_csv(file_path)
    filename = os.path.basename(file_path).replace(".csv", "")
    domain = filename.split("_")[1] if "_" in filename else "general"
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

        wc = WordCloud(width=1000, height=500, background_color='white').generate_from_frequencies(dict(ngram_freq))
        plt.figure(figsize=(12, 6))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(os.path.join(fig_path, "ngram_wordcloud.png"))

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