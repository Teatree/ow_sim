from oauth2client.service_account import ServiceAccountCredentials
import random
import math
import pandas as pd
import numpy as np
from collections import defaultdict
from bondingCurveCalc import calculateBondingCurveValue
from line_profiler import profile

# Configuration (Placeholder - Replace with actual values)
num_runs = 10
# region_name = 'AB'
# region_stage = 1
print("Encounter") 

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

bonrdingcurve_values = {}
numCaptureAttempts = 5
num_encounters = 15


# Function to calculate combined weights for Illuvials

def calculate_illuvial_combined_weights(illuvials_list, illuvial_weights, region, stage, encounter_type, illuvial_capture_counts):
    combined_weights = []

    capture_counts_dict = {illuvial['Production_ID']: illuvial['CaptureCount'] for illuvial in illuvial_capture_counts}

    for illuvial in illuvials_list:
        production_id = illuvial['Production_ID']
        if production_id == 'Production_ID':
            continue

        # Fetch the individual weights for Stage, Tier, Affinity, and Class from the weights table
        stage_weight = illuvial_weights[(region, stage, encounter_type)]['Stage'].get('S' + str(illuvial['Stage']), 0)
        tier_weight = illuvial_weights[(region, stage, encounter_type)]['Tier'].get('T' + str(illuvial['Tier']), 0)
        affinity_weight = illuvial_weights[(region, stage, encounter_type)]['Affinity'].get(illuvial['Affinity'], 0)
        class_weight = illuvial_weights[(region, stage, encounter_type)]['Class'].get(illuvial['Class'], 0)
        
        capture_count = capture_counts_dict.get(production_id, 0)
        bonding_curve_value = calculateBondingCurveValue(capture_count, illuvial.get('Stage'), illuvial.get('Tier'))
        
        # TODO: Iterate here and see if the list of bonding curves contains 
        
        # Calculate combined weight and append it along with the illuvial's Production_ID
        if stage_weight and tier_weight and affinity_weight and class_weight:  # Ensure no zero weights
            combined_weight = stage_weight * tier_weight * affinity_weight * class_weight * bonding_curve_value
            combined_weights.append((illuvial['Production_ID'], combined_weight))
    #print("combined_weights: " + str(combined_weights))
    return combined_weights


# Combining Weigths for Illuvials

def get_weighted_choice(options):
    """Given a list of tuples [(illuvial_identifier, combined_weight)], return an identifier based on the weighted probability."""
    identifiers, weights = zip(*options)

    total = sum(weights)
    r = random.uniform(0, total)
    upto = 0
    for identifier, weight in zip(identifiers, weights):
        if upto + weight >= r:
            # TODO: Add probability of HOLO or DARK HOLO
            return identifier
        upto += weight
    assert False, "Shouldn't get here"


def calculate_capture_probability(capture_power, capture_difficulty, bonding_curve_value):
    overshoot = 1.1  # 110%
    curve_strength = 0.01  # 1%
    probability = overshoot / (1 + math.exp(-curve_strength * (capture_power - capture_difficulty)))
    probability *= bonding_curve_value
    return probability


def choose_shard(shard_amounts, chosen_tier):
    # Choose a random shard that has a non-zero amount
    if shard_amounts:
        available_shards = [tier for tier, amount in shard_amounts.items() if int(amount) > 0 and tier == "Shard T"+str(chosen_tier)]
        if not available_shards:
            return None, shard_amounts  # No shards available
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

