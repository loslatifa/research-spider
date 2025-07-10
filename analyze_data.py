# analyze_data.py - 双模式（自动 / 手动选择列）科研数据分析脚本

import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import os
import glob
from wordcloud import WordCloud

figures_path = "figures"
os.makedirs(figures_path, exist_ok=True)

# 内置英文停用词
stop_words = set([
    'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'with', 'without', 'by', 'of', 'and', 'or', 'but', 'so', 'if', 'then', 'than',
    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'their', 'our', 'is', 'are', 'was', 'were', 'be', 'been', 'am', 'this', 'that', 'these', 'those', 'as', 'from', 'up', 'down', 'out', 'about', 'into', 'over', 'under', 'again', 'further', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'too', 'very', 'can', 'will', 'just', 'should', 'now'
])

def get_latest_csv():
    csv_files = sorted(glob.glob("data/result_*.csv"), key=os.path.getmtime, reverse=True)
    if not csv_files:
        print("❌ No CSV files found in data/ folder.")
        exit()
    return csv_files[0]

def analyze_csv(file_path, selected_columns=None):
    print(f"\n📊 Analyzing: {file_path}")
    df = pd.read_csv(file_path)
    print(f"✅ Loaded CSV with shape: {df.shape}\n")
    print("Columns:", df.columns.tolist())

    if selected_columns is None:
        text_cols = []
        cat_cols = []
        for col in df.columns:
            col_lower = col.lower()
            if any(key in col_lower for key in ["text", "paragraph", "quote"]):
                text_cols.append(col)
            elif any(key in col_lower for key in ["author", "tags", "category"]):
                cat_cols.append(col)
        selected_columns = text_cols + cat_cols
        if not selected_columns:
            text_lengths = df.select_dtypes(include='object').apply(lambda x: x.str.len().mean())
            selected_columns = [text_lengths.idxmax()]

    print(f"\nUsing columns for analysis: {selected_columns}")

    combined_text = []
    for col in selected_columns:
        combined_text.extend(df[col].dropna().astype(str).tolist())

    words = []
    for text in combined_text:
        words.extend(text.split())

    filtered_words = [w.lower().strip(',.!"\'()') for w in words if len(w) > 2 and w.lower() not in stop_words]
    counter = Counter(filtered_words)
    most_common = counter.most_common(20)

    if most_common:
        words_, counts = zip(*most_common)
        plt.figure(figsize=(12, 6))
        plt.bar(words_, counts)
        plt.title("Top 20 Word Frequency (Filtered)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        bar_path = os.path.join(figures_path, "word_frequency_bar.png")
        plt.savefig(bar_path)
        print(f"✅ Saved bar chart to {bar_path}")

        wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(counter)
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        wc_path = os.path.join(figures_path, "wordcloud.png")
        plt.savefig(wc_path)
        print(f"✅ Saved word cloud to {wc_path}")
    else:
        print("⚠️ No valid words found for word frequency analysis.")

    for col in selected_columns:
        cat_counts = df[col].value_counts().head(20)
        if cat_counts.nunique() > 1:
            plt.figure(figsize=(12, 6))
            cat_counts.plot(kind='bar')
            plt.title(f"Top Categories in '{col}'")
            plt.ylabel("Count")
            plt.xticks(rotation=45)
            plt.tight_layout()
            cat_path = os.path.join(figures_path, f"category_distribution_{col}.png")
            plt.savefig(cat_path)
            print(f"✅ Saved category distribution chart to {cat_path}")

if __name__ == "__main__":
    csv_file = get_latest_csv()
    df_temp = pd.read_csv(csv_file)
    print("\n请选择分析模式：\n1) 自动模式（推荐快速分析）\n2) 手动选择列分析")
    mode = input("输入 1 或 2: ").strip()

    if mode == '2':
        print("\n可选列：")
        for idx, col in enumerate(df_temp.columns):
            print(f"{idx+1}: {col}")
        selected_indices = []
        while True:
            sel = input("输入要选择列的编号（输入 n 完成选择）： ").strip()
            if sel.lower() == 'n':
                break
            if sel.isdigit() and 1 <= int(sel) <= len(df_temp.columns):
                selected_indices.append(int(sel)-1)
            else:
                print("⚠️ 输入无效，请重新输入。")
        selected_columns = [df_temp.columns[i] for i in selected_indices]
        analyze_csv(csv_file, selected_columns)
    else:
        analyze_csv(csv_file)

    print("\n🎉 Analysis completed. Figures saved in figures/ folder.")