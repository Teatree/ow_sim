import gspread
import random
from oauth2client.service_account import ServiceAccountCredentials
from tqdm import tqdm
from encounter3 import publicSimulateResults
from encounter3 import publicSimulateEncountersPopulation
import pandas as pd
import numpy as np

# Authorization Setup
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('quiet-notch-415414-04dc8df47d6d.json', scope)
gc = gspread.authorize(credentials)

# Open the Spreadsheet
spreadsheet_key = '1OfSVkFkOfhmMN8GUiv4-cWTZQmgiWTr7Q3NRp9GpYWc' 
keyValueSheet = gc.open_by_key(spreadsheet_key).worksheet('KeyValue')

# Fetch each range separately
range_1 = keyValueSheet.range('H7:I27')
range_2 = keyValueSheet.range('C33:C36')

# Combine the cell ranges into one list
cells = range_1 + range_2

# Continue with the dictionary comprehension as before
cell_values = {(cell.row, cell.col): cell.value for cell in cells}

# Fetch KeyValue input data
num_runs = int(cell_values[(7, 8)])
energyForMining = int(cell_values[(18, 9)])
energyForHarvesting = int(cell_values[(19, 9)])
energyForEncounter = int(cell_values[(20, 9)])
energy_cost_per_mining = int(cell_values[(33, 3)])
energy_cost_per_encounter = int(cell_values[(36, 3)])
region_name = cell_values[(11, 9)]
region_stage = int(cell_values[(12, 9)])
num_harvestables = int(cell_values[(24, 9)])
num_deposits = int(cell_values[(22, 9)])
num_mega_deposits = int(cell_values[(23, 9)])
harvesting_cost = int(cell_values[(34, 3)])
mini_scanning_cost = int(cell_values[(33, 3)])
num_deplete_mega = int(cell_values[(27, 9)])
mega_scanning_cost = int(cell_values[(35, 3)])

# population specific
runs_weighted_types = [int(cell.value) for cell in keyValueSheet.range('N7:N11')]
region_weighted_types = [str(reg.value) for reg in keyValueSheet.range('N12:N14')]
region_stage_weighted_types = [int(regs.value) for regs in keyValueSheet.range('N15:N18')]
max_runs_weighted_values = [int(cell.value) for cell in keyValueSheet.range('O7:O11')]
max_region_weighted_values = [int(cell.value) for cell in keyValueSheet.range('O12:O14')]
max_region_stage_weighted_values = [int(cell.value) for cell in keyValueSheet.range('O15:O18')]
high_runs_weighted_values = [int(cell.value) for cell in keyValueSheet.range('P7:P11')]
high_region_weighted_values = [int(cell.value) for cell in keyValueSheet.range('P12:P14')]
high_region_stage_weighted_values = [int(cell.value) for cell in keyValueSheet.range('P15:P18')]
moderate_runs_weighted_values = [int(cell.value) for cell in keyValueSheet.range('Q7:Q11')]
moderate_region_weighted_values = [int(cell.value) for cell in keyValueSheet.range('Q12:Q14')]
moderate_region_stage_weighted_values = [int(cell.value) for cell in keyValueSheet.range('Q15:Q18')]
low_runs_weighted_values = [int(cell.value) for cell in keyValueSheet.range('R7:R11')]
low_region_weighted_values = [int(cell.value) for cell in keyValueSheet.range('R12:R14')]
low_region_stage_weighted_values = [int(cell.value) for cell in keyValueSheet.range('R15:R18')]

# DEPOSIT DATA
depositSpawnSheet = gc.open_by_key(spreadsheet_key).worksheet('DepositSpawn_EXPORT')
populationEstimateSheet = gc.open_by_key(spreadsheet_key).worksheet('PopulationEstimate')
populationSimSheet = gc.open_by_key(spreadsheet_key).worksheet('PopulationSim')
mining_sim_sheet = gc.open_by_key(spreadsheet_key).worksheet('MiningSim')
harvesting_sim_sheet = gc.open_by_key(spreadsheet_key).worksheet('HarvestingSim')
deposit_spawn_data = depositSpawnSheet.get_all_records()
deposits_info = pd.DataFrame(deposit_spawn_data)
regular_deposits = ['GeodyneDeposit', 'LazuriteDeposit', 'BismuthDeposit']
mega_deposits = ['SeismicQuartz', 'TectonicNeovite', 'HelioAgate']

