import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import pytz

OUTPUT_HTML = "summary_classification.html"

FAVORITES = ['Pinto', 'Correia', 'Lopes', 'Rodrigues', 'Vitor', 'Barbosa', 'Francisco', 'Nicolas', 'Fotios', 'Andrii', 'BEREZNOWSKA', 'Carmen, 'Simen', 'Jandosa']

def summary_classification():
    url = "https://live.breizhchrono.com/types/generic/custo/x.running/findInResults.jsp"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "https://live.breizhchrono.com/external/live5/classements.jsp?reference=1384568432549-14",
        "Origin": "https://live.breizhchrono.com",
    }

    payload_base = {
        "inter": "",
        "search": "",
        "ville": "",
        "course": "24h",
        "sexe": "",
        "category": "",
        "reference": "1384568432549-14",
        "from": "null",
        "nofacebook": "1",
        "version": "v6",
    }

    all_rows = []
    page = 0
    expected_headers = ["Clsmt.", "Nom & Prénom", "Nombre de passages", "Heure dernier passage", "Distance"]

    while True:
        payload = payload_base.copy()
        payload["page"] = page
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code != 200:
            break

        soup = BeautifulSoup(response.text, "html.parser")
        tables = soup.find_all("table", class_="table table-striped")
        table_found = False

        for table in tables:
            headers_table = [th.get_text(strip=True) for th in table.find_all("th")]
            if headers_table == expected_headers:
                table_found = True
                for tr in table.find_all("tr"):
                    tds = tr.find_all("td")
                    if tds and len(tds) == len(expected_headers):
                        row_dict = dict(zip(headers_table, [''.join(td.stripped_strings) for td in tds]))

                        # Extrair Runner, Dossard e Nationality
                        name_col_idx = headers_table.index("Nom & Prénom")
                        name_cell = tds[name_col_idx]
                        a_tag = name_cell.find("a")
                        if a_tag:
                            text = a_tag.get_text(strip=True)
                            if "(" in text and ")" in text:
                                name, nat = text.rsplit("(", 1)
                                dossard = text.split("N°")[1].split()[0].rstrip("-")
                                row_dict["Runner"] = name.replace(f"N°{dossard}", "").strip().lstrip("- ").strip()
                                row_dict["Nationality"] = nat.replace(")", "").strip()
                                row_dict["Dossard"] = dossard
                            else:
                                row_dict["Runner"] = text.lstrip("- ").strip()
                                row_dict["Nationality"] = ""
                                row_dict["Dossard"] = ""
                        all_rows.append(row_dict)
                break

        if not table_found:
            break
        page += 1

    if all_rows:
        df = pd.DataFrame(all_rows)
        if "Nom & Prénom" in df.columns:
            df.drop(columns=["Nom & Prénom"], inplace=True)
        if "Distance" in df.columns:
            df["Distance"] = df["Distance"].str.replace("km", "").str.strip()
        cols = df.columns.tolist()
        final_order = ["Clsmt.", "Runner", "Nationality", "Dossard"] + [c for c in cols if c not in ["Clsmt.", "Runner", "Nationality", "Dossard"]]
        df = df[final_order]

        df_por = df[df["Nationality"] == "POR"]

        # Timestamp em Lisboa
        tz_pt = pytz.timezone("Europe/Lisbon")
        timestamp = datetime.now(tz_pt).strftime("%d-%m-%Y %H:%M:%S")

        # Gerar HTML das linhas com destaque apenas para favoritos
        def generate_table_html(df_input):
            headers_html = "".join([f"<th>{col}</th>" for col in df_input.columns])
            rows_html = ""
            for _, row in df_input.iterrows():
                row_color = ""
                for fav in FAVORITES:
                    if fav.lower() in row["Runner"].lower():
                        row_color = ' style="background-color:#ccffcc;"'
                        break
                rows_html += "<tr" + row_color + ">" + "".join([f"<td>{row[col]}</td>" for col in df_input.columns]) + "</tr>"
            table_html = f"<table>{headers_html}{rows_html}</table>"
            return table_html

        html_por = generate_table_html(df_por)
        html_all = generate_table_html(df)

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Breizhchrono Classification</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                small {{ display: block; margin-bottom: 10px; color: gray; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <small>Generated on {timestamp}</small>
            <h3>Portuguese Runners</h3>
            {html_por}
            <h3>All Runners</h3>
            {html_all}
        </body>
        </html>
        """

        with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"✅ HTML generated successfully: {OUTPUT_HTML}")
    else:
        print("⚠️ No data extracted.")


if __name__ == "__main__":
    summary_classification()
