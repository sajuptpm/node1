import openpyxl

wb = openpyxl.load_workbook("workflow-fixes/data1.xlsx", data_only=True)
ws = wb["nodejs"]

max_r = ws.max_row
max_c = ws.max_column

print(f"Sheet 'nodejs' max_row: {max_r}, max_column: {max_c}")

# Check headers
headers = [ws.cell(row=1, column=c).value for c in range(1, max_c + 1)]
print(f"Total headers: {len(headers)}")
print(f"Header 1: {headers[0]}")
print(f"Header 2: {headers[1]} (New Category column: Infra/Tool)")
print(f"Header 3: {headers[2]}")
print(f"Header 21: {headers[20]} (Pipeline Category)")

# Check for empty cells or anomalies
empty_counts = {c: 0 for c in range(1, max_c + 1)}
category_counts = {}

for r in range(2, max_r + 1):
    cat_val = ws.cell(row=r, column=2).value
    category_counts[cat_val] = category_counts.get(cat_val, 0) + 1
    
    for c in range(1, max_c + 1):
        val = ws.cell(row=r, column=c).value
        if val is None or str(val).strip() == "":
            empty_counts[c] += 1

empty_cols = {headers[c-1]: empty_counts[c] for c in range(1, max_c + 1) if empty_counts[c] > 0}
print(f"\nColumns with empty values: {empty_cols}")
print(f"\nCategory (Infra / Tool) Breakdown: {category_counts}")

# Analysis for List 1: Purchase Orders / Quotes / Paid / Blocked
po_rows = []
free_rows = []
tool_summary = {}

for r in range(2, max_r + 1):
    tool = ws.cell(row=r, column=1).value
    category = ws.cell(row=r, column=2).value
    rec_type = ws.cell(row=r, column=5).value
    paid_status = ws.cell(row=r, column=9).value
    blocked = ws.cell(row=r, column=10).value
    spdx = ws.cell(row=r, column=12).value
    copyleft = ws.cell(row=r, column=13).value
    redist = ws.cell(row=r, column=14).value
    verdict = ws.cell(row=r, column=17).value
    pipe = ws.cell(row=r, column=23).value
    yml = ws.cell(row=r, column=24).value
    req_purchase = ws.cell(row=r, column=30).value
    price_link = ws.cell(row=r, column=37).value
    best_alt = ws.cell(row=r, column=41).value
    evidence = ws.cell(row=r, column=45).value
    
    tool_summary[(tool, category)] = tool_summary.get((tool, category), 0) + 1
    
    # List 1: Purchase Orders, Vendor Quotes, Paid items, or Blocked Upstream infra
    if (str(req_purchase).startswith("Yes") or 
        "paid" in str(paid_status).lower() or 
        str(blocked).startswith("Yes")):
        po_rows.append((r, pipe, yml, tool, category, rec_type, paid_status, req_purchase, blocked, price_link, best_alt))
    
    # List 2: Free and open-source tools for legal compliance
    if "free" in str(paid_status).lower():
        free_rows.append((r, pipe, yml, tool, category, rec_type, spdx, copyleft, redist, verdict))

print(f"\n========================================================")
print(f"LIST 1: CANDIDATES FOR PURCHASE ORDERS / VENDOR QUOTES / BLOCKED UPSTREAM INFRA")
print(f"Total matching rows: {len(po_rows)}")
print(f"========================================================")
seen_po_tools = set()
for r, pipe, yml, tool, category, rec_type, paid_status, req_purchase, blocked, price_link, best_alt in po_rows:
    if tool not in seen_po_tools:
        print(f"Tool: {tool[:33]:33} | Category: {category:5} | Paid: {paid_status[:20]:20} | Req PO: {req_purchase[:22]:22}")
        seen_po_tools.add(tool)

print(f"\n========================================================")
print(f"LIST 2: FREE & OPEN SOURCE TOOLS FOR LEGAL COMPLIANCE")
print(f"Total matching rows: {len(free_rows)}")
print(f"========================================================")
seen_free_tools = set()
for r, pipe, yml, tool, category, rec_type, spdx, copyleft, redist, verdict in free_rows:
    if tool not in seen_free_tools:
        print(f"Tool: {tool[:30]:30} | Cat: {category:5} | SPDX: {spdx[:15]:15} | Copyleft: {copyleft[:15]:15} | Verdict: {verdict[:15]:15}")
        seen_free_tools.add(tool)

print(f"\n========================================================")
print(f"ALL 21 UNIQUE TOOLS BREAKDOWN (Total: {sum(tool_summary.values())} rows)")
print(f"========================================================")
for (t, cat), cnt in sorted(tool_summary.items(), key=lambda x: -x[1]):
    print(f"{t:42}: [{cat:5}] {cnt:3} rows")
