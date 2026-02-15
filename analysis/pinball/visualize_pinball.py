import sqlite3
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import os
import matplotlib.cm as cm

# Construct absolute path to DB
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "hobart.db")

def visualize_journey(sr_id):
    conn = sqlite3.connect(DB_PATH)
    
    print(f"Visualizing journey for SR: {sr_id}")
    query = f"""
    SELECT 
        a.creationdate,
        a.jur_assignedgroup_id,
        a.creator_desk_id
    FROM activity a
    WHERE a.sr_id = {sr_id}
    ORDER BY a.creationdate ASC;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("No activities found.")
        return

    # --- 1. Data Processing (Desks Only) ---
    all_desks = set()
    path_sequence = [] # List of Desk IDs
    
    path_sequence.append("Client")
    
    for index, row in df.iterrows():
        desk_id = row['jur_assignedgroup_id']
        if pd.isna(desk_id):
            desk_id = row['creator_desk_id'] 
        
        if pd.isna(desk_id):
            continue
            
        desk_id = str(int(desk_id)) # Use string ID
        all_desks.add(desk_id)
        
        # Add to path if different from previous step?
        # User wants to see direction. 
        # If Desk A -> Desk A (internal churn), should we show it?
        # Yes, as a self-loop, to show "Stuckness".
        
        path_sequence.append(desk_id)

    # --- 2. Build Layout (Linear Left-to-Right) ---
    G = nx.DiGraph()
    pos = {}
    labels = {}
    
    # 2a. Determine Order of First Appearance
    desk_order = []
    seen_desks = set()
    
    # Client first
    desk_order.append("Client")
    seen_desks.add("Client")
    
    for desk_id in path_sequence:
        if desk_id not in seen_desks:
             desk_order.append(desk_id)
             seen_desks.add(desk_id)
             
    # 2b. Position Nodes linearly
    # Spacing - Increased for better separation
    x_spacing = 8.0
    
    for i, desk_id in enumerate(desk_order):
        x = i * x_spacing
        y = 0 
        
        G.add_node(desk_id)
        pos[desk_id] = (x, 0)
        
        if desk_id == "Client":
            labels[desk_id] = "CLIENT"
        else:
            labels[desk_id] = f"Desk\n{desk_id}"

    # --- 3. Draw ---
    plt.figure(figsize=(24, 10))
    ax = plt.gca()
    
    # Draw Nodes
    # Client
    nx.draw_networkx_nodes(G, pos, nodelist=["Client"], node_size=5000, 
                           node_color='#FFD700', edgecolors='orange', linewidths=4)
    
    # Desks
    # Color map for desks
    desk_colors = [hash(n) % 20 for n in desk_order if n != "Client"]
    # Filter 'Client' out of desk_order for this specific draw call as Client is drawn separately
    real_desks = [d for d in desk_order if d != "Client"]
    
    nx.draw_networkx_nodes(G, pos, nodelist=real_desks, node_size=7000, 
                           node_color=desk_colors, cmap=plt.cm.Pastel1, 
                           edgecolors='#555555', linewidths=3)
    
    # Labels
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=12, font_weight='bold', font_color='#333333')

    # Draw Flow Arrows
    import matplotlib.colors as mcolors
    cmap = plt.get_cmap('plasma')
    
    for k in range(len(path_sequence) - 1):
        u = path_sequence[k]
        v = path_sequence[k+1]
        
        # Color based on time
        progress = k / (len(path_sequence) - 1)
        edge_color = cmap(progress)
        
        if u == v:
            continue
            
        # Curvature
        # A -> B (Forward): Curve "South" (rad positive or negative depending on layout)
        # B -> A (Backward): Curve "North" 
        
        # Determine direction
        try:
            u_idx = desk_order.index(u)
            v_idx = desk_order.index(v)
        except ValueError:
            continue
            
        if v_idx > u_idx:
            # Forward: Top Curve? Or Bottom?
            # Let's do Bottom Curve for Forward, Top for Backward?
            # rad = -0.3
            connection_style = "arc3,rad=-0.4" 
        else:
            # Backward
            connection_style = "arc3,rad=-0.4"
            
        # Actually proper arc logic:
        # rad > 0 is right-handed. 
        # If u=(0,0), v=(1,0). rad=0.5 -> center is at (0.5, -y) -> Curves "down/right".
        
        ax.annotate("",
                    xy=pos[v], xycoords='data',
                    xytext=pos[u], textcoords='data',
                    arrowprops=dict(arrowstyle="-|>", color=edge_color, 
                                    connectionstyle=connection_style, 
                                    linewidth=3, alpha=0.6,
                                    shrinkA=25, shrinkB=25, mutation_scale=20)
                   )

    plt.title(f"The Pinball Effect (Timeline View)\nTicket #{sr_id}", fontsize=20, fontweight='bold', pad=20)
    plt.axis('off')
    
    plt.figtext(0.5, 0.02, "Arrow Color: Purple (Start) -> Yellow (Finish)", ha="center", fontsize=12, style='italic', bbox=dict(facecolor='white', alpha=0.8, pad=0.5))

    output_path = f"pinball_linear_{sr_id}.png"
    plt.savefig(output_path, format="PNG", dpi=300, bbox_inches='tight')
    print(f"Graph saved to {output_path}")

if __name__ == "__main__":
    visualize_journey(1405635)
