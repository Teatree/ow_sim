import gspread
import random
import pandas as pd
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials
from collections import defaultdict
from tqdm import tqdm
#from encounter import simulateEncounters
from encounter2 import publicSimulateEncountersPopulation
import threading
from line_profiler import profile

# Authorization Setup
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]
credentials = ServiceAccountCredentials.from_json_keyfile_name('quiet-notch-415414-04dc8df47d6d.json', scope)
gc = gspread.authorize(credentials)

print("sim multi")
# ============================
# INIT
# Open the Spreadsheet (no changes needed here)
spreadsheet_key = '1OfSVkFkOfhmMN8GUiv4-cWTZQmgiWTr7Q3NRp9GpYWc' 
spreadsheet = gc.open_by_key(spreadsheet_key)
keyValueSheet = spreadsheet.worksheet('KeyValue')

# Fetch each range separately
range_1 = keyValueSheet.range('H7:I27')
range_2 = keyValueSheet.range('C11:C37')

# Combine the cell ranges into one list
cells = range_1 + range_2

# Continue with the dictionary comprehension as before
cell_values = {(cell.row, cell.col): cell.value for cell in cells}

# Fetch KeyValue input data
num_runs_individual = int(cell_values[7,8])
energyForMining = int(cell_values[(18, 9)])
energyForHarvesting = int(cell_values[(19, 9)])
energyForEncounter = int(cell_values[(20, 9)])
energy_cost_per_mining = int(cell_values[(33, 3)])
energy_cost_per_encounter = int(cell_values[(36, 3)])+int(cell_values[(37, 3)])
# region_name = cell_values[(11, 9)]
# region_stage = int(cell_values[(12, 9)])
num_harvestables = int(cell_values[(24, 9)])
num_deposits = int(cell_values[(22, 9)])
num_mega_deposits = int(cell_values[(23, 9)])
harvesting_cost = int(cell_values[(34, 3)])
mini_scanning_cost = int(cell_values[(33, 3)])
num_deplete_mega = int(cell_values[(27, 9)])
mega_scanning_cost = int(cell_values[(35, 3)])

regionTravelCost = []
regionTravelCost.append(int(cell_values[(11, 3)]))
regionTravelCost.append(int(cell_values[(12, 3)]))
regionTravelCost.append(int(cell_values[(13, 3)]))
regionTravelCost.append(int(cell_values[(14, 3)]))



# population specific
runs_weighted_types = []
for cell in keyValueSheet.range('N7:N11'):
    runs_weighted_types.append(int(cell.value))
region_weighted_types = []
for reg in keyValueSheet.range('N12:N14'):
    region_weighted_types.append(str(reg.value))
region_stage_weighted_types = []
for regs in keyValueSheet.range('N15:N18'):
    region_stage_weighted_types.append(int(regs.value))
#run_focus_weighted_types = []
#for runt in keyValueSheet.range('N19:N21'):
#    run_focus_weighted_types.append(int(runt.value))

max_runs_weighted_values = []
for cell in keyValueSheet.range('O7:O11'):
    max_runs_weighted_values.append(int(cell.value))
max_region_weighted_values = []
for cell in keyValueSheet.range('O12:O14'):
    max_region_weighted_values.append(int(cell.value))
max_region_stage_weighted_values = []
for cell in keyValueSheet.range('O15:O18'):
    max_region_stage_weighted_values.append(int(cell.value))
#run_focus_weighted_values = []
#for cell in keyValueSheet.range('R19:O21'):
#    run_focus_weighted_values.append(int(cell.value))

high_runs_weighted_values = []
for cell in keyValueSheet.range('P7:P11'):
    high_runs_weighted_values.append(int(cell.value))
high_region_weighted_values = []
for cell in keyValueSheet.range('P12:P14'):
    high_region_weighted_values.append(int(cell.value))
high_region_stage_weighted_values = []
for cell in keyValueSheet.range('P15:P18'):
    high_region_stage_weighted_values.append(int(cell.value))
#run_focus_weighted_values = []
#for cell in keyValueSheet.range('O19:O21'):
    #run_focus_weighted_values.append(int(cell.value))

moderate_runs_weighted_values = []
for cell in keyValueSheet.range('Q7:Q11'):
    moderate_runs_weighted_values.append(int(cell.value))
moderate_region_weighted_values = []
for cell in keyValueSheet.range('Q12:Q14'):
    moderate_region_weighted_values.append(int(cell.value))
moderate_region_stage_weighted_values = []
for cell in keyValueSheet.range('Q15:Q18'):
    moderate_region_stage_weighted_values.append(int(cell.value))
#run_focus_weighted_values = []
#for cell in keyValueSheet.range('P19:O21'):
#    run_focus_weighted_values.append(int(cell.value))

low_runs_weighted_values = []
for cell in keyValueSheet.range('R7:R11'):
    low_runs_weighted_values.append(int(cell.value))
low_region_weighted_values = []
for cell in keyValueSheet.range('R12:R14'):
    low_region_weighted_values.append(int(cell.value))
low_region_stage_weighted_values = []
for cell in keyValueSheet.range('R15:R18'):
    low_region_stage_weighted_values.append(int(cell.value))
#run_focus_weighted_values = []
#for cell in keyValueSheet.range('Q19:O21'):
#    run_focus_weighted_values.append(int(cell.value))

def load_illuvials_list(illuvials_list_data):
    headers = illuvials_list_data[1]
    production_id_idx = headers.index('Production_ID')  # Replace with the correct header if necessary
    
    illuvialsCounts = []
    # Skip the header row with [1:]
    for row in illuvials_list_data[1:]:
        # Construct a dictionary for each Illuvial
        illuvial = {
            'Production_ID': row[production_id_idx],
            'CaptureCount': 0,
        }
        illuvialsCounts.append(illuvial)
    
    return illuvialsCounts