def choose_mineables(region, stage, deposit):
    key = (region, stage, deposit)
    deposit_data = deposits_info[(deposits_info['Region'] == region) & (deposits_info['Region Stage'] == stage) & (deposits_info['Deposit Type'] == deposit)]
    if deposit_data.empty:
        return []

    mineables = deposit_data.iloc[:, 4:56]
    probabilities = deposit_data.iloc[:, 56:72].values.flatten()
    slots = random.choices(range(1, 14), weights=probabilities, k=1)[0]

    chosen_mineables = mineables.sample(n=slots, weights=mineables.values.flatten(), axis=1).columns
    return chosen_mineables.tolist()

# HARVESTABLE DATA
harvestableSpawnSheet = gc.open_by_key(spreadsheet_key).worksheet('HarvestSpawn_EXPORT')
harvestable_spawn_data = harvestableSpawnSheet.get_all_records()
harvestables_info = pd.DataFrame(harvestable_spawn_data)
regular_harvestSpots = ['Clovium', 'NymphairBasket', 'Flintcap', 'Puffballs', 'StinkyFlora', 'WallPopper', 'GumboDandy', 'Ringshrooms', 'JellyFruit']

def choose_harvestable(region, stage, harvestableSpot):
    key = (region, stage, harvestableSpot)
    harvestable_data = harvestables_info[(harvestables_info['Region'] == region) & (harvestables_info['Region Stage'] == stage) & (harvestables_info['Harvestable Type'] == harvestableSpot)]
    if harvestable_data.empty:
        return []

    harvestables = harvestable_data.iloc[:, 4:40]

    chosen_harvestables = harvestables.sample(n=1, weights=harvestables.values.flatten(), axis=1).columns
    return chosen_harvestables.tolist()

def choose_essences(region, stage, harvestableSpot):
    key = (region, stage, harvestableSpot)
    harvestable_data = harvestables_info[(harvestables_info['Region'] == region) & (harvestables_info['Region Stage'] == stage) & (harvestables_info['Harvestable Type'] == harvestableSpot)]
    if harvestable_data.empty:
        return []

    essences = harvestable_data.iloc[:, 40:52]

    chosen_essences = essences.sample(n=1, weights=essences.values.flatten(), axis=1).columns
    return chosen_essences.tolist()[0]

