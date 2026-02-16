import sqlite3
import csv
import os

DB_PATH = "/Users/milo/Desktop/BNP_BDD/hobart.db"

def analyze_desk_retention():
    print("--- Analyzing Desk Retention (Initial vs. Final) ---")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return

    # 1. Get Final Desk and Status from SR
    print("Fetching Final Desk data from SR table...")
    query_sr = """
    SELECT 
        id, 
        jur_desk_id,
        status_id -- To verify closure if needed, but we rely on closingdate
    FROM sr 
    WHERE closingdate IS NOT NULL
    """
    
    try:
        cursor.execute(query_sr)
        # Store as dict: {sr_id: final_desk_id}
        final_desks = {row[0]: row[1] for row in cursor.fetchall()}
    except sqlite3.Error as e:
        print(f"Error querying SR table: {e}")
        conn.close()
        return

    print(f"Loaded {len(final_desks)} closed tickets.")

    # 2. Get Initial Desk from Activity Table
    # We want the FIRST activity for each SR.
    # We will order by creationdate to ensure we get the first one.
    print("Fetching Initial Desk data from Activity table...")
    
    # Note: We select rows and then filter in python to find the first one per SR
    # because doing "GROUP BY sr_id HAVING MIN(creationdate)" is complex with getting other columns in SQLite
    # without window functions (though SQLite supports them, safe to do in python for clarity).
    # We order by sr_id and creationdate.
    
    query_activity = """
    SELECT 
        sr_id,
        jur_assignedgroup_id,
        creator_desk_id
    FROM activity 
    ORDER BY creationdate ASC
    """
    
    initial_desks = {}
    
    try:
        cursor.execute(query_activity)
        
        # Cursor.description can help if we use row factory, but here we know indices:
        # 0: sr_id, 1: jur_assignedgroup_id, 2: creator_desk_id
        
        count = 0
        for row in cursor:
            sr_id = row[0]
            assigned_group = row[1]
            creator_desk = row[2]
            
            # Since we ordered by Date (implicitly or explicitly if added), 
            # The FIRST time we see an SR_ID, it is the EARLIEST activity.
            # However, my query above sorts by creationdate globally, not per SR.
            # This is fine. We iterate through time. The first time we encounter an SR, that's its birth.
            
            if sr_id not in initial_desks:
                # Use assigned group if available, else creator desk
                initial_desk = assigned_group if assigned_group else creator_desk
                initial_desks[sr_id] = initial_desk
                
            count += 1
            if count % 100000 == 0:
                print(f"Processed {count} activity rows...", end='\r')
                
    except sqlite3.Error as e:
        print(f"Error querying Activity table: {e}")
        conn.close()
        return
        
    conn.close()
    print(f"\nIdentified initial desks for {len(initial_desks)} tickets.")
    
    # 3. Compare
    print("Comparing Initial vs. Final...")
    common_ids = set(final_desks.keys()) & set(initial_desks.keys())
    
    if not common_ids:
        print("No intersecting data found.")
        return
        
    total_analyzed = len(common_ids)
    same_desk_count = 0
    
    for sr_id in common_ids:
        initial = initial_desks[sr_id]
        final = final_desks[sr_id]
        
        # Handle potential None values
        if initial is None or final is None:
            continue
            
        # Ensure types match (int vs str)
        if str(initial) == str(final):
            same_desk_count += 1
            
    retention_rate = (same_desk_count / total_analyzed) * 100 if total_analyzed > 0 else 0
    
    print(f"Total Closed Tickets with History: {total_analyzed}")
    print(f"Tickets Solved by Initial Desk: {same_desk_count}")
    print(f"Retention Rate: {retention_rate:.2f}%")
    
    # Save report
    # Save in the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(script_dir, "desk_retention_report.txt")
    
    with open(report_path, "w") as f:
        f.write("DESK RETENTION ANALYSIS\n")
        f.write("-----------------------\n")
        f.write(f"Definition: Percentage of tickets where the Creation Desk is the same as the Closing Desk.\n\n")
        f.write(f"Total Closed Tickets Analyzed: {total_analyzed}\n")
        f.write(f"Tickets Solved by Initial Desk: {same_desk_count}\n")
        f.write(f"Retention Rate: {retention_rate:.2f}%\n")
        
    print(f"Report saved to {report_path}")

if __name__ == "__main__":
    analyze_desk_retention()