# ================================
# DEPOSIT DATA
depositSpawnSheet = spreadsheet.worksheet('DepositSpawn_EXPORT')
populationEstimateSheet = spreadsheet.worksheet('PopulationEstimate')
populationSimSheet = spreadsheet.worksheet('PopulationSim')
populationSimIlluvialSheet = spreadsheet.worksheet('PopulationSimIlluvial')
mining_sim_sheet = spreadsheet.worksheet('MiningSim')
harvesting_sim_sheet = spreadsheet.worksheet('HarvestingSim')
illuvials_list_sheet = spreadsheet.worksheet('IlluvialsList')
illuvials_list_data = illuvials_list_sheet.get_all_values()
illuvialsCounts = load_illuvials_list(illuvials_list_data)
deposit_spawn_data = depositSpawnSheet.get_all_records()
deposits_info = {}  # A dictionary to hold the deposit information
regular_deposits = ['GeodyneDeposit', 'LazuriteDeposit', 'BismuthDeposit']
mega_deposits = ['SeismicQuartz', 'TectonicNeovite', 'HelioAgate']

for row in deposit_spawn_data :
    # Using the region, stage, and deposit type as a unique key
    key = (row['Region'], row['Region Stage'], row['Deposit Type'])
    
    # Structuring the data for easy access
    deposits_info[key] = {
        'Mineables':{
            'Osvium': row['Osvium'],
            'Rhodivium': row['Rhodivium'],
            'Lithvium': row['Lithvium'],
            'Chrovium': row['Chrovium'],
            'Pallavium': row['Pallavium'],
            'Gallvium': row['Gallvium'],
            'Vanavium': row['Vanavium'],
            'Tellvium': row['Tellvium'],
            'Rubivium': row['Rubivium'],
            'Irivium': row['Irivium'],
            'Selenvium': row['Selenvium'],
            'Celestvium': row['Celestvium'],
            'Shard T0': row['ShardT0'],
            'Shard T1': row['ShardT1'],
            'Shard T2': row['ShardT2'],
            'Shard T3': row['ShardT3'],
            'Shard T4': row['ShardT4'],
            'Shard T5': row['ShardT5'],
            'WaterGemT0': row['WaterGemT0'],
            'WaterGemT1': row['WaterGemT1'],
            'WaterGemT2': row['WaterGemT2'],
            'WaterGemT3': row['WaterGemT3'],
            'WaterGemT4': row['WaterGemT4'],
            'WaterGemT5': row['WaterGemT5'],
            'EarthGemT0': row['EarthGemT0'],
            'EarthGemT1': row['EarthGemT1'],
            'EarthGemT2': row['EarthGemT2'],
            'EarthGemT3': row['EarthGemT3'],
            'EarthGemT4': row['EarthGemT4'],
            'EarthGemT5': row['EarthGemT5'],
            'FireGemT0': row['FireGemT0'],
            'FireGemT1': row['FireGemT1'],
            'FireGemT2': row['FireGemT2'],
            'FireGemT3': row['FireGemT3'],
            'FireGemT4': row['FireGemT4'],
            'FireGemT5': row['FireGemT5'],
            'NatureGemT0': row['NatureGemT0'],
            'NatureGemT1': row['NatureGemT1'],
            'NatureGemT2': row['NatureGemT2'],
            'NatureGemT3': row['NatureGemT3'],
            'NatureGemT4': row['NatureGemT4'],
            'NatureGemT5': row['NatureGemT5'],
            'AirGemT0': row['AirGemT0'],
            'AirGemT1': row['AirGemT1'],
            'AirGemT2': row['AirGemT2'],
            'AirGemT3': row['AirGemT3'],
            'AirGemT4': row['AirGemT4'],
            'AirGemT5': row['AirGemT5']
        },
        'Slots': row['Slots'],
        'Probabilities': {
            'Slot1Prob': row['Slot1Prob'],
            'Slot2Prob': row['Slot2Prob'],
            'Slot3Prob': row['Slot3Prob'],
            'Slot4Prob': row['Slot4Prob'],
            'Slot5Prob': row['Slot5Prob'],
            'Slot6Prob': row['Slot6Prob'],
            'Slot7Prob': row['Slot7Prob'],
            'Slot8Prob': row['Slot8Prob'],
            'Slot9Prob': row['Slot9Prob'],
            'Slot10Prob': row['Slot10Prob'],
            'Slot11Prob': row['Slot11Prob'],
            'Slot12Prob': row['Slot12Prob'],
            'Slot13Prob': row['Slot13Prob'],
            'Slot14Prob': row['Slot14Prob'],
            'Slot15Prob': row['Slot15Prob'],
            'Slot16Prob': row['Slot16Prob']
        }
    }



def choose_mineables(region, stage, deposit):
    key = (region, stage, deposit)
    deposit_data = deposits_info.get(key)
    if not deposit_data:
        return []

    mineables = deposit_data['Mineables']
    probabilities = [deposit_data['Probabilities'][f'Slot{i}Prob'] for i in range(1, 17)]
    slots = random.choices(range(1, 17), weights=probabilities, k=1)[0]

    chosen_mineables = random.choices(list(mineables.keys()), weights=list(mineables.values()), k=slots)
    return chosen_mineables


# ================================
# HARVESTABLE DATA
harvestableSpawnSheet = spreadsheet.worksheet('HarvestSpawn_EXPORT')
harvestable_spawn_data = harvestableSpawnSheet.get_all_records()
harvestables_info = {}  # A dictionary to hold the deposit information
regular_harvestSpots = ['Clovium', 'NymphairBasket', 'Flintcap', 'Puffballs', 'StinkyFlora', 'WallPopper', 'GumboDandy', 'Ringshrooms', 'JellyFruit']