# SIMULATION PART
def simulate_population_activities():
    population_data = pd.DataFrame(populationEstimateSheet.get_all_records())
    population_sim_summary = pd.DataFrame(columns=['Day', 'Segment', 'Population', 'Total Crypton Spent', 'Runs', 'AB Runs', 'BS Runs', 'CW Runs', 'S0 Runs', 'S1 Runs', 'S2 Runs', 'S3 Runs', 'Mines', 'GeodyneDeposit', 'LazuriteDeposit', 'BismuthDeposit', 'SeismicQuartz', 'TectonicNeovite', 'HelioAgate', 'Ores Extracted', 'T0 Ores', 'T1 Ores', 'T2 Ores', 'T3 Ores', 'T4 Ores', 'T5 Ores', 'Shards', 'T0 Shards', 'T1 Shards', 'T2 Shards', 'T3 Shards', 'T4 Shards', 'T5 Shards', 'Gems', 'Water Gems', 'Earth Gems', 'Fire Gems', 'Nature Gems', 'Air Gems', 'Osvium', 'Rhodivium', 'Lithvium', 'Chrovium', 'Pallavium', 'Gallvium', 'Vanavium', 'Tellvium', 'Rubivium', 'Irivium', 'Selenvium', 'Celestvium', 'ShardT0', 'ShardT1', 'ShardT2', 'ShardT3', 'ShardT4', 'ShardT5', 'WaterGemT0', 'WaterGemT1', 'WaterGemT2', 'WaterGemT3', 'WaterGemT4', 'WaterGemT5', 'EarthGemT0', 'EarthGemT1', 'EarthGemT2', 'EarthGemT3', 'EarthGemT4', 'EarthGemT5', 'FireGemT0', 'FireGemT1', 'FireGemT2', 'FireGemT3', 'FireGemT4', 'FireGemT5', 'NatureGemT0', 'NatureGemT1', 'NatureGemT2', 'NatureGemT3', 'NatureGemT4', 'NatureGemT5', 'AirGemT0', 'AirGemT1', 'AirGemT2', 'AirGemT3', 'AirGemT4', 'AirGemT5', 'Harvests', 'Clovium', 'NymphairBasket', 'Flintcap', 'Puffballs', 'StinkyFlora', 'WallPopper', 'GumboDandy', 'Ringshrooms', 'JellyFruit', 'Fruit', 'Essences', 'SpikeJuice_T0', 'SpikeJuice_T1', 'SpikeJuice_T2', 'SpikeJuice_T3', 'BasketFruit_T0', 'BasketFruit_T1', 'BasketFruit_T2', 'BasketFruit_T3', 'FlintCapCap_T0', 'FlintCapCap_T1', 'FlintCapCap_T2', 'FlintCapCap_T3', 'DragonEgg_T0', 'DragonEgg_T1', 'DragonEgg_T2', 'DragonEgg_T3', 'Floraball_T0', 'Floraball_T1', 'Floraball_T2', 'Floraball_T3', 'PopSpore_T0', 'PopSpore_T1', 'PopSpore_T2', 'PopSpore_T3', 'GumboBaby_T0', 'GumboBaby_T1', 'GumboBaby_T2', 'GumboBaby_T3', 'Ringnut_T0', 'Ringnut_T1', 'Ringnut_T2', 'Ringnut_T3', 'JellyfruitTendril_T0', 'JellyfruitTendril_T1', 'JellyfruitTendril_T2', 'JellyfruitTendril_T3', 'Sanguine', 'Bolstering', 'Lethargy', 'Growth', 'Agile', 'Vitality', 'Haste', 'Wrath', 'Guardian', 'Might', 'Fury', 'Ruination','Illuvials Captured','Illuvials','T0 Illuvials','T1 Illuvials','T2 Illuvials','T3 Illuvials','T4 Illuvials','T5 Illuvials','S1 Illuvials','S2 Illuvials','S3 Illuvials','Shards Used'])
    

    for _, segment_data in population_data.iterrows():
        segment_name = segment_data['']

        for day_key, population in tqdm(segment_data.items()):
            if day_key != '':
                # define pop variable
                day = day_key
                runs = 0
                population_count = 0
                # region select
                # region stage select

                while population_count < population:
                    population_count += 1
                    if segment_name == "Max":
                        num_runs = random.choices(runs_weighted_types, weights=max_runs_weighted_values)[0]
                    elif segment_name == "High":
                        num_runs = random.choices(runs_weighted_types, weights=high_runs_weighted_values)[0]
                    elif segment_name == "Moderate":
                        num_runs = random.choices(runs_weighted_types, weights=moderate_runs_weighted_values)[0]
                    else:
                        num_runs = random.choices(runs_weighted_types, weights=low_runs_weighted_values)[0]

                    simMiningResult = pd.DataFrame(createMiningSimData(mining_sim_sheet))
                    simMiningResult['Region'] = simMiningResult['Region'].apply(lambda x: 'AB' if x == 'AB' else ('BS' if x == 'BS' else 'CW'))
                    simMiningResult['Stage'] = simMiningResult['Stage'].apply(lambda x: f'S{x}')

                    extractionsCount = len(simMiningResult)
                    depositCounts = simMiningResult['Deposit'].value_counts().to_dict()
                    mineableCounts = simMiningResult['MineableExtracted'].value_counts().to_dict()

                    # Define variables
                    runs += num_runs
                    total_crypton_spent = num_runs * 1000 # TODO: Has to be price of run in that Region
                    regionsAB = len(simMiningResult[simMiningResult['Region'] == 'AB'])
                    regionsBS = len(simMiningResult[simMiningResult['Region'] == 'BS'])
                    regionsCW = len(simMiningResult[simMiningResult['Region'] == 'CW'])
                    regionsS0 = len(simMiningResult[simMiningResult['Stage'] == 'S0'])
                    regionsS1 = len(simMiningResult[simMiningResult['Stage'] == 'S1'])
                    regionsS2 = len(simMiningResult[simMiningResult['Stage'] == 'S2'])
                    regionsS3 = len(simMiningResult[simMiningResult['Stage'] == 'S3'])

                    t0ORECounts = {ore: mineableCounts.get(ore, 0) for ore in ['Osvium', 'Rhodivium']}
                    t1ORECounts = {ore: mineableCounts.get(ore, 0) for ore in ['Lithvium', 'Chrovium']}
                    t2ORECounts = {ore: mineableCounts.get(ore, 0) for ore in ['Pallavium', 'Gallvium']}
                    t3ORECounts = {ore: mineableCounts.get(ore, 0) for ore in ['Vanavium', 'Tellvium']}
                    t4ORECounts = {ore: mineableCounts.get(ore, 0) for ore in ['Rubivium', 'Irivium']}
                    t5ORECounts = {ore: mineableCounts.get(ore, 0) for ore in ['Selenvium', 'Celestvium']}
                    shardCounts = {shard: mineableCounts.get(shard, 0) for shard in ['ShardT0', 'ShardT1', 'ShardT2', 'ShardT3', 'ShardT4', 'ShardT5']}
                    gemsCounts = {gem: mineableCounts.get(gem, 0) for gem in ['WaterGemT0', 'WaterGemT1', 'WaterGemT2', 'WaterGemT3', 'WaterGemT4', 'WaterGemT5', 'EarthGemT0', 'EarthGemT1', 'EarthGemT2', 'EarthGemT3', 'EarthGemT4', 'EarthGemT5', 'FireGemT0', 'FireGemT1', 'FireGemT2', 'FireGemT3', 'FireGemT4', 'FireGemT5', 'NatureGemT0', 'NatureGemT1', 'NatureGemT2', 'NatureGemT3', 'NatureGemT4', 'NatureGemT5', 'AirGemT0', 'AirGemT1', 'AirGemT2', 'AirGemT3', 'AirGemT4', 'AirGemT5']}

                    simHarvestingResult = pd.DataFrame(createHarvestingSimData(harvesting_sim_sheet))
                    harvestsCount = len(simHarvestingResult)
                    harvestsCountsVals = simHarvestingResult['Harvestable'].value_counts().to_dict()
                    harvestResultCountsVals = simHarvestingResult['HarvestableExtracted'].value_counts().to_dict()

                    encounterResults = publicSimulateEncountersPopulation(num_runs, region_name, region_stage, energyForEncounter, energy_cost_per_encounter, shard_amounts, shard_powers)
                    
                    columns_with_defaults = [
                        'Day', 'Segment', 'Population', 'Total Crypton Spent', 'Runs', 'AB Runs',
                        'BS Runs', 'CW Runs', 'S0 Runs', 'S1 Runs', 'S2 Runs', 'S3 Runs', 'Mines',
                        'GeodyneDeposit', 'LazuriteDeposit', 'BismuthDeposit', 'SeismicQuartz',
                        'TectonicNeovite', 'HelioAgate', 'Mineable Extracted', 'T0 Ores', 'T1 Ores',
                        'T2 Ores', 'T3 Ores', 'T4 Ores', 'T5 Ores', 'Shards', 'T0 Shards', 'T1 Shards',
                        'T2 Shards', 'T3 Shards', 'T4 Shards', 'T5 Shards', 'Gems', 'Osvium', 'Rhodivium',
                        'Lithvium', 'Chrovium', 'Pallavium', 'Gallvium', 'Vanavium', 'Tellvium', 'Rubivium',
                        'Irivium', 'Selenvium', 'Celestvium', 'ShardT0', 'ShardT1', 'ShardT2', 'ShardT3',
                        'ShardT4', 'ShardT5', 'WaterGemT0', 'WaterGemT1', 'WaterGemT2', 'WaterGemT3',
                        'WaterGemT4', 'WaterGemT5', 'EarthGemT0', 'EarthGemT1', 'EarthGemT2', 'EarthGemT3',
                        'EarthGemT4', 'EarthGemT5', 'FireGemT0', 'FireGemT1', 'FireGemT2', 'FireGemT3',
                        'FireGemT4', 'FireGemT5', 'NatureGemT0', 'NatureGemT1', 'NatureGemT2', 'NatureGemT3',
                        'NatureGemT4', 'NatureGemT5', 'AirGemT0', 'AirGemT1', 'AirGemT2', 'AirGemT3',
                        'AirGemT4', 'AirGemT5', 'Harvests', 'Clovium', 'NymphairBasket', 'Flintcap',
                        'Puffballs', 'StinkyFlora', 'WallPopper', 'GumboDandy', 'Ringshrooms', 'JellyFruit',
                        'Fruit', 'Essences', 'SpikeJuice_T0', 'SpikeJuice_T1', 'SpikeJuice_T2', 'SpikeJuice_T3',
                        'BasketFruit_T0', 'BasketFruit_T1', 'BasketFruit_T2', 'BasketFruit_T3',
                        'FlintCapCap_T0', 'FlintCapCap_T1', 'FlintCapCap_T2', 'FlintCapCap_T3',
                        'DragonEgg_T0', 'DragonEgg_T1', 'DragonEgg_T2', 'DragonEgg_T3', 'Floraball_T0',
                        'Floraball_T1', 'Floraball_T2', 'Floraball_T3', 'PopSpore_T0', 'PopSpore_T1',
                        'PopSpore_T2', 'PopSpore_T3', 'GumboBaby_T0', 'GumboBaby_T1', 'GumboBaby_T2',
                        'GumboBaby_T3', 'Ringnut_T0', 'Ringnut_T1', 'Ringnut_T2', 'Ringnut_T3',
                        'JellyfruitTendril_T0', 'JellyfruitTendril_T1', 'JellyfruitTendril_T2', 'JellyfruitTendril_T3',
                        'Sanguine', 'Bolstering', 'Lethargy', 'Growth', 'Agile', 'Vitality', 'Haste',
                        'Wrath', 'Guardian', 'Might', 'Fury', 'Ruination', 'Illuvials Captured', 'Illuvials',
                        'T0 Illuvials', 'T1 Illuvials', 'T2 Illuvials', 'T3 Illuvials', 'T4 Illuvials',
                        'T5 Illuvials', 'S1 Illuvials', 'S2 Illuvials', 'S3 Illuvials', 'Shards Used'
                    ]

                    data_dict = {key: 0 for key in columns_with_defaults}  # Default all to 0

                    data_updates = {
                        'Day': day,
                        'Segment': segment_name,
                        'Population': population,
                        'Total Crypton Spent': total_crypton_spent,
                        'Runs': runs,
                        'AB Runs': regionsAB,
                        'BS Runs': regionsBS,
                        'CW Runs': regionsCW,
                        'S0 Runs': regionsS0,
                        'S1 Runs': regionsS1,
                        'S2 Runs': regionsS2,
                        'S3 Runs': regionsS3,
                        'Mines': extractionsCount,
                        'Ores Extracted': sum(mineableCounts.values()),
                        'T0 Ores': sum(t0ORECounts.values()),
                        'T1 Ores': sum(t1ORECounts.values()),
                        'T2 Ores': sum(t2ORECounts.values()),
                        'T3 Ores': sum(t3ORECounts.values()),
                        'T4 Ores': sum(t4ORECounts.values()),
                        'T5 Ores': sum(t5ORECounts.values()),
                        'Shards': sum(shardCounts.values()),
                        'Gems': sum(gemsCounts.values()),
                        'Harvests': harvestsCount,
                        'Fruit': 0,
                        'Essences': 0,
                        }
                    
                    data_dict.update(data_updates)
                    data_dict.update(depositCounts)
                    data_dict.update(shardCounts)
                    data_dict.update(mineableCounts)
                    data_dict.update(harvestsCountsVals)
                    data_dict.update(harvestResultCountsVals)
                    data_dict.update(encounterResults)

                    # print(type(population_sim_summary))
                    simDayData = pd.Series(data_dict, index=columns_with_defaults)
                    simDayData_df = simDayData.to_frame().T
                    population_sim_summary = pd.concat([population_sim_summary, simDayData_df], ignore_index=True)
                    # print(population_sim_summary.dtypes)
                    # print(simDayData.dtypes)
    population_sim_summary.fillna(0, inplace=True)
    populationSimSheet.batch_clear(["A2:EX"])
    try:
        population_sim_summary = custom_sort(population_sim_summary)
    except:
        print("Error occurred during sorting")
    populationSimSheet.update('A2', population_sim_summary.to_numpy().tolist(), value_input_option='USER_ENTERED')
            
