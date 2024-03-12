import gspread
from oauth2client.service_account import ServiceAccountCredentials
import random
import math
import pandas as pd
import numpy as np
from collections import defaultdict

# Setup and Authorization
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

spreadsheet_key = '1OfSVkFkOfhmMN8GUiv4-cWTZQmgiWTr7Q3NRp9GpYWc' 
credentials = ServiceAccountCredentials.from_json_keyfile_name('quiet-notch-415414-04dc8df47d6d.json', scope)
gc = gspread.authorize(credentials)

# Configuration (Placeholder - Replace with actual values)
num_runs = 10
region_name = 'AB'
region_stage = 1 
energy_balance = 2500
energy_per_encounter = 1250
shardT0amount = 25
shardT1amount = 25
shardT2amount = 25
shardT3amount = 25
shardT4amount = 25
shardT5amount = 0
masterShardamount = 0
shardT0power = 50
shardT1power = 100
shardT2power = 200
shardT3power = 300
shardT4power = 400
shardT5power = 500
masterShardpower = 1000

numCaptureAttempts = 5
num_encounters = 15


# Helper Functions
def load_sheet_data(sheet_name):
    """Load data from a specified sheet."""
    sheet = gc.open_by_key(spreadsheet_key).worksheet(sheet_name)
    return sheet.get_all_records()

def load_illuvial_weights(sheet_name):
    sheet = gc.open_by_key(spreadsheet_key).worksheet(sheet_name)
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

# Function to calculate combined weights for Illuvials
def calculate_illuvial_combined_weights(illuvials_list, illuvial_weights, region, stage, encounter_type):
    combined_weights = []
    for illuvial in illuvials_list:
        # Fetch the individual weights for Stage, Tier, Affinity, and Class from the weights table
        stage_weight = illuvial_weights[(region, stage, encounter_type)]['Stage'].get('S' + str(illuvial['Stage']), 0)
        tier_weight = illuvial_weights[(region, stage, encounter_type)]['Tier'].get('T' + str(illuvial['Tier']), 0)
        affinity_weight = illuvial_weights[(region, stage, encounter_type)]['Affinity'].get(illuvial['Affinity'], 0)
        class_weight = illuvial_weights[(region, stage, encounter_type)]['Class'].get(illuvial['Class'], 0)
        
        # Calculate combined weight and append it along with the illuvial's Production_ID
        if stage_weight and tier_weight and affinity_weight and class_weight:  # Ensure no zero weights
            combined_weight = stage_weight * tier_weight * affinity_weight * class_weight
            combined_weights.append((illuvial['Production_ID'], combined_weight))
    #print("combined_weights: " + str(combined_weights))
    return combined_weights

def load_illuvials_list(sheet_name):
    sheet = gc.open_by_key(spreadsheet_key).worksheet(sheet_name)
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

# Combining Weigths for Illuvials
def get_weighted_choice(options):
    """Given a list of tuples [(illuvial_identifier, combined_weight)], return an identifier based on the weighted probability."""
    identifiers, weights = zip(*options)
    total = sum(weights)
    r = random.uniform(0, total)
    upto = 0
    for identifier, weight in zip(identifiers, weights):
        if upto + weight >= r:
            return identifier
        upto += weight
    assert False, "Shouldn't get here"

def load_capture_difficulties(sheet_name):
    sheet = gc.open_by_key(spreadsheet_key).worksheet(sheet_name)
    return sheet.get_all_records()

def calculate_capture_probability(capture_power, capture_difficulty):
    overshoot = 1.1  # 110%
    curve_strength = 0.01  # 1%
    probability = overshoot / (1 + math.exp(-curve_strength * (capture_power - capture_difficulty)))
    return probability

def choose_shard(shard_amounts, chosen_tier):
    # Choose a random shard that has a non-zero amount
    if shard_amounts:
        available_shards = [tier for tier, amount in shard_amounts.items() if int(amount) > 0 and tier == "shardT"+str(chosen_tier)]
        if not available_shards:
            return None, None  # No shards available
        chosen_shard = available_shards[0]

        shard_amounts[str(chosen_shard)] -= 1  # Deduct one shard
        return chosen_shard, shard_amounts
    else:
        return None, None