def simulate_encounters(num_runs, regionNames, regionStages, illuvial_weights, encounter_types, encounter_type, 
                        illuvials_list, shard_amounts_vals, shard_powers, capture_difficulties, energy_per_encounter, illuvial_capture_counts, energy_balance):
    """Simulate encounters based on the provided parameters and probabilities."""
    illuvialCaptured = []
    illuvialCapturedTiers = []
    illuvialCapturedStages = []
    shardsUsedForCapture = []

    num_encounters = math.floor(energy_balance / energy_per_encounter)
    
    for _ in range(num_runs):
        region_name = regionNames[_]
        region_stage = regionStages[_]

        combined_illuvial_weights = calculate_illuvial_combined_weights(illuvials_list, illuvial_weights, region_name, region_stage, encounter_type, illuvial_capture_counts)
        target_power = get_target_power(region_stage, encounter_type, encounter_types)

        shard_amounts = shard_amounts_vals
        currentEnergy_balance = energy_balance

        for _ in range(num_encounters):
            encounter_illuvials = []
            total_power = 0
            total_mastery_points = 0

            while total_power < target_power:
                selected_illuvial_id = get_weighted_choice(combined_illuvial_weights)
                illuvial_record = next((illuvial for illuvial in illuvials_list if illuvial['Production_ID'] == selected_illuvial_id), None)
                if illuvial_record:
                    encounter_illuvials.append(illuvial_record)
                    synergy_bonus = get_synergy_bonus(chosen_illuvials=encounter_illuvials)
                    total_mastery_points += int(illuvial_record['Mastery Points'])
                    total_power = total_mastery_points * (1 + synergy_bonus)

            win = random.random() < 0.8
            if win:
                currentEnergy_balance -= energy_per_encounter
                illuvialsToCapture = [illuvial['Production_ID'] for illuvial in encounter_illuvials]
                illuvialsToCaptureTiers = [illuvial['Tier'] for illuvial in encounter_illuvials]
                illuvialsToCaptureStages = [illuvial['Stage'] for illuvial in encounter_illuvials]

                for index in range(len(illuvialsToCapture)):
                    captureAttempts = 0
                    while shard_amounts and captureAttempts < numCaptureAttempts:
                        chosen_shard, shard_amounts = choose_shard(shard_amounts, illuvialsToCaptureTiers[index])

                        captureAttempts += 1

                        if chosen_shard:
                            shardsUsedForCapture.append(chosen_shard)
                            shard_power = shard_powers[chosen_shard]
                            capture_difficulty = get_capture_difficulty(capture_difficulties, illuvialsToCaptureTiers[index], illuvialsToCaptureStages[index])

                            capture_count = next((illuvial['CaptureCount'] for illuvial in illuvial_capture_counts if illuvial['Production_ID'] == illuvialsToCapture[index]), 0)
                            bonding_curve_value = calculateBondingCurveValue(capture_count, illuvialsToCaptureStages[index], illuvialsToCaptureTiers[index])

                            capture_probability = calculate_capture_probability(shard_power, capture_difficulty, bonding_curve_value)
                            success = random.random() < capture_probability
                            if success:
                                illuvialCaptured.append(illuvialsToCapture[index])
                                illuvialCapturedTiers.append(illuvialsToCaptureTiers[index])
                                illuvialCapturedStages.append(illuvialsToCaptureStages[index])
                                break

    return illuvialCaptured, illuvialCapturedTiers, illuvialCapturedStages, shardsUsedForCapture, shard_amounts

# def write_to_sheet(sheet_name, data):
#     """Write the simulation allEncountersInRegion to the specified Google Sheet."""
#     sheet = gc.open_by_key(spreadsheet_key).worksheet(sheet_name)
#     sheet.resize(rows=len(data) + 1, cols=len(data[0]) if data else 0)
#     sheet.update('A2', data, value_input_option='USER_ENTERED')


def get_target_power(region_stage, encounter_type, encounter_types):
    for row in encounter_types:
        if row['Stage'] == region_stage and row['Encounter'] == encounter_type:
            return row['Target Power']
    return None  # Return None or raise an exception if not found

# Load data from sheets (Placeholder - Replace with actual data retrieval)
# encounter_types = load_sheet_data('EncounterType_EXPORT')
# quantity_weights = load_sheet_data('QuantityWeightsTable_EXPORT')
# illuvial_weights = load_illuvial_weights('IlluvialWeightsTable_EXPORT')
# illuvials_list = load_illuvials_list('IlluvialsList')
# capture_difficulties = load_capture_difficulties('Capture')

# Shard details and powers
#shard_amounts = {
#    'Shard T0': shardT0amount, 'Shard T1': shardT1amount, 'Shard T2': shardT2amount,
#    'Shard T3': shardT3amount, 'Shard T4': shardT4amount, 'Shard T5': shardT5amount,
#    'Master Shard': masterShardamount
#}
# shard_powers = {
#     'Shard T0': shardT0power, 'Shard T1': shardT1power, 'Shard T2': shardT2power,
#     'Shard T3': shardT3power, 'Shard T4': shardT4power, 'Shard T5': shardT5power,
#     'Master Shard': masterShardpower
# }

