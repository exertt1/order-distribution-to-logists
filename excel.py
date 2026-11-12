from openpyxl import load_workbook

def read_excel_to_dicts(file_path: str):
    results_list = []

    wb = load_workbook(filename=file_path, data_only=True)

    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))

    if not rows:
        return []

    headers = [str(h).strip() for h in rows[0]]

    data_rows = rows[1:]

    for row in data_rows:
        if all(cell is None for cell in row):
            continue

        record = dict(zip(headers, row))

        results_list.append(record)

    return results_list