def get_capture_difficulty(capture_difficulties, tier, stage):
    # Convert tier and stage to strings if they are not already, to match the sheet format
    tier = tier
    stage = stage
    
    for difficulty in capture_difficulties:
        # Check if the current record matches the Illuvial's tier and stage
        if str(difficulty['Illuvial Tier']) == tier and str(difficulty['Illuvial Stage']) == stage:
            return difficulty['Base Capture Difficulty']  # Return the capture difficulty
    
    return None  # Return None if no matching difficulty is found

def get_encounter(self, target_power: int, region: str, stage: str, encounter_type: str):
    total_power = 0
    total_mastery_points = 0
    total_synergy_stacks = 0
    encounter_illuvials = []
    while total_power < target_power:
        chosen_illuvial = self.sample_illuvial(region=region, stage=stage, encounter_type=encounter_type)
        encounter_illuvials.append(chosen_illuvial)
        synergy_bonus = self.get_synergy_bonus(chosen_illuvials=encounter_illuvials)
        total_mastery_points += int(chosen_illuvial.loc["Mastery Points"])
        total_power = total_mastery_points * (1 + synergy_bonus)
    return encounter_illuvials

def get_synergy_bonus(chosen_illuvials: list):
    #chosen_illuvials_data = pd.DataFrame(pd.concat(chosen_illuvials, axis=1)).T
    chosen_illuvials_df = pd.DataFrame(chosen_illuvials)

    chosen_illuvials_df['Mastery Points'] = chosen_illuvials_df['Mastery Points'].astype(int)

    affinity_stacks = chosen_illuvials_df.groupby("Affinity")["Production_ID"].nunique().to_dict()
    class_stacks = chosen_illuvials_df.groupby("Class")["Production_ID"].nunique().to_dict()

    affinity_synergy_thresholds = calc_synergy_thresholds(affinity_stacks)
    class_synergy_thresholds = calc_synergy_thresholds(class_stacks)

    synergy_bonus = (affinity_synergy_thresholds + class_synergy_thresholds) * 0.2
    return synergy_bonus

def calc_synergy_thresholds(stacks: dict):
    thresholds = 0
    for synergy_name, synergy_stacks in stacks.items():
        if synergy_name in ["Fire", "Water", "Earth", "Air", "Nature", "Bulwark", "Rogue", "Fighter", "Empath", "Psion"]:
            thresholds += np.floor(synergy_stacks/3)
        else:
            if synergy_stacks > 1:
                thresholds += (synergy_stacks - 1)
            else:
                pass
    return thresholds