for row in harvestable_spawn_data :
    # Using the region, stage, and deposit type as a unique key
    key = (row['Region'], row['Region Stage'], row['Harvestable Type'])
    
    # Structuring the data for easy access
    harvestables_info[key] = {
        'Harvestables':{
            'SpikeJuice_T0': row['SpikeJuice_T0'],
            'SpikeJuice_T1': row['SpikeJuice_T1'],
            'SpikeJuice_T2': row['SpikeJuice_T2'],
            'SpikeJuice_T3': row['SpikeJuice_T3'],
            'BasketFruit_T0': row['BasketFruit_T0'],
            'BasketFruit_T1': row['BasketFruit_T1'],
            'BasketFruit_T2': row['BasketFruit_T2'],
            'BasketFruit_T3': row['BasketFruit_T3'],
            'FlintCapCap_T0': row['FlintCapCap_T0'],
            'FlintCapCap_T1': row['FlintCapCap_T1'],
            'FlintCapCap_T2': row['FlintCapCap_T2'],
            'FlintCapCap_T3': row['FlintCapCap_T3'],
            'DragonEgg_T0': row['DragonEgg_T0'],
            'DragonEgg_T1': row['DragonEgg_T1'],
            'DragonEgg_T2': row['DragonEgg_T2'],
            'DragonEgg_T3': row['DragonEgg_T3'],
            'Floraball_T0': row['Floraball_T0'],
            'Floraball_T1': row['Floraball_T1'],
            'Floraball_T2': row['Floraball_T2'],
            'Floraball_T3': row['Floraball_T3'],
            'PopSpore_T0': row['PopSpore_T0'],
            'PopSpore_T1': row['PopSpore_T1'],
            'PopSpore_T2': row['PopSpore_T2'],
            'PopSpore_T3': row['PopSpore_T3'],
            'GumboBaby_T0': row['GumboBaby_T0'],
            'GumboBaby_T1': row['GumboBaby_T1'],
            'GumboBaby_T2': row['GumboBaby_T2'],
            'GumboBaby_T3': row['GumboBaby_T3'],
            'Ringnut_T0': row['Ringnut_T0'],
            'Ringnut_T1': row['Ringnut_T1'],
            'Ringnut_T2': row['Ringnut_T2'],
            'Ringnut_T3': row['Ringnut_T3'],
            'JellyfruitTendril_T0': row['JellyfruitTendril_T0'],
            'JellyfruitTendril_T1': row['JellyfruitTendril_T1'],
            'JellyfruitTendril_T2': row['JellyfruitTendril_T2'],
            'JellyfruitTendril_T3': row['JellyfruitTendril_T3']
        },
        'Essences':{
            'Sanguine': row['Sanguine'],
            'Bolstering': row['Bolstering'],
            'Lethargy': row['Lethargy'],
            'Growth': row['Growth'],
            'Agile': row['Agile'],
            'Vitality': row['Vitality'],
            'Haste': row['Haste'],
            'Wrath': row['Wrath'],
            'Guardian': row['Guardian'],
            'Might': row['Might'],
            'Fury': row['Fury'],
            'Ruination': row['Ruination']
        },
        'Essence Chance': row['Essence Chance'],
        'Bonus Essence': row['Bonus Essence']
    }

def choose_harvestable(region, stage, harvestableSpot):
    key = (region, stage, harvestableSpot)
    harvestable_data = harvestables_info.get(key)
    if not harvestable_data:
        return []

    harvestables = harvestable_data['Harvestables']

    chosen_harvestables = random.choices(list(harvestables.keys()), weights=list(harvestables.values()))
    return chosen_harvestables

def choose_essences(region, stage, harvestableSpot):
    key = (region, stage, harvestableSpot)
    harvestable_data = harvestables_info.get(key)
    if not harvestable_data:
        return []

    essences = harvestable_data['Essences']

    chosen_essences = random.choices(list(essences.keys()), weights=list(essences.values()))

    return chosen_essences[0]

population_data = populationEstimateSheet.get_all_records()
deposit_spawn_data = depositSpawnSheet.get_all_records()
harvestable_spawn_data = harvestableSpawnSheet.get_all_records()

# =================================
# SIMULATION PART WORKER

# Helper Functions

def load_illuvials_list(sheet_name):
    sheet = spreadsheet.worksheet(sheet_name)
    # Get all values from the sheet
    all_values = sheet.get_all_values()
    # Identify the header row, assuming it's the first row
    headers = all_values[1]
    #print("header: " + str(headers[0]))
    
    # Find the indices for the columns you're interested in
    production_id_idx = headers.index('Production_ID')  # Replace with the correct header if necessary
    stage_idx = headers.index('Stage')
    tier_idx = headers.index('Tier')
    affinity_idx = headers.index('Affinity')
    class_idx = headers.index('Class')
    mastery_points_idx = headers.index('Mastery Points')
    
    illuvials_list = []
    # Skip the header row with [1:]
    for row in all_values[1:]:
        # Construct a dictionary for each Illuvial
        illuvial = {
            'Production_ID': row[production_id_idx],
            'Stage': row[stage_idx],
            'Tier': row[tier_idx],
            'Affinity': row[affinity_idx],
            'Class': row[class_idx],
            'Mastery Points': row[mastery_points_idx],
        }
        illuvials_list.append(illuvial)
    
    return illuvials_list

def load_sheet_data(sheet_name):
    """Load data from a specified sheet."""
    sheet = spreadsheet.worksheet(sheet_name)
    return sheet.get_all_records()

def load_illuvial_weights(sheet_name):
    sheet = spreadsheet.worksheet(sheet_name)
    data = sheet.get_all_records()
    weights = {}
    for row in data:
        weights[(row['Region'], row['Region Stage'], row['Encounter Type'])] = {
            'Stage': {key: value for key, value in row.items() if key.startswith('S')},
            'Tier': {key: value for key, value in row.items() if key.startswith('T')},
            'Affinity': {key: value for key, value in row.items() if key in ['Water', 'Fire', 'Earth', 'Air', 'Nature']},
            'Class': {key: value for key, value in row.items() if key not in ['Region', 'Stage', 'Encounter Type', 'Weight', 'Target Power']}
        }
    return weights

