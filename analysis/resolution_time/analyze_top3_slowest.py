import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Construct absolute path to DB
BASE_DIR = "/Users/milo/Desktop/BNP_BDD"
DB_PATH = os.path.join(BASE_DIR, "hobart.db")

def analyze_top3_slowest():
    conn = sqlite3.connect(DB_PATH)
    
    print("--- Deep Dive: Top 3 Slowest Categories ---")
    
    # Target Categories
    target_categories = ['Statements', 'Connexis', 'Loan']
    
    query = f"""
    SELECT 
        s.id as sr_id,
        s.creationdate_parsed,
        s.closingdate_parsed,
        c.name as category_name
    FROM sr s
    LEFT JOIN category c ON s.category_id = c.original_id
    WHERE s.closingdate_parsed IS NOT NULL 
      AND s.creationdate_parsed IS NOT NULL
      AND c.name IN ({','.join(["'" + c + "'" for c in target_categories])});
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("No data found.")
        return

    # Parse Dates
    def parse_date(date_str):
        try:
            return pd.to_datetime(date_str, format='%y-%m-%d %H.%M.%S')
        except:
            return pd.NaT

    df['start'] = df['creationdate_parsed'].apply(parse_date)
    df['end'] = df['closingdate_parsed'].apply(parse_date)
    
    df = df.dropna(subset=['start', 'end'])
    df['duration_days'] = (df['end'] - df['start']).dt.total_seconds() / (24 * 3600)
    df = df[df['duration_days'] >= 0]
    
    # 1. Detailed Statistics
    print("\n--- Detailed Statistics ---")
    stats = df.groupby('category_name')['duration_days'].describe(percentiles=[0.25, 0.5, 0.75, 0.90, 0.95])
    print(stats)
    
    # Save stats to markdown
    stats.to_markdown("analysis/top3_stats.md")
    
    # 2. Outlier Analysis (Top 5 Slowest per Category)
    print("\n--- Top 5 Slowest Tickets per Category ---")
    for cat in target_categories:
        print(f"\nCategory: {cat}")
        cat_df = df[df['category_name'] == cat].sort_values(by='duration_days', ascending=False).head(5)
        print(cat_df[['sr_id', 'start', 'end', 'duration_days']])

    # 3. Visualization: Boxplot & Strip Plot
    plt.figure(figsize=(12, 8))
    sns.set_theme(style="whitegrid")
    
    # Boxplot to show distribution and median
    sns.boxplot(x='category_name', y='duration_days', data=df, showfliers=False, palette="Set2")
    
    # Strip plot to show actual data points (jittered)
    sns.stripplot(x='category_name', y='duration_days', data=df, color=".25", alpha=0.5, jitter=True)
    
    plt.title('Deep Dive: Distribution of Resolution Time (Top 3 Slowest)', fontsize=16, fontweight='bold')
    plt.ylabel('Days to Resolve', fontsize=12)
    plt.xlabel('Category', fontsize=12)
    
    output_path = "analysis/top3_slowest_distribution.png"
    plt.savefig(output_path, dpi=300)
    print(f"\nDistribution Chart saved to {output_path}")

if __name__ == "__main__":
    analyze_top3_slowest()
