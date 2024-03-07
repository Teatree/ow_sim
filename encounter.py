import json
import pandas as pd
import numpy as np
import math
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Define the scope
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

# Update the path to your service account credentials JSON file
creds = ServiceAccountCredentials.from_json_keyfile_name('quiet-notch-415414-04dc8df47d6d.json', scope)
spreadsheet_key = '1OfSVkFkOfhmMN8GUiv4-cWTZQmgiWTr7Q3NRp9GpYWc' 

# Authorize with gspread
gc = gspread.authorize(creds)


class EconomySimulator:

    def __init__(self) -> None:
        self.player_energy = 100 
        self.energy_per_encounter = 10 
        self.encounter_limit = 10 
        self.economy_gsheet = gc.open_by_key(spreadsheet_key)
        #self.economy_gsheet = gc.open_by_url('https://docs.google.com/spreadsheets/d/1DeTl13vKN7wBjRc0BuaDNTcapiTSTXeomZfe8ODcQX8/edit#gid=818814824')
        #self.arena_gsheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1DeTl13vKN7wBjRc0BuaDNTcapiTSTXeomZfe8ODcQX8")
        self.illuvial_data, self.encounter_quantity_data, self.encounter_type_data, self.illuvial_weights = self.prepare_data()
        self.affinity_distribution = self.get_affinity_distribution()
        self.extended_illuvial_data = self.extend_illuvial_data(self.illuvial_data, self.illuvial_weights)
        self.player_region_probs = {
            "BS": 0.3,
            "AB": 0.3,
            "CW": 0.4
        }
        self.player_stage_probs = {
            "0": 1
        }

    def get_affinity_distribution(self):
      affinity_cols = ["Water", "Earth", "Fire", "Nature", "Air"]
      return self.illuvial_weights.loc[:, affinity_cols].copy().astype(int)

    def extend_illuvial_data(self, illuvial_data: pd.DataFrame, illuvial_weights: pd.DataFrame) -> pd.DataFrame:
      """
      Goal of this function is to have the sampling weight per illuvial per region per stage per encounter type for easy lookup
      """
      returned_columns = [
          "Region",
          "Region Stage",
          "Encounter Type",
          "Illuvial Name",
          "Illuvial Line",
          "Stage",
          "Tier",
          "Affinity",
          "Class",
          "Mastery Points",
          "TotalWeight"
      ]
      illuvial_data["tmp"] = 1
      illuvial_weights["tmp"] = 1
      m = pd.merge(illuvial_data, illuvial_weights.reset_index(), on=["tmp"])
      m["Tier"] = "T" + m["Tier"]
      m["Stage"] = "S" + m["Stage"]
      m.loc[(m.Class == "None"), "Class"] = "Cls_None"
      for var in ["Tier", "Stage", "Class"]:
        col_name = var + "Weight"
        proto_weights = m.loc[:, m[var]].values
        m[col_name] = proto_weights[np.arange(len(proto_weights)), np.arange(len(proto_weights))].astype(int)
      m["TotalWeight"] = m["TierWeight"] * m["StageWeight"] * m["ClassWeight"]
      m = m[returned_columns]
      m = m.set_index(["Region", "Region Stage", "Encounter Type", "Affinity"]).sort_index()
      print("Calculating weights for each (region, region stage, encounter type, illuvial) complete")
      return m

    def run_session_simulation(self, n: int):
      total_captures = []
      for _ in range(n):
        chosen_region = self.sample_region()
        chosen_stage = self.sample_stage()
        session_captures = self.session_sim(region=chosen_region, stage=chosen_stage, n_runs=10)
        total_captures.extend(session_captures)
      s = pd.Series(total_captures)
      return s.value_counts()

    def sample_region(self):
      region = np.random.choice(a=list(self.player_region_probs.keys()), p=list(self.player_region_probs.values()))
      return region

    def sample_stage(self):
      stage = np.random.choice(a=list(self.player_stage_probs.keys()), p=list(self.player_stage_probs.values()))
      return stage

    def sample_encounters(self, n_samples: int, region: str = None, stage: str = None, encounter_type_config: str = None, target_power: int = None):
      if region is None:
        raise NotImplementedError("No region sampling functionality in place, please input region ID")
      if stage is None:
        raise NotImplementedError("No stage sampling functionality in place, please input stage")
      sim_illuvials = []
      if encounter_type_config is not None:
        encounter_type, target_power = self.get_target_power(encounter_type=encounter_type_config, stage=stage)
      for i in range(n_samples):
        if (encounter_type_config is None):
          encounter_type, target_power = self.sample_encounter_type(stage=stage)
        if (encounter_type not in ["Mini Encounter", "Mega Encounter"]):
          raise NotImplementedError(f"No encounter of name: {encounter_type} possible, only 'Mini Encounter' or 'Mega Encounter'")
        encounter_illuvials=self.get_encounter(target_power=target_power, region=region, stage=stage, encounter_type=encounter_type)
        #encounter_illuvials=self.get_encounter(region=region, stage=stage, encounter_type=encounter_type)
        encounter_illuvials["SimID"] = i
        sim_illuvials.append(encounter_illuvials)
      return pd.concat(sim_illuvials)

    def session_sim(self, region: str, stage: str, n_runs: int):
        all_runs_data = []  # List to hold data of all runs
        
        for run_index in range(1, n_runs + 1):
            # Reset player energy at the start of each run
            self.player_energy = 100  # Assuming player energy is reset for each run
            encounter_limit = self.encounter_limit
            
            run_data = []  # List to hold data for this run
            encounters_done = 0
            
            while encounters_done < encounter_limit and self.player_energy >= 10:
                encounters_done += 1
                encounter_type, target_power = self.sample_encounter_type(stage=stage)
                encounter_illuvials = self.get_encounter(target_power=target_power, region=region, stage=stage, encounter_type=encounter_type)
                captured_illuvials = self.simulate_captures(encounter_illuvials=encounter_illuvials)
                
                # Calculate energy balance after this encounter
                self.player_energy -= 10
                energy_balance = self.player_energy
                
                # Append encounter data to run data
                for illuvial in captured_illuvials:
                    run_data.append([run_index, encounters_done, energy_balance, illuvial])
            
            all_runs_data.extend(run_data)
            print("all_runs_data: " + str(all_runs_data[2]))
        
        return all_runs_data

    def simulate_captures(self, encounter_illuvials):
      captured_illuvials = []
      for illuvial in encounter_illuvials:
        if np.random.uniform() < 0.35:
          captured_illuvials.append(illuvial)
        else:
          pass
      return captured_illuvials

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
      encounter_df = pd.concat(encounter_illuvials, axis=1).T
      return encounter_df

    def get_synergy_bonus(self, chosen_illuvials: list):
      chosen_illuvials_data = pd.DataFrame(pd.concat(chosen_illuvials, axis=1)).T
      affinity_stacks = chosen_illuvials_data.groupby("Affinity")[["Illuvial Line"]].nunique()["Illuvial Line"].to_dict()
      class_stacks = chosen_illuvials_data.groupby("Class")[["Illuvial Line"]].nunique()["Illuvial Line"].to_dict()
      affinity_synergy_thresholds = self.calc_synergy_thresholds(affinity_stacks)
      class_synergy_thresholds = self.calc_synergy_thresholds(class_stacks)
      synergy_bonus = (affinity_synergy_thresholds + class_synergy_thresholds) * 0.2
      return synergy_bonus

    def calc_synergy_thresholds(self, stacks: dict):
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

    def sample_illuvial(self, region: str, stage: int, encounter_type: str):
      chosen_affinity = self.sample_affinity(region=region, stage=stage, encounter_type=encounter_type)

      remaining_aff_choices = self.extended_illuvial_data.loc[(region, stage, encounter_type, chosen_affinity)].reset_index().copy()
      none_aff_choices = self.extended_illuvial_data.loc[(region, stage, encounter_type, "None")].reset_index().copy()
      all_choices = pd.concat([remaining_aff_choices, none_aff_choices]).reset_index(drop=True)

      choice_index = np.random.choice(a=all_choices.index.values, p=all_choices["TotalWeight"].values/all_choices["TotalWeight"].values.sum())
      return all_choices.loc[choice_index]

    def prepare_data(self):
      illuvial_data = self.get_illuvial_data(self.economy_gsheet)  # Use self.economy_gsheet directly within the method
      encounter_quantity_data = self.get_encounter_quantity_dist(self.economy_gsheet)
      encounter_type_data = self.get_encounter_type_dist(self.economy_gsheet)
      illuvial_weights = self.get_illuvial_weights_dist(self.economy_gsheet)
      return illuvial_data, encounter_quantity_data, encounter_type_data, illuvial_weights
    
    def get_illuvial_data(self, economy_gsheet):
        data = economy_gsheet.worksheet("IlluvialsList").get_all_values()
        df = pd.DataFrame(data[2:], columns=data[1])
        df = df.rename(columns={"": "Illuvial Name"})
        cols = ["Illuvial Name", "Illuvial Line", "Stage", "Tier", "Affinity", "Class", "Mastery Points"]
        illuvial_data = df[cols].copy()
        return illuvial_data

    def get_encounter_quantity_dist(self, economy_sheets):
      sheet_data = economy_sheets.worksheet("QuantityWeightsTable_EXPORT").get_all_values()
      df = pd.DataFrame(sheet_data[1:], columns=sheet_data[0]).set_index(["Region", "Stage"]).astype(int)
      return df

    def get_encounter_type_dist(self, economy_sheets):
      sheet_data = economy_sheets.worksheet("EncounterType_EXPORT").get_all_values()
      df = pd.DataFrame(sheet_data[1:], columns=sheet_data[0]).set_index(["Stage"])
      return df

    def get_illuvial_weights_dist(self, economy_sheets):
      sheet_data = economy_sheets.worksheet("IlluvialWeightsTable_EXPORT").get_all_values()
      df = pd.DataFrame(sheet_data[1:], columns=sheet_data[0]).set_index(["Region", "Region Stage", "Encounter Type"])
      return df

    def sample_affinity(self, region: str, stage: str, encounter_type: str):
      aff_dist = self.affinity_distribution.loc[(region, stage, encounter_type), :]
      chosen_aff = np.random.choice(a=aff_dist.index.values, p=aff_dist.values/aff_dist.values.sum())
      return chosen_aff

    def sample_encounter_quantity(self, region: str, stage: int):
      filtered_dist = self.encounter_quantity_data.loc[(region, stage)].copy()
      chosen_illuvial_node_quantity = np.random.choice(a=filtered_dist.index.values, p=filtered_dist.values/filtered_dist.values.sum())
      return chosen_illuvial_node_quantity

    def get_target_power(self, encounter_type: str, stage: int):
      target_power_source = self.encounter_type_data.reset_index().copy()
      target_power = target_power_source.loc[(target_power_source.Encounter == encounter_type) & (target_power_source.Stage == str(stage)), "Target Power"].values
      return encounter_type, int(target_power[0])

    def sample_encounter_type(self, stage: int):
      filtered_dist = self.encounter_type_data.loc[str(stage), ["Encounter", "Weight"]].set_index("Encounter")["Weight"].astype(int)
      chosen_encounter_type = np.random.choice(a=filtered_dist.index.values, p=filtered_dist.values/filtered_dist.values.sum())
      target_power = int(self.encounter_type_data.reset_index().set_index(["Stage", "Encounter"]).loc[(str(stage), chosen_encounter_type)]["Target Power"])
      return chosen_encounter_type, target_power
    
    def write_encounters_to_sheet(self, encounters):
        encounter_sim_sheet = self.economy_gsheet.worksheet('EncounterSim')
        encounter_sim_sheet.batch_clear(["A2:Z"])
        
        encounters_list = [[item.item() if isinstance(item, np.generic) else item for item in row] for row in encounters.reset_index().values]
        print("encounter_list: " + str(encounters_list[1]))

        header = encounters.columns.tolist()
        data_for_writing = [header] + encounters_list
        
        encounter_sim_sheet.update('A1', values=data_for_writing, value_input_option='USER_ENTERED')

def simulateEncounters(region, regionStage, runs):
  sim = EconomySimulator()

  region = region
  assert region in list(sim.player_region_probs.keys()), f"Region acronym not known, try one of {sim.player_region_probs.keys()}"
  assert isinstance(region, str), "Region input not a string"

  stage = str(regionStage)
  assert stage in ["0", "1", "2", "3"], f"Stage input not known, should be 0-3"
  assert isinstance(stage, str)

  n_samples = runs

  encounters = sim.sample_encounters(n_samples=n_samples, region=region, stage=stage, encounter_type_config="Mega Encounter")
  sim.write_encounters_to_sheet(encounters)
  print(encounters) 

  print(str(sim.run_session_simulation(10)))

  # For grouping and counting, convert the result to string for pretty printing
  #encounter_summary = encounters.groupby(["Encounter Type", "Illuvial Name"])[["SimID"]].count().to_string()
  #print(encounter_summary)