def custom_sort(data):
    severity_mapping = {"Max": 1, "High": 2, "Moderate": 3, "Low": 4}
    data['SortKey'] = data['Day'].str.extract('(\d+)', expand=False).astype(int)
    data['SeverityKey'] = data['Segment'].map(severity_mapping)
    data.sort_values(['SortKey', 'SeverityKey'], inplace=True)
    data.drop(['SortKey', 'SeverityKey'], axis=1, inplace=True)
    return data

    #MINING
def createMiningSimData(mining_sim_sheet):
    simMiningResult = []
    for _ in range(num_runs):
        extractions = []
        energyToMine = energyForMining
        available_regular_deposits = num_deposits
        available_mega_deposits = num_mega_deposits
        if energyToMine == 0:
            extractions.append({
                        'Region': region_name,
                        'Stage': region_stage,
                        'EnergyForMining': energyToMine,
                        'Deposit': None,
                        'Category': "None",
                        'EnergySpent': 0,
                        'MineableExtracted': None,
                        'Amount': 1
                    })
        while energyToMine >= 100:
                deposit_type = random.choices(['regular', 'mega'], weights=[80, 20], k=1)[0] if available_regular_deposits > 0 and available_mega_deposits > 0 else ('regular' if available_regular_deposits > 0 else 'mega')
                if deposit_type == 'mega':
                    deposit = random.choice(mega_deposits)
                    category = 'mega'
                    energy_cost_per_mining = num_deplete_mega * mega_scanning_cost
                    available_mega_deposits -= 1
                else:
                    deposit = random.choice(regular_deposits)
                    category = 'mini'
                    available_regular_deposits -= 1
                    energy_cost_per_mining = mini_scanning_cost
                energyToMine -= energy_cost_per_mining

                mineableExtracted = choose_mineables(region_name, str("S" + str(region_stage)), deposit)
                energySpentThisExtraction = False
                for mineable in mineableExtracted:
                    extractions.append({
                        'Region': region_name,
                        'Stage': region_stage,
                        'EnergyForMining': energyToMine,
                        'Deposit': deposit,
                        'Category': category,
                        'EnergySpent': energy_cost_per_mining if not energySpentThisExtraction else 0,
                        'MineableExtracted': mineable,
                        'Amount': 1
                    })
                    energySpentThisExtraction = True
        simMiningResult.append(pd.DataFrame(extractions))

        return pd.concat(simMiningResult, ignore_index=True)
     
     #HARVESTING