# Main Functions
def simulate_encounters(num_runs, region_name, region_stage, encounter_types_processed, quantity_weights_processed, illuvial_weights, illuvials_list, shard_amounts, shard_powers, capture_difficulties):
    """Simulate encounters based on the provided parameters and probabilities."""
    results = []
    encounter_illuvials = []
    encounter_index = 1  # Initialize encounter index
    target_power = get_target_power(region_stage, encounter_type) # init target power

    for run in range(1, num_runs + 1):
        currentEnergy_balance = energy_balance
        chosen_encounter_index = random.randint(1, num_encounters) 
        chosen_encounter_index2 = random.randint(1, num_encounters) 

        encounter_index = 1
        
        for _ in range(num_encounters):
            # Determine the number of Illuvials in this encounter
            # num_illuvials_in_encounter = get_weighted_choice(quantity_weights_processed)  # This needs to be adjusted if quantity_weights_processed structure changes
            
            if encounter_index == chosen_encounter_index or encounter_index == chosen_encounter_index2:
                currentEnergy_balance -= energy_per_encounter  # Deduct energy spent on this encounter

            total_power = 0
            total_mastery_points = 0
            total_synergy_stacks = 0

            while total_power < target_power:
                selected_illuvial_id = get_weighted_choice(combined_illuvial_weights)
                illuvial_record = next((illuvial for illuvial in illuvials_list if illuvial['Production_ID'] == selected_illuvial_id), None)
                if not illuvial_record:
                    continue
                
                # calculating power
                encounter_illuvials.append(illuvial_record)
                synergy_bonus = get_synergy_bonus(chosen_illuvials=encounter_illuvials)
                total_mastery_points += int(illuvial_record['Mastery Points'])
                total_power = total_mastery_points * (1 + synergy_bonus)

                # Append Illuvial data to results with the same encounter_index for Illuvials in the same encounter
                if encounter_index == chosen_encounter_index or encounter_index == chosen_encounter_index2:
                    captureAttempts = 0
                    doCapture = "Yes"
                    while doCapture == "Yes":
                        captureAttempts += 1
                        if shard_amounts:
                            chosen_shard, shard_amounts = choose_shard(shard_amounts, illuvial_record['Tier'])
                        else:
                            doCapture = "No"
                            success = "No"
                            results.append([
                                    run,
                                    region_name,
                                    region_stage,
                                    encounter_index,
                                    encounter_type,
                                    illuvial_record['Production_ID'],
                                    illuvial_record['Stage'],
                                    illuvial_record['Tier'],
                                    illuvial_record['Affinity'],
                                    illuvial_record['Class'],
                                    illuvial_record['Mastery Points'],
                                    captureAttempts,
                                    "No Shards :(",
                                    success
                                ])
                            break
                        if chosen_shard:
                            shard_power = shard_powers[chosen_shard]
                            capture_difficulty = get_capture_difficulty(capture_difficulties, illuvial_record['Tier'], illuvial_record['Stage']) 
                            capture_probability = calculate_capture_probability(shard_power, capture_difficulty)
                            success = "Yes" if random.random() < capture_probability else "No"
                            if captureAttempts >= numCaptureAttempts:
                                doCapture = "No"
                                success = "No"
                                results.append([
                                    run,
                                    region_name,
                                    region_stage,
                                    encounter_index,
                                    encounter_type,
                                    illuvial_record['Production_ID'],
                                    illuvial_record['Stage'],
                                    illuvial_record['Tier'],
                                    illuvial_record['Affinity'],
                                    illuvial_record['Class'],
                                    illuvial_record['Mastery Points'],
                                    captureAttempts,
                                    chosen_shard,
                                    success
                                ])
                            if success == "Yes":
                                results.append([
                                    run,
                                    region_name,
                                    region_stage,
                                    encounter_index,
                                    encounter_type,
                                    illuvial_record['Production_ID'],
                                    illuvial_record['Stage'],
                                    illuvial_record['Tier'],
                                    illuvial_record['Affinity'],
                                    illuvial_record['Class'],
                                    illuvial_record['Mastery Points'],
                                    captureAttempts,
                                    chosen_shard,
                                    success
                                ])
                                doCapture = "No" 
                        else:
                            # Handle case where no shard is available for capture attempt
                            pass
                else:
                    results.append([
                        run,
                        region_name,
                        region_stage,
                        encounter_index,
                        encounter_type,
                        illuvial_record['Production_ID'],
                        illuvial_record['Stage'],
                        illuvial_record['Tier'],
                        illuvial_record['Affinity'],
                        illuvial_record['Class'],
                        illuvial_record['Mastery Points'],  # Placeholder, adjust as necessary
                    ])
                    

            encounter_index += 1  # Increment encounter index after adding all Illuvials for this encounter
    
    return results


def write_to_sheet(sheet_name, data):
    """Write the simulation results to the specified Google Sheet."""
    sheet = gc.open_by_key(spreadsheet_key).worksheet(sheet_name)
    sheet.resize(rows=len(data) + 1, cols=len(data[0]) if data else 0)
    sheet.update('A2', data, value_input_option='USER_ENTERED')

def get_target_power(region_stage, encounter_type):
    for row in encounter_types:
        if row['Stage'] == region_stage and row['Encounter'] == encounter_type:
            return row['Target Power']
    return None  # Return None or raise an exception if not found

# Load data from sheets (Placeholder - Replace with actual data retrieval)
encounter_types = load_sheet_data('EncounterType_EXPORT')
quantity_weights = load_sheet_data('QuantityWeightsTable_EXPORT')
illuvial_weights = load_illuvial_weights('IlluvialWeightsTable_EXPORT')
illuvials_list = load_illuvials_list('IlluvialsList')
capture_difficulties = load_capture_difficulties('Capture')

# Shard details and powers
shard_amounts = {
    'shardT0': shardT0amount, 'shardT1': shardT1amount, 'shardT2': shardT2amount,
    'shardT3': shardT3amount, 'shardT4': shardT4amount, 'shardT5': shardT5amount,
    'masterShard': masterShardamount
}
shard_powers = {
    'shardT0': shardT0power, 'shardT1': shardT1power, 'shardT2': shardT2power,
    'shardT3': shardT3power, 'shardT4': shardT4power, 'shardT5': shardT5power,
    'masterShard': masterShardpower
}