def load_capture_difficulties(sheet_name):
    sheet = spreadsheet.worksheet(sheet_name)
    return sheet.get_all_records()

# encounter_types = load_sheet_data('EncounterType_EXPORT')
# quantity_weights = load_sheet_data('QuantityWeightsTable_EXPORT')
# illuvial_weights = load_illuvial_weights('IlluvialWeightsTable_EXPORT')
# illuvials_list = load_illuvials_list('IlluvialsList')
# capture_difficulties = load_capture_difficulties('Capture')


def worker(segment_data, shared_data, results):
    deposit_spawn_data, harvestable_spawn_data, illuvialsCounts, shard_names, shard_amounts_values_int, shard_powers, encounter_types, quantity_weights, illuvial_weights, illuvials_list, capture_difficulties, shard_amounts = shared_data

    segment_name = segment_data['']
    print("simulating " + segment_name)

    invShards = [] # starting amount of shards that every Player in the segment has
    
    population_sim_summary = []

    for day_key in tqdm(segment_data.items()):
        day = ""
        total_crypton_spent = 0
        runs = 0
        encounterResults = None
        populationCount = 0
        population = 0
        extractionsCount = 0
        harvestsCount = 0
        deposits = []
        harvests = []
        deposit_counts = {'GeodyneDeposit': 0,'LazuriteDeposit': 0,'BismuthDeposit': 0,'SeismicQuartz': 0,'TectonicNeovite': 0,'HelioAgate': 0}
        harvests_counts = {'Clovium': 0,'NymphairBasket': 0,'Flintcap':0, 'Puffballs': 0,'StinkyFlora': 0,'WallPopper': 0,'GumboDandy': 0,'Ringshrooms': 0,'JellyFruit': 0}
        harvestResults = []
        harvestResult_counts = {'SpikeJuice_T0': 0,'SpikeJuice_T1': 0,'SpikeJuice_T2': 0,'SpikeJuice_T3': 0,'BasketFruit_T0': 0,'BasketFruit_T1': 0,'BasketFruit_T2': 0,'BasketFruit_T3': 0,'FlintCapCap_T0': 0,'FlintCapCap_T1': 0,'FlintCapCap_T2': 0,'FlintCapCap_T3': 0,'DragonEgg_T0': 0,'DragonEgg_T1': 0,'DragonEgg_T2': 0,'DragonEgg_T3': 0,'Floraball_T0': 0,'Floraball_T1': 0,'Floraball_T2': 0,'Floraball_T3': 0,'PopSpore_T0': 0,'PopSpore_T1': 0,'PopSpore_T2': 0,'PopSpore_T3': 0,'GumboBaby_T0': 0,'GumboBaby_T1': 0,'GumboBaby_T2': 0,'GumboBaby_T3': 0,'Ringnut_T0': 0,'Ringnut_T1': 0,'Ringnut_T2': 0,'Ringnut_T3': 0,'JellyfruitTendril_T0': 0,'JellyfruitTendril_T1': 0,'JellyfruitTendril_T2': 0,'JellyfruitTendril_T3': 0}
        essenceResult_counts = {"Sanguine": 0, "Bolstering": 0,"Lethargy": 0,"Growth": 0,"Agile": 0,"Vitality": 0,"Haste": 0,"Wrath": 0,"Guardian": 0,"Might": 0,"Fury": 0,"Ruination": 0}
        mineables = []
        mineablesT0 = ['Osvium','Rhodivium']
        mineablesT1 = ['Lithvium','Chrovium']
        mineablesT2 = ['Pallavium','Gallvium']
        mineablesT3 = ['Vanavium','Tellvium']
        mineablesT4 = ['Rubivium','Irivium']
        mineablesT5 = ['Selenvium','Celestvium']
        shardTypeCounts = ['ShardT0','ShardT1','ShardT2','ShardT3','ShardT4','ShardT5']
        gemsTypeCounts = ['WaterGemT0','WaterGemT1','WaterGemT2','WaterGemT3','WaterGemT4','WaterGemT5','EarthGemT0','EarthGemT1','EarthGemT2','EarthGemT3','EarthGemT4','EarthGemT5','FireGemT0','FireGemT1','FireGemT2','FireGemT3','FireGemT4','FireGemT5','NatureGemT0','NatureGemT1','NatureGemT2','NatureGemT3','NatureGemT4','NatureGemT5','AirGemT0','AirGemT1','AirGemT2','AirGemT3','AirGemT4','AirGemT5']
        mineable_counts = {'Osvium':0,'Rhodivium':0,'Lithvium':0,'Chrovium':0,'Pallavium':0,'Gallvium':0,'Vanavium':0,'Tellvium':0,'Rubivium':0,'Irivium':0,'Selenvium':0,'Celestvium':0,'ShardT0':0,'ShardT1':0,'ShardT2':0,'ShardT3':0,'ShardT4':0,'ShardT5':0,'WaterGemT0':0,'WaterGemT1':0,'WaterGemT2':0,'WaterGemT3':0,'WaterGemT4':0,'WaterGemT5':0,'EarthGemT0':0,'EarthGemT1':0,'EarthGemT2':0,'EarthGemT3':0,'EarthGemT4':0,'EarthGemT5':0,'FireGemT0':0,'FireGemT1':0,'FireGemT2':0,'FireGemT3':0,'FireGemT4':0,'FireGemT5':0,'NatureGemT0':0,'NatureGemT1':0,'NatureGemT2':0,'NatureGemT3':0,'NatureGemT4':0,'NatureGemT5':0,'AirGemT0':0,'AirGemT1':0,'AirGemT2':0,'AirGemT3':0,'AirGemT4':0,'AirGemT5':0}
        t0oresCounts = {'Osvium': 0,'Rhodivium': 0}
        t1oresCounts = {'Lithvium': 0,'Chrovium': 0}
        t2oresCounts = {'Pallavium':0,'Gallvium':0}
        t3oresCounts = {'Vanavium':0,'Tellvium':0}
        t4oresCounts = {'Rubivium':0,'Irivium':0}
        t5oresCounts = {'Selenvium':0,'Celestvium':0}
        shardCounts = {'Shard T0':0,'Shard T1':0,'Shard T2':0,'Shard T3':0,'Shard T4':0,'Shard T5':0}
        gemsCounts = {'WaterGemT0':0,'WaterGemT1':0,'WaterGemT2':0,'WaterGemT3':0,'WaterGemT4':0,'WaterGemT5':0,'EarthGemT0':0,'EarthGemT1':0,'EarthGemT2':0,'EarthGemT3':0,'EarthGemT4':0,'EarthGemT5':0,'FireGemT0':0,'FireGemT1':0,'FireGemT2':0,'FireGemT3':0,'FireGemT4':0,'FireGemT5':0,'NatureGemT0':0,'NatureGemT1':0,'NatureGemT2':0,'NatureGemT3':0,'NatureGemT4':0,'NatureGemT5':0,'AirGemT0':0,'AirGemT1':0,'AirGemT2':0,'AirGemT3':0,'AirGemT4':0,'AirGemT5':0}
        regionsAB = 0
        regionsBS = 0
        regionsCW = 0
        regionsS0 = 0
        regionsS1 = 0
        regionsS2 = 0
        regionsS3 = 0

        if day_key[0] != '':  # Skip the segment name
            population = day_key[1]
            day = day_key[0]

            # remove 30% of population
            if invShards:
                num_to_keep = round(len(invShards) * 0.3)
                indices = np.random.choice(len(invShards), num_to_keep, replace=False)
                invShards = [invShards[i] for i in indices]
            
            while populationCount < population:
                # print(str(segment_name) + ":" + str(populationCount) + " / " + str(population), end="\r", flush=True)
                populationCount += 1
                
                regionNames = []
                regionStages = []

                if segment_name == "Max": 
                    num_runs = random.choices(runs_weighted_types, weights=max_runs_weighted_values)[0]
                    region_name = random.choices(region_weighted_types, weights=max_region_weighted_values)[0]
                    region_stage = random.choices(region_stage_weighted_types, weights=max_region_stage_weighted_values)[0]
                elif segment_name == "High": 
                    num_runs = random.choices(runs_weighted_types, weights=high_runs_weighted_values)[0]
                    region_name = random.choices(region_weighted_types, weights=high_region_weighted_values)[0]
                    region_stage = random.choices(region_stage_weighted_types, weights=high_region_stage_weighted_values)[0]
                elif segment_name == "Moderate": 
                    num_runs = random.choices(runs_weighted_types, weights=moderate_runs_weighted_values)[0]
                    region_name = random.choices(region_weighted_types, weights=moderate_region_weighted_values)[0]
                    region_stage = random.choices(region_stage_weighted_types, weights=moderate_region_stage_weighted_values)[0]
                else:
                    num_runs = random.choices(runs_weighted_types, weights=low_runs_weighted_values)[0]
                    region_name = random.choices(region_weighted_types, weights=low_region_weighted_values)[0]
                    region_stage = random.choices(region_stage_weighted_types, weights=low_region_stage_weighted_values)[0]
                
                

                # ILLUVIALS
                if len(invShards) > 0:
                        # go through invShards and remove
                    currentShardsInv = invShards.pop()
                    newEncounterResults = publicSimulateEncountersPopulation(num_runs, region_name, region_stage, energyForEncounter, energy_cost_per_encounter, currentShardsInv, shard_powers, illuvialsCounts,
                                                                         encounter_types, quantity_weights, illuvial_weights, illuvials_list, capture_difficulties)
                else:
                    shard_amounts = dict(zip(shard_names, shard_amounts_values_int))

                 # ILLUVIAL ENCOUNTERS DON"T REMOVE
                newEncounterResults = publicSimulateEncountersPopulation(num_runs, region_name, region_stage, energyForEncounter, energy_cost_per_encounter, shard_amounts, shard_powers, illuvialsCounts,
                                                                         encounter_types, quantity_weights, illuvial_weights, illuvials_list, capture_difficulties)
                if encounterResults is None:
                    encounterResults = newEncounterResults
                else: 
                    encounterResults = accumulate_encounter_results(encounterResults, newEncounterResults)

                # Calculate IlluvialCounts for BondingCurve
                captured_illuvials = encounterResults[1].split(', ')  # Split the string to get individual Illuvials
                for illuvial in captured_illuvials:
                    illuvial_dict = next((item for item in illuvialsCounts if item['Production_ID'] == illuvial), None)
                    if illuvial_dict is not None:
                        illuvial_dict['CaptureCount'] += 1


                simMiningResult = createMiningSimData(num_runs, region_stage, region_name)
                for run in simMiningResult:
                    runs += 1
                    total_crypton_spent += regionTravelCost[region_stage] # find value based on region stage

                    if region_name == "AB":
                        regionsAB += 1
                    elif region_name == "BS":
                        regionsBS += 1
                    elif region_name == "CW":
                        regionsCW += 1

                    if region_stage == 0:
                        regionsS0 += 1
                    elif region_stage == 1:
                        regionsS1 += 1
                    elif region_stage == 2:
                        regionsS2 += 1
                    elif region_stage == 3:
                        regionsS3 += 1
                    
                    curEX = 0
                    currentShardCounts = {'ShardT0':0,'ShardT1':0,'ShardT2':0,'ShardT3':0,'ShardT4':0,'ShardT5':0}
                    moreThanZero = False
                    for extraction in run['Extractions']:
                        mineables.append(extraction['MineableExtracted'])
                        if extraction['MineableExtracted'] == "ShardT0":
                            currentShardCounts['ShardT0'] += 1
                            moreThanZero = True
                        elif extraction['MineableExtracted'] == "ShardT1":
                            currentShardCounts['ShardT1'] += 1
                            moreThanZero = True
                        elif extraction['MineableExtracted'] == "ShardT2":
                            currentShardCounts['ShardT2'] += 1
                            moreThanZero = True
                        elif extraction['MineableExtracted'] == "ShardT3":
                            currentShardCounts['ShardT3'] += 1
                            moreThanZero = True
                        elif extraction['MineableExtracted'] == "ShardT4":
                            currentShardCounts['ShardT4'] += 1
                            moreThanZero = True
                        elif extraction['MineableExtracted'] == "ShardT5":
                            currentShardCounts['ShardT5'] += 1
                            moreThanZero = True

                        if extraction['Ex'] != curEX:
                            deposits.append(extraction['Deposit'])
                            extractionsCount += 1
                            curEX = extraction['Ex']

                    if moreThanZero == True:
                        invShards.append(currentShardCounts)

                simHarvestingResult = createHarvestingSimData(num_runs, region_stage, region_name)
                for run in simHarvestingResult:
                    for extraction in run['Extractions']:
                        harvestsCount += 1

                        harvests.append(extraction['Harvestable'])
                        harvestResults.append(extraction['HarvestableExtracted'])
                        if extraction['EssenceExtracted'] in essenceResult_counts:
                            essenceResult_counts[extraction['EssenceExtracted']] += 1
                        if extraction['BonusEssenceExtracted'] in essenceResult_counts:
                            essenceResult_counts[extraction['BonusEssenceExtracted']] += 1

        ##print("OUTPUT:" + str(harvesting_data_for_writing))
        # calculate deposits
        for d in deposits:
            if d in deposit_counts:
                deposit_counts[d] += 1
            else:
                deposit_counts[d] = 1
        # calculate mineables
        #mineables 
        for m in mineables:
            if m in mineable_counts:
                mineable_counts[m] += 1
                if m in mineablesT0:
                    t0oresCounts[m] += 1
                elif m in mineablesT1:
                    t1oresCounts[m] += 1
                elif m in mineablesT2:
                    t2oresCounts[m] += 1
                elif m in mineablesT3:
                    t3oresCounts[m] += 1
                elif m in mineablesT4:
                    t4oresCounts[m] += 1
                elif m in mineablesT5:
                    t5oresCounts[m] += 1
                elif m in shardTypeCounts:
                    shardCounts[m] += 1
                elif m in gemsTypeCounts:
                    gemsCounts[m] += 1
            #else:
                #mineable_counts[m] = 0 
                    
        # calculate harvestables
        for d in harvests:
            d = d.replace('_Stage0', '')
            d = d.replace('_Stage1', '')
            d = d.replace('_Stage2', '')
            d = d.replace('_Stage3', '')
            if d in harvests_counts:
                harvests_counts[d] += 1
            else:
                harvests_counts[d] = 1

        # calculate harvestables
        for d in harvestResults:
            if d in harvestResult_counts:
                harvestResult_counts[d] += 1
            else:
                harvestResult_counts[d] = 1

        dpeositCounts = list(deposit_counts.values())
        mineableCounts = list(mineable_counts.values())
        shardCountsVals = list(shardCounts.values())
        harvestsCountsVals = list(harvests_counts.values())
        harvestResultCountsVals = list(harvestResult_counts.values())
        essenceResultCountsVals = list(essenceResult_counts.values()) 
        
        # Calculate counts using numpy
        harvestResult_counts_array = np.array(harvestResultCountsVals)
        essenceResult_counts_array = np.array(essenceResultCountsVals)
        mineable_counts_array = np.array(mineableCounts)
        t0ORECounts_array = np.array(list(t0oresCounts.values()))
        t1ORECounts_array = np.array(list(t1oresCounts.values()))
        t2ORECounts_array = np.array(list(t2oresCounts.values()))
        t3ORECounts_array = np.array(list(t3oresCounts.values()))
        t4ORECounts_array = np.array(list(t4oresCounts.values()))
        t5ORECounts_array = np.array(list(t5oresCounts.values()))
        shardCounts_array = np.array(list(shardCounts.values()))
        gemsCounts_array = np.array(list(gemsCounts.values()))


        if day_key[0] != '':  # Skip the segment name
            simDayData = [day, segment_name, population, total_crypton_spent, runs, regionsAB, regionsBS, regionsCW, regionsS0, regionsS1, regionsS2, regionsS3, extractionsCount, *dpeositCounts, 
                                mineable_counts_array.sum().item(), t0ORECounts_array.sum().item(), t1ORECounts_array.sum().item(),t2ORECounts_array.sum().item(), t3ORECounts_array.sum().item(), t4ORECounts_array.sum().item(), t5ORECounts_array.sum().item(), shardCounts_array.sum().item(), 
                                *shardCountsVals, gemsCounts_array.sum().item(), *mineableCounts, harvestsCount, *harvestsCountsVals, harvestResult_counts_array.sum().item()-essenceResult_counts_array.sum().item(), essenceResult_counts_array.sum().item(), 
                                *harvestResultCountsVals, *essenceResultCountsVals, *encounterResults]
            #population_sim_summary.append(simDayData)
            results.append(simDayData)
    
    return results
 

