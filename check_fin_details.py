import pandas as pd, os
path = r"E:\\Projects\\AI\\repo_all\\GitHub\\arthsutra\\Fin_details.xlsx"
print("exists", os.path.exists(path))
if os.path.exists(path):
    df = pd.read_excel(path)
    print("Columns:", df.columns.tolist())
    print(df.head())
else:
    print("File not found.")