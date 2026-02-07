import pandas as pd
import os
import json

excel_path = os.path.join(os.path.dirname(__file__), 'Fin_details.xlsx')
json_path = os.path.join(os.path.dirname(__file__), 'fin_details.json')

def main():
    if not os.path.exists(excel_path):
        print('File not found.')
        return
    df = pd.read_excel(excel_path)
    # Convert dates to string for JSON serialization
    df['T_date'] = df['T_date'].astype(str)
    df['P_date'] = df['P_date'].astype(str)
    # Export to JSON
    df.to_json(json_path, orient='records', indent=2)
    print(f'Exported {len(df)} records to {json_path}')

if __name__ == '__main__':
    main()
