import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Authorization Setup
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]
credentials = ServiceAccountCredentials.from_json_keyfile_name('quiet-notch-415414-04dc8df47d6d.json', scope)
gc = gspread.authorize(credentials)

# Open the Spreadsheet (no changes needed here)
spreadsheet_key = '1OfSVkFkOfhmMN8GUiv4-cWTZQmgiWTr7Q3NRp9GpYWc' 
worksheet_name = 'KeyValue' 
worksheet = gc.open_by_key(spreadsheet_key).worksheet(worksheet_name)

# Fetch input data
num_runs = int(key_value_sheet.acell('H7').value)
energy_per_run = int(key_value_sheet.acell('I18').value)
energy_cost_per_mining = int(key_value_sheet.acell('C33').value)
region_name = key_value_sheet.acell('I11').value
region_stage = int(key_value_sheet.acell('I12').value)
num_deposits = int(key_value_sheet.acell('I22').value)
num_mega_deposits = int(key_value_sheet.acell('I23').value)


# Read Values Example
cell_value = worksheet.acell('B2').value
all_values = worksheet.get_all_values() 

# Write Values Example
cell_range = 'A1:D1'  # Specify the cell range for the update
value_list = [['New Value 1', 'New Value 2', 'New Value 3', cell_value]]  # Wrap your list in another list to form a 2D array

# Update cells with the values
worksheet.update(value_list, cell_range, value_input_option='USER_ENTERED')