import os
import pandas as pd
from datetime import datetime, timezone

from app import create_app
from app.models import EchoCounts, db

# Directory containing CSV files
CSV_DIR = 'csv'

app, _ = create_app()

def migrate_csv_to_db():
    with app.app_context():
        for root, dirs, files in os.walk(CSV_DIR):
            for filename in files:
                if filename.endswith('.csv'):
                    site_name = os.path.splitext(filename)[0]  # e.g., 'cly' from 'cly.csv'
                    filepath = os.path.join(root, filename)
                    df = pd.read_csv(filepath)

                    # Ensure Timestamp is parsed as datetime
                    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')

                    # Group by Scan (one scan = all rows until Scan==1, or group by Scan column if that's unique)
                    scan_groups = df.groupby((df['Scan'] == 1).cumsum())

                    for _, group in scan_groups:
                        if group.empty:
                            continue
                        # Use the last timestamp in the group as the scan timestamp
                        timestamp = group['Timestamp'].max()
                        # Compute averages
                        total_echoes = int(group['Num_Echoes'].mean())
                        iono_echoes = int(group['Num_Ionosph_Echoes'].mean())
                        gs_echoes = int(group['Num_Gnd_sctr_Echoes'].mean())

                        echo = EchoCounts(
                            site_name=site_name,
                            timestamp=timestamp if pd.notnull(timestamp) else datetime.now(timezone.utc),
                            total_echoes=total_echoes,
                            ionospheric_echoes=iono_echoes,
                            ground_scatter_echoes=gs_echoes
                        )
                        db.session.add(echo)
                    db.session.commit()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_csv_to_db()