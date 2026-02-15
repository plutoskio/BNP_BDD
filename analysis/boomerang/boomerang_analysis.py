import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Construct absolute path to DB
BASE_DIR = "/Users/milo/Desktop/BNP_BDD"
DB_PATH = os.path.join(BASE_DIR, "hobart.db")

def analyze_boomerang():
    conn = sqlite3.connect(DB_PATH)
    
    print("--- Analyzing Boomerang Rate (Re-opens) ---")
    
    # We need:
    # 1. Total tickets per Category
    # 2. Tickets with reopen_date_parsed IS NOT NULL per Category
    
    query = """
    SELECT 
        s.id,
        c.name as category_name,
        CASE WHEN s.reopen_date_parsed IS NOT NULL THEN 1 ELSE 0 END as is_boomerang
    FROM sr s
    LEFT JOIN category c ON s.category_id = c.original_id
    WHERE c.name IS NOT NULL;
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("No data found.")
        return

    # --- 1. Global Stats ---
    total_tickets = len(df)
    total_boomerangs = df['is_boomerang'].sum()
    global_rate = (total_boomerangs / total_tickets) * 100
    
    print(f"Global Boomerang Rate: {global_rate:.2f}% ({total_boomerangs}/{total_tickets})")
    
    # --- 2. Rate by Category ---
    cat_stats = df.groupby('category_name').agg(
        total=('id', 'count'),
        boomerangs=('is_boomerang', 'sum')
    ).reset_index()
    
    cat_stats['boomerang_rate'] = (cat_stats['boomerangs'] / cat_stats['total']) * 100
    
    # Filter for significant volume (> 50 tickets) to avoid noise
    cat_stats = cat_stats[cat_stats['total'] > 50]
    cat_stats = cat_stats.sort_values(by='boomerang_rate', ascending=False)
    
    # Top 20 Categories for Chart
    top_20 = cat_stats.head(20)
    
    # --- Visualization: Boomerang Rate Bar Chart ---
    plt.figure(figsize=(12, 10))
    sns.set_theme(style="whitegrid")
    
    barplot = sns.barplot(
        data=top_20,
        x='boomerang_rate',
        y='category_name',
        palette='rocket' # Intense colors for "danger"
    )
    
    plt.title('Top 20 Categories by Re-open Rate (Boomerang Effect)', fontsize=18, fontweight='bold')
    plt.xlabel('Re-open Rate (%)', fontsize=14)
    plt.ylabel('', fontsize=14)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    
    # Add values
    for i, v in enumerate(top_20['boomerang_rate']):
        barplot.text(v + 0.5, i, f"{v:.1f}%", color='black', va='center', fontweight='bold')

    plt.tight_layout()
    output_path = "analysis/boomerang/boomerang_rate_by_category.png"
    plt.savefig(output_path, dpi=300)
    print(f"Chart saved to {output_path}")
    
    # --- Save Stats ---
    with open("analysis/boomerang/boomerang_stats.md", "w") as f:
        f.write(f"# Boomerang Analysis\n\n")
        f.write(f"**Global Rate:** {global_rate:.2f}%\n\n")
        f.write(f"## Top Categories (High Failure Rate)\n")
        f.write(top_20.to_markdown(index=False))

if __name__ == "__main__":
    analyze_boomerang()