def createHarvestingSimData(harvesting_sim_sheet):
    simHarvestingResult = []
    for _ in range(num_runs):
        extractions = []
        energyToHarvest = energyForHarvesting
        available_harvestables = num_harvestables
        if energyToHarvest == 0:
            extractions.append({
                    'Region': region_name,
                    'Stage': region_stage,
                    'EnergyForHarvesting': energyToHarvest,
                    'Harvestable': 0,
                    'EnergySpent': 0,
                    'HarvestableExtracted': None,
                    'EssenceExtracted': "None",
                    'BonusEssenceExtracted': "None",
                    'Amount': 1
                })

        while energyToHarvest >= 100:
            available_harvestables -= 1
            energy_cost_per_harvesting = harvesting_cost
            energyToHarvest -= energy_cost_per_harvesting

            harvestableSpot = random.choice(regular_harvestSpots) + str("_Stage" + str(region_stage))
            harvestableExtracted = choose_harvestable(region_name, str("S" + str(region_stage)), harvestableSpot)

            energySpentThisExtraction = False
            for h in harvestableExtracted:
                essenceExtracted = ""
                bonusEssenceExtracted = ""
                if random.randint(0, 100) > 60:
                    essenceExtracted = choose_essences(region_name, str("S" + str(region_stage)), harvestableSpot)
                    if random.randint(0, 100) > 95:
                        bonusEssenceExtracted = choose_essences(region_name, str("S" + str(region_stage)), harvestableSpot)

                extractions.append({
                    'Region': region_name,
                    'Stage': region_stage,
                    'EnergyForHarvesting': energyToHarvest,
                    'Harvestable': harvestableSpot,
                    'EnergySpent': energy_cost_per_harvesting if not energySpentThisExtraction else 0,
                    'HarvestableExtracted': h,
                    'EssenceExtracted': str(essenceExtracted),
                    'BonusEssenceExtracted': str(bonusEssenceExtracted),
                    'Amount': 1
                })
                energySpentThisExtraction = True

    simHarvestingResult = pd.DataFrame(extractions)
    return simHarvestingResult

#Simulate Encounters
headers = keyValueSheet.row_values(30)
shard_names_col = headers.index('Shard Type') + 1
shard_amounts_col = headers.index('Shard Amounts') + 1
shard_power_col = headers.index('Shard Power') + 1
shard_names = keyValueSheet.col_values(shard_names_col)[30:38]
shard_amounts_values = keyValueSheet.col_values(shard_amounts_col)[30:38]
shard_power_values = keyValueSheet.col_values(shard_power_col)[30:38]
shard_amounts = dict(zip(shard_names, map(int, shard_amounts_values)))
shard_powers = dict(zip(shard_names, map(int, shard_power_values)))

print("Simulating...")
simulate_population_activities()