def simulate_population_activities(shared_data):
    num_threads = 4
    threads = []
    results = []

    for segment_data in population_data:
        t = threading.Thread(target=worker, args=(segment_data, shared_data, results))
        t.start()
        threads.append(t)

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # for segment_data in population_data:
    #     worker(segment_data, shared_data, results)
    
    # Create the first list of lists with empty "Shards Used" and "Illuvials Captured" columns
    empty_results = [row[:143] + [''] + row[144:153] + [''] + row[154:] for row in results]

    # Extract unique Illuvial names and days
    unique_illuvials = sorted(set(illuvial for row in results for illuvial in row[143].split(', ') if illuvial))
    unique_days = sorted(set(row[0] for row in results))

    # Create the second list of lists
    illuvial_counts = [[''] + unique_days]  # First row with day headers
    for illuvial in unique_illuvials:
        row = [illuvial]
        for day in unique_days:
            count = sum(1 for r in results if r[0] == day and illuvial in r[143].split(', '))
            row.append(count)
        illuvial_counts.append(row)
        

    # Write results to sheet
    populationSimSheet.batch_clear(["A2:EZ"])
    try:
        empty_results = custom_sort(empty_results)
    except:
        print(f"Error occurred during custom sorting")
    populationSimSheet.update('A2', empty_results, value_input_option='USER_ENTERED')
    populationSimIlluvialSheet.update('A1', illuvial_counts, value_input_option='USER_ENTERED')


def accumulate_encounter_results(results_list, new_results):
    for i in range(len(new_results)):
        # If the result item is a string, check it's not an empty space and concatenate it.
        if isinstance(new_results[i], str) and new_results[i].strip():
            if results_list[i]:  # if the current result list string is not empty
                results_list[i] += ", " + new_results[i]
            else:  # if the current result list string is empty (first iteration)
                results_list[i] = new_results[i]
        # If the result item is an integer, sum it.
        elif isinstance(new_results[i], int):
            results_list[i] += new_results[i]
    return results_list


def custom_sort(data):
    severity_mapping = {"Max": 1, "High": 2, "Moderate": 3, "Low": 4}

    validated_and_sorted_data = sorted(
        (item for item in data if len(item) > 1 and isinstance(item[0], str) and ' ' in item[0] and item[1] in severity_mapping),
        key=lambda x: (int(x[0].split()[1]), severity_mapping.get(x[1], 5))
    )
    return validated_and_sorted_data
# ==========================
# MINING

# Create MiningSim output data
def createMiningSimData(num_runs, region_stage, region_name):
    runsCounter = 0
    simMiningResult = []
    energyToMine = energyForMining
    deposit = ""
    cetegory = ""
    mineableExtracted = ""

    while runsCounter < num_runs:
        runsCounter+=1 
        extractions = []
        extractionCounter = 1
        energyToMine = energyForMining

        available_regular_deposits = num_deposits
        available_mega_deposits = num_mega_deposits

        while energyToMine >= 100:
            # Decide between regular and mega deposit based on availability
            if available_regular_deposits > 0 and available_mega_deposits > 0:
                deposit_type = random.choices(['regular', 'mega'], weights=[80, 20], k=1)[0]
                if region_stage == 0:
                    deposit_type = 'regular'
            elif available_regular_deposits > 0:
                deposit_type = 'regular'
            else:
                deposit_type = 'mega'

            # Select deposit based on type and decrease availability
            if deposit_type == 'mega':
                deposit = np.random.choice(mega_deposits)
                category = 'mega' 
                energy_cost_per_mining = num_deplete_mega*mega_scanning_cost
                available_mega_deposits -= 1
            else:
                deposit = np.random.choice(regular_deposits)
                category = 'mini'  
                available_regular_deposits -= 1
                energy_cost_per_mining = mini_scanning_cost
            energyToMine -= energy_cost_per_mining

            mineableExtracted = choose_mineables(region_name, str("S"+str(region_stage)), deposit)
            energySpentThisExtraction = False
            for mineable in mineableExtracted:
                extractions.append({
                    'Ex': extractionCounter,
                    'EnergyForMining': energyToMine,
                    'Deposit': deposit,
                    'Category': category,
                    'EnergySpent': energy_cost_per_mining if not energySpentThisExtraction else 0,
                    'MineableExtracted': mineable,
                    'Amount': 1  # Update logic as needed
                })
                if not energySpentThisExtraction:
                    energySpentThisExtraction = True  # Update the flag after the first mineable
            extractionCounter += 1
        simMiningResult.append({
            'Run': runsCounter,
            'Region': region_name,
            'Stage': region_stage,
            'Extractions': extractions
        })
    #print("Mining Done")
    return simMiningResult

