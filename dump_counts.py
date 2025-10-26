import sqlite3
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
outfile = os.path.join(base_dir, 'counts.txt')
db_path = os.path.join(base_dir, 'mtdl_pcm.db')

conn = sqlite3.connect(db_path)
c = conn.cursor()

rows = []
rows.append(f"equipments={c.execute('select count(*) from equipments').fetchone()[0]}")
rows.append(f"materials={c.execute('select count(*) from materials').fetchone()[0]}")
rows.append(f"plans={c.execute('select count(*) from maintenance_plans').fetchone()[0]}")
rows.append(f"plan_actions={c.execute('select count(*) from maintenance_plan_actions').fetchone()[0]}")
rows.append(f"plan_materials={c.execute('select count(*) from maintenance_plan_materials').fetchone()[0]}")
rows.append(f"work_orders_preventive={c.execute("select count(*) from work_orders where type='Preventiva'").fetchone()[0]}")

conn.close()

with open(outfile, 'w', encoding='utf-8') as f:
    for r in rows:
        f.write(r + '\n')

print('\n'.join(rows))