encounter_types_processed = [(record['Encounter'], record['Weight']) for record in encounter_types]

encounter_type = get_weighted_choice(encounter_types_processed)

target_power = 0


quantity_weights_processed = [(int(k), v) for record in quantity_weights for k, v in record.items() if k.isdigit()]
combined_illuvial_weights = calculate_illuvial_combined_weights(illuvials_list, illuvial_weights, region_name, region_stage, encounter_type)
# Simulate Encounters
#results = simulate_encounters(num_runs, region_name, region_stage, encounter_types_processed, quantity_weights_processed, illuvial_weights, illuvials_list)


simulationResults = simulate_encounters(
    num_runs, 
    region_name, 
    region_stage, 
    encounter_types_processed, 
    quantity_weights_processed, 
    combined_illuvial_weights, 
    illuvials_list,
    shard_amounts,
    shard_powers, 
    capture_difficulties
)

# Write results to 'EncounterSim' sheet
write_to_sheet('EncounterSim', simulationResults)


def publicSimulateResults (num_runs, region_name, region_stage, energyForEncounter, energy_cost_per_encounter, shard_amounts_values, shard_power_values):
    num_runs = num_runs
    region_name = region_name
    region_stage = region_stage
    energy_balance = energyForEncounter
    energy_per_encounter = energy_cost_per_encounter

    simulationResults = simulate_encounters(
        num_runs, 
        region_name, 
        region_stage, 
        encounter_types_processed, 
        quantity_weights_processed, 
        combined_illuvial_weights, 
        illuvials_list,
        shard_amounts_values,
        shard_power_values, 
        capture_difficulties
    )

    write_to_sheet('EncounterSim', simulationResults)

def publicSimulateEncountersPopulation (num_runs, region_name, region_stage, energyForEncounter, energy_cost_per_encounter, shard_amounts_values, shard_power_values):
    num_runs = num_runs
    region_name = region_name
    region_stage = region_stage
    energy_balance = energyForEncounter
    energy_per_encounter = energy_cost_per_encounter

    simulationResults = simulate_encounters(
        num_runs, 
        region_name, 
        region_stage, 
        encounter_types_processed, 
        quantity_weights_processed, 
        combined_illuvial_weights, 
        illuvials_list,
        shard_amounts_values,
        shard_power_values, 
        capture_difficulties
    )

    aggregated_results = []
    run_data = defaultdict(lambda: defaultdict(int))
    illuvials_per_run = defaultdict(list)

    # Iterate over the simulationResults
    for result in simulationResults:
        run_number = result[0]
        illuvial_name = result[5]
        tier = result[6]
        stage = result[7]
        if len(result) > 11 and result[11]:
            shards_used = result[11]
        else:
            shards_used = 0

        # Increment Illuvials Captured
        run_data[run_number]['Illuvials Captured'] += 1
        illuvials_per_run[run_number].append(illuvial_name)
        run_data[run_number][f'T{tier} Illuvials'] += 1
        run_data[run_number][f'S{stage} Illuvials'] += 1
        run_data[run_number]['Shards Used'] += int(shards_used)

    # Convert the temporary dictionary to a list of dictionaries with required information
    for run_number, data in run_data.items():
        data['Illuvials'] = ', '.join(illuvials_per_run[run_number])
        aggregated_results.append(data)

    sorted_aggregated_results = sorted(aggregated_results, key=custom_sort)

    sorted_keys = ['Illuvials Captured', 'illuvial_name', 'T0 Illuvials', 'T1 Illuvials', 'T2 Illuvials', 'T3 Illuvials', 'T4 Illuvials', 'T5 Illuvials', 'S1 Illuvials', 'S3 Illuvials', 'S3 Illuvials', 'Shards Used']  # and so on for all keys
    values_only_sorted_aggregated_results = [list(map(item.get, sorted_keys)) for item in sorted_aggregated_results]

    # Replace 'None' with '0' for summation
    cleaned_results = [[0 if v is None else v for v in sublist] for sublist in values_only_sorted_aggregated_results]

    # Sum the values by their respective positions using zip and sum
    summed_results = [sum(values) for values in zip(*cleaned_results)]

    return summed_results

def custom_sort(item):
    return (item['run_number'], item['illuvial_name'], item['T0 Illuvials'], item['T1 Illuvials'])  # Add the rest of your tier keys