# ==========================
# HARVESTING

# Create HarvestingSim output data
def createHarvestingSimData(num_runs, region_stage, region_name):
    runsCounter = 0
    simHarvestingResult = []
    energyToHarvest = energyForHarvesting
    harvestableSpot= ""
    harvestableExtracted = ""
    essenceExtracted = ""
    bonusEssenceExtracted = ""

    while runsCounter < num_runs:
        runsCounter+=1 
        extractions = []
        extractionCounter = 1
        energyToHarvest = energyForHarvesting

        available_harvestables = num_harvestables

        while energyToHarvest >= harvesting_cost:
            available_harvestables -= 1
            energy_cost_per_harvesting = harvesting_cost
            energyToHarvest -= energy_cost_per_harvesting

            harvestableSpot = np.random.choice(regular_harvestSpots) + str("_Stage"+str(region_stage))

            harvestableExtracted = choose_harvestable(region_name, str("S"+str(region_stage)), harvestableSpot)

            energySpentThisExtraction = False
            for h in harvestableExtracted:

                essenceExtracted = ""
                bonusEssenceExtracted = ""
                if random.randint(0,100)>60:
                    essenceExtracted = choose_essences(region_name, str("S"+str(region_stage)), harvestableSpot)
                    if random.randint(0,100)>95:
                        bonusEssenceExtracted = choose_essences(region_name, str("S"+str(region_stage)), harvestableSpot)

                extractions.append({
                    'Ex': extractionCounter,
                    'EnergyForHarvesting': energyToHarvest,
                    'Harvestable': harvestableSpot,
                    'EnergySpent': energy_cost_per_harvesting if not energySpentThisExtraction else 0,
                    'HarvestableExtracted': h,
                    'EssenceExtracted': str(essenceExtracted),
                    'BonusEssenceExtracted': str(bonusEssenceExtracted),
                    'Amount': 1 
                })
                #print("extracitons: " + str(extractions))
                if not energySpentThisExtraction:
                    energySpentThisExtraction = True
            extractionCounter += 1
        simHarvestingResult.append({
            'Run': runsCounter,
            'Region': region_name,
            'Stage': region_stage,
            'Extractions': extractions
        })
    #print("Harvesting Done")
    return simHarvestingResult

