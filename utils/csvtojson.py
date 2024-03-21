import pandas as pd
import json
from unidecode import unidecode

def csv_to_json(file_path):
    df = pd.read_csv(file_path)
    
    # Grab the first three columns
    selected_columns = df.iloc[:, :3]
    
    # Concatenate 'Nombre' and 'Apellidos' columns as keys and use 'DNI' column as values
    data_dict = {unidecode(nombre + ' ' + apellidos): dni for nombre, apellidos, dni in zip(selected_columns['Nombre'], selected_columns['Apellidos'], selected_columns['DNI'])}
    
    # Serialize the dictionary to a JSON string
    json_string = json.dumps(data_dict)
    
    # systemd_ready = json_string.replace('"', '\\"')
    
    return json_string

if __name__ == '__main__':
    file_path = 'usuarios.csv'  
    json_data = csv_to_json(file_path)
    print(json_data)
