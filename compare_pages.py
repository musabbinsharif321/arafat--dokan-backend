# Let's inspect all rows in pages 11, 12, 13, 14, 15, 16 vs sqlite!
# Let's see: in sqlite, what are all transactions?
import json

with open('sqlite_party18_dump.json', 'r', encoding='utf-8') as f:
    txs = json.load(f)

print(f"Total transactions in sqlite: {len(txs)}")
# Let's check all dates and amounts
for i, t in enumerate(txs):
    # Print date and total
    items_summary = ", ".join([f"{it[0]} ({it[1]}x{it[2]}={it[4]})" for it in t['items']])
    if t['type'] == 'sale':
        # print first 5 and last 5
        pass

print("Done")