# =======================
# WRITING
# Prepare the data for writing
mining_data_for_writing = []
harvesting_data_for_writing = []

# def individualSim(num_runs):
#     simMiningResult = createMiningSimData(num_runs)
#     for run in tqdm(simMiningResult):
#         for extraction in run['Extractions']:
#             # Format each extraction as a row according to your specified columns
#             row = [
#                 run['Run'],
#                 run['Region'],
#                 run['Stage'],
#                 extraction['EnergyForMining'],  # Assuming this is the Energy Balance
#                 extraction['Ex'],
#                 extraction['Deposit'],
#                 extraction['Category'],
#                 extraction['EnergySpent'],
#                 extraction['MineableExtracted'],
#                 extraction['Amount'],
#             ]
#             mining_data_for_writing.append(row)

#     simHarvestingResult = createHarvestingSimData(num_runs)
#     for run in tqdm(simHarvestingResult):
#         #print("this: " + str(simHarvestingResult))
#         for extraction in run['Extractions']:
#             # Format each extraction as a row according to your specified columns
#             row = [
#                 run['Run'],
#                 run['Region'],
#                 run['Stage'],
#                 extraction['EnergyForHarvesting'],  # Assuming this is the Energy Balance
#                 extraction['Ex'],
#                 extraction['Harvestable'],
#                 extraction['EnergySpent'],
#                 extraction['HarvestableExtracted'],
#                 extraction['Amount'],
#                 extraction['EssenceExtracted'],
#                 extraction['BonusEssenceExtracted']
#             ]
#             harvesting_data_for_writing.append(row)
#             ##print("OUTPUT:" + str(harvesting_data_for_writing))
    
#     #(num_runs, region_name, region_stage, energyForEncounter, energy_cost_per_encounter, shard_amounts, shard_powers)

#     if mining_data_for_writing:
#         number_of_rows_to_clear = len(mining_sim_sheet.get_all_values())
#         range_to_clear = f'A2:K{number_of_rows_to_clear}'
#         mining_sim_sheet.batch_clear([range_to_clear])

#         mining_sim_sheet.update('A2', mining_data_for_writing, value_input_option='USER_ENTERED')
#     else:
#         number_of_rows_to_clear = len(mining_sim_sheet.get_all_values())
#         range_to_clear = f'A2:K{number_of_rows_to_clear}'
#         mining_sim_sheet.batch_clear([range_to_clear])


#     if harvesting_data_for_writing:
#         number_of_rows_to_clear = len(harvesting_sim_sheet.get_all_values())
#         range_to_clear = f'A2:K{number_of_rows_to_clear}'
#         harvesting_sim_sheet.batch_clear([range_to_clear])

#         harvesting_sim_sheet.update('A2', harvesting_data_for_writing, value_input_option='USER_ENTERED')
#     else:
#         number_of_rows_to_clear = len(harvesting_sim_sheet.get_all_values())
#         range_to_clear = f'A2:K{number_of_rows_to_clear}'
#         harvesting_sim_sheet.batch_clear([range_to_clear])


# Simulate Encounters
headers = keyValueSheet.row_values(30)

shard_names_col = headers.index('Shard Type') + 1
shard_amounts_col = headers.index('Shard Amounts') + 1  # +1 because list index is 0-based, but gspread is 1-based
shard_power_col = headers.index('Shard Power') + 1

shard_names = keyValueSheet.col_values(shard_names_col)[30:38]
shard_amounts_values = keyValueSheet.col_values(shard_amounts_col)[30:38] 
shard_power_values = keyValueSheet.col_values(shard_power_col)[30:38]

shard_amounts_values_int = [int(value) for value in shard_amounts_values]
shard_power_values_int = [int(value) for value in shard_power_values]

shard_amounts = dict(zip(shard_names, shard_amounts_values_int))
shard_powers = dict(zip(shard_names, shard_power_values_int))


if __name__ == '__main__':
    print("simulating")

    # Load shared data
    deposit_spawn_data = depositSpawnSheet.get_all_records()
    harvestable_spawn_data = harvestableSpawnSheet.get_all_records()
    encounter_types = load_sheet_data('EncounterType_EXPORT')
    quantity_weights = load_sheet_data('QuantityWeightsTable_EXPORT')
    illuvial_weights = load_illuvial_weights('IlluvialWeightsTable_EXPORT')
    illuvials_list = load_illuvials_list('IlluvialsList')
    capture_difficulties = load_capture_difficulties('Capture')

    shared_data = (
        deposit_spawn_data,
        harvestable_spawn_data,
        illuvialsCounts,
        shard_names,
        shard_amounts_values_int,
        shard_powers,
        encounter_types,
        quantity_weights,
        illuvial_weights,
        illuvials_list,
        capture_difficulties,
        shard_amounts
    )

    simulate_population_activities(shared_data)

#individualSim(num_runs_individual)

#combined_values = shard_amounts_values + shard_power_values
#print("combined_values: " + str(combined_values))
# publicSimulateResults(num_runs, region_name, region_stage, energyForEncounter, energy_cost_per_encounter, shard_amounts, shard_powers)