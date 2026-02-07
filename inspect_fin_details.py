import pandas as pd
import os

excel_path = os.path.join(os.path.dirname(__file__), 'Fin_details.xlsx')

if not os.path.exists(excel_path):
    print('File not found.')
else:
    df = pd.read_excel(excel_path)
    print('Columns:', df.columns.tolist())
    print('Sample Data:')
    print(df.head())
    print('Info:')
    print(df.info())
