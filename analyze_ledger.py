# Let's check the differences and check every page
# Why does Bijoy Excel have errors?
# 1. Bijoy 52 / SutonnyMJ text encoding:
#    In Excel, typing in SutonnyMJ replaces English letters visually with Bengali glyphs,
#    e.g. "Gm wm Avi Gg" -> "এসসিআরএম", "10 wg: wj:" -> "১০ মি.মি". When imported, it reads as raw English characters!
# 2. Date typos in Excel:
#    e.g. Page 1: 1/2/2024 (should be 1/2/2025 because it's after 12/31/2024!)
#    e.g. Page 6: 1/10/1902 (Excel serial number error! Someone entered a date or formula wrong, showing year 1902!)
#    e.g. Page 6: 1/8/2026 appears after 2/7/2026!
# 3. Sum / Calculation differences:
#    Let's check every line total = qty * rate, vs the printed UvKv (টাকা) column.

print("Analyzing ledger inconsistencies...")
