# analyze_data.py - 自动检索当前文件夹及子文件夹中最新 CSV 文件，支持 n-gram 分析

import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
from wordcloud import WordCloud
from sklearn.feature_extraction.text import CountVectorizer

with open("research_stop_words.txt") as f:
    stop_words = set(line.strip() for line in f if line.strip())

figures_root = "figures"
os.makedirs(figures_root, exist_ok=True)

def get_latest_csv():
    files = sorted(glob.glob("data/**/*.csv", recursive=True), key=os.path.getmtime, reverse=True)
    return files[0] if files else None

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
    filename = os.path.basename(file_path)
    domain = filename.split("_")[1] if "_" in filename else "general"
    fig_path = os.path.join(figures_root, domain)
    os.makedirs(fig_path, exist_ok=True)

    df = smart_column_mapping(df)
    
    texts = df['text'].dropna().astype(str).tolist() if 'text' in df.columns else []
    tags = df['tags'].dropna().astype(str).tolist() if 'tags' in df.columns else []
    combined_text = texts + tags

    if not combined_text:
        print("❌ No text data found for analysis.")
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

        print(f"✅ N-gram figures and frequency table saved under {fig_path}")
    else:
        print("⚠️ No valid n-grams found for visualization.")

if __name__ == "__main__":
    csv_files = sorted(glob.glob("data/**/*.csv", recursive=True))
    analyzed = 0
    skipped = 0

    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        domain = filename.split("_")[0] if "_" in filename else "general"
        fig_path = os.path.join(figures_root, domain)

        # 检查是否已有图像（即已分析）
        wordcloud_path = os.path.join(fig_path, "ngram_wordcloud.png")
        if os.path.exists(wordcloud_path):
            print(f"⏭️ 已存在分析图像，跳过：{filename}")
            skipped += 1
            continue

        print(f"\n📊 正在分析：{filename}")
        analyze_csv(csv_file)
        analyzed += 1

    print(f"\n✅ 共分析新文件 {analyzed} 个，跳过已存在图像的 {skipped} 个。")