import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime

# Construct absolute path to DB
BASE_DIR = "/Users/milo/Desktop/BNP_BDD"
DB_PATH = os.path.join(BASE_DIR, "hobart.db")

def analyze_resolution_time():
    conn = sqlite3.connect(DB_PATH)
    
    print("--- Analyzing Resolution Time by Category ---")
    
    query = """
    SELECT 
        s.id,
        s.creationdate_parsed,
        s.closingdate_parsed,
        c.name as category_name
    FROM sr s
    LEFT JOIN category c ON s.category_id = c.original_id
    WHERE s.closingdate_parsed IS NOT NULL 
      AND s.creationdate_parsed IS NOT NULL
      AND c.name IS NOT NULL;
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
    
    # Filter Outliers
    df = df[~df['category_name'].isin(['Statements', 'Connexis'])]
    
    # Aggregation
    category_perf = df.groupby('category_name')['duration_days'].mean().reset_index()
    category_perf = category_perf.sort_values(by='duration_days', ascending=False) # Slowest first
    
    # --- Presentation Chart: Top 30 Slowest (Cleaned) ---
    top_30 = category_perf.head(30)
    
    plt.figure(figsize=(14, 12)) 
    sns.set_theme(style="whitegrid")
    
    barplot = sns.barplot(
        data=top_30,
        x='duration_days',
        y='category_name',
        palette='magma' 
    )
    
    plt.title('Top 30 Slowest Categories (Excluding Outliers)', fontsize=20, fontweight='bold')
    plt.xlabel('Average Days to Resolve', fontsize=16)
    plt.ylabel('', fontsize=16) # Remove label for cleaner look
    plt.yticks(fontsize=14)
    plt.xticks(fontsize=12)
    
    sns.despine(left=True, bottom=True)
    
    # Add values
    for i, v in enumerate(top_30['duration_days']):
        barplot.text(v + 1, i, f"{v:.0f}d", color='black', va='center', fontweight='bold', fontsize=12)

    plt.tight_layout()
    output_path = "analysis/resolution_time_presentation.png"
    plt.savefig(output_path, dpi=300)
    print(f"Presentation Chart saved to {output_path}")

if __name__ == "__main__":
    analyze_resolution_time()