# encounter_types_processed = [(record['Encounter'], record['Weight']) for record in encounter_types]

# encounter_type = get_weighted_choice(encounter_types_processed)

# target_power = 0


#quantity_weights_processed = [(int(k), v) for record in quantity_weights for k, v in record.items() if k.isdigit()]
#combined_illuvial_weights = calculate_illuvial_combined_weights(illuvials_list, illuvial_weights, region_name, region_stage, encounter_type)
# Simulate Encounters
#allEncountersInRegion = simulate_encounters(num_runs, region_name, region_stage, encounter_types_processed, quantity_weights_processed, illuvial_weights, illuvials_list)

# TEST RUN
#simulationResults = simulate_encounters(
    #num_runs, 
    #region_name, 
    #region_stage, 
    #encounter_types_processed, 
    #quantity_weights_processed, 
    #combined_illuvial_weights, 
    #illuvials_list,
    #shard_amounts,
    #shard_powers, 
    #capture_difficulties,
    #illuvial_capture_counts
#)

#write_to_sheet('EncounterSim', simulationResults)


# def publicSimulateResults (num_runs, region_name, region_stage, energyForEncounter, energy_cost_per_encounter, shard_amounts_values, shard_power_values, illuvial_capture_counts):
#     num_runs = num_runs
#     region_name = region_name
#     region_stage = region_stage
#     energy_balance = energyForEncounter
#     energy_per_encounter = energy_cost_per_encounter

#     simulationResults = simulate_encounters(
#         num_runs, 
#         region_name, 
#         region_stage, 
#         encounter_types_processed, 
#         quantity_weights_processed, 
#         combined_illuvial_weights, 
#         illuvials_list,
#         shard_amounts_values,
#         shard_power_values, 
#         capture_difficulties,
#         illuvial_capture_counts,
#         energy_balance
#     )

#     write_to_sheet('EncounterSim', simulationResults)


def publicSimulateEncountersPopulation(num_runs, regionNames, regionStages, energyForEncounter, energy_cost_per_encounter, shard_amounts_values, shard_power_values, 
                                       illuvial_capture_counts, encounter_types, illuvial_weights, illuvials_list, capture_difficulties):
    energy_balance = energyForEncounter
    energy_per_encounter = energy_cost_per_encounter
    encounter_types_processed = [(record['Encounter'], record['Weight']) for record in encounter_types]
    encounter_type = get_weighted_choice(encounter_types_processed)

    illuvialCaptured, illuvialCapturedTiers, illuvialCapturedStages, shardsUsedForCapture, shardAmounts = simulate_encounters(
        num_runs,
        regionNames,
        regionStages,
        illuvial_weights,
        encounter_types,
        encounter_type,
        illuvials_list,
        shard_amounts_values,
        shard_power_values,
        capture_difficulties,
        energy_per_encounter,
        illuvial_capture_counts,
        energy_balance
    )

    # Calculating sums and counts
    sum_illuvialCaptured = len(illuvialCaptured)
    sum_shardsUsedForCapture = len(shardsUsedForCapture)

    # Joining lists into strings
    illuvialCaptured_str = ", ".join(illuvialCaptured) # can't use this because of 50000 chars in cell limit
    shardsUsedForCapture_str = ", ".join(shardsUsedForCapture) # can't use this because of 50000 chars in cell limit

    # Counting occurrences of each Tier and Stage
    tier_counts = {f"T{tier}": illuvialCapturedTiers.count(str(tier)) for tier in range(6)}  # Tiers T0-T5
    stage_counts = {f"S{stage}": illuvialCapturedStages.count(str(stage)) for stage in range(1, 4)}  # Stages S1-S3

    # Building the final list containing the required information
    result = [
        sum_illuvialCaptured,
        illuvialCaptured_str,
        tier_counts["T0"], tier_counts["T1"], tier_counts["T2"], tier_counts["T3"], tier_counts["T4"], tier_counts["T5"],
        stage_counts["S1"], stage_counts["S2"], stage_counts["S3"], 
        shardsUsedForCapture_str,
        sum_shardsUsedForCapture
    ]

    return result, shardAmounts


def custom_sort(item):
    return (item['run_number'], item['illuvial_name'], item['T0 Illuvials'], item['T1 Illuvials'])  # Add the rest of your tier keys