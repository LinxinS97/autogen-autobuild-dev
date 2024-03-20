#
# Run this file to download the human_eval dataset, and create a corresponding testbed scenario:
# (default: ../scenarios/human_eval_two_agents_gpt4.jsonl and ./scenarios/human_eval_two_agents_gpt35.jsonl)
#

import requests
import tarfile
import json
import os
import re
from autogen.agentchat.contrib.agent_builder import AgentBuilder

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

SCENARIO_DIR = os.path.realpath(os.path.join(SCRIPT_DIR, os.path.pardir))
TEMPLATES_DIR = os.path.join(SCENARIO_DIR, "Templates")
TASKS_DIR = os.path.join(SCENARIO_DIR, "Tasks")
DOWNLOADS_DIR = os.path.join(SCENARIO_DIR, "Downloads")
SAVE_DIR = os.path.join(SCENARIO_DIR, "Saved_agents")

SELECTED_CHEM_PROBLEMS = [
    "../scibench/dataset/original/quan.json", # 42
    "../scibench/dataset/original/quan_sol.json",
    "../scibench/dataset/original/chemmc.json", # 48
    "../scibench/dataset/original/chemmc_sol.json",
    "../scibench/dataset/original/atkins.json", # 123
    "../scibench/dataset/original/atkins_sol.json",
    "../scibench/dataset/original/matter.json", # 59
    "../scibench/dataset/original/matter_sol.json",
]

SELECTED_PHY_PROBLEMS = [
    "../scibench/dataset/original/fund.json", # 83
    "../scibench/dataset/original/fund_sol.json",
    "../scibench/dataset/original/thermo.json", # 84
    "../scibench/dataset/original/thermo_sol.json",
    "../scibench/dataset/original/class.json", # 54
    "../scibench/dataset/original/class_sol.json",
]


def load_data():
    """Load SCI Chemistry data.
    Return a JSON dictionary of selected problems."""

    selected_problems = dict()
    for file in SELECTED_CHEM_PROBLEMS:
        problems = json.load(open(file))
        selected_problems[file] = problems

    return selected_problems


def create_jsonl(name, problems, template, agent_list = None):
    """Creates a JSONL scenario file with a given name, dictionary of Chemistry problems, and template path."""

    # Create a task directory if it doesn't exist
    if not os.path.isdir(TASKS_DIR):
        os.mkdir(TASKS_DIR)

    # Create the jsonl file
    with open(os.path.join(TASKS_DIR, name + ".jsonl"), "wt") as fh:
        for item in problems.items():
            data = item[1]

            task_id = item[0].replace("MATH/", "").replace(".json", "").replace("/", "_")
            print(f"Converting: [{item[0]}] {task_id}")

            record = {
                "id": task_id,
                "template": os.path.join(os.path.pardir, template),
                "substitutions": {
                    "prompt.txt": {"__PROMPT__": data["problem"]},
                    "expected_answer.txt": {"__ANSWER__": data["solution"]},
                    "agent_list.txt": {"__AGENT_LIST__": json.dumps(agent_list)},
                },
            }

            fh.write(json.dumps(record).strip() + "\n")


###############################################################################
def main():
    problems = load_data()

    building_task = """We need a group of experts to solve some scientific problems.
Those problems are in the fields of Chemistry.
They need to solve the problem collaboratively and check each other's answer. Also, they can write python code themselves to help solving the task if needed.
"""

    # list all directories in the Templates directory
    # and populate a dictionary with the name and path
    templates = {}
    for entry in os.scandir(TEMPLATES_DIR):
        if entry.is_dir():
            templates[re.sub(r"\s", "", entry.name)] = entry.path

    default_llm_config = {
        "temperature": 1,
        "top_p": 0.95,
        "max_tokens": 1024,
    }

    ## build agents
    builder = AgentBuilder(config_file_or_env='OAI_CONFIG_LIST',
                           builder_model='gpt-4-1106',
                           agent_model='gpt-4-1106',
                           max_agents=10)
    _, agent_configs = builder.build(building_task, default_llm_config, coding=True)

    if not os.path.isdir(SAVE_DIR):
        os.mkdir(SAVE_DIR)

    builder.save(f"{SAVE_DIR}/autobuild.json")

    for t in templates.items():
        create_jsonl(f"sci_chem_{t[0]}", problems, t[1], agent_list=agent_configs)

if __name__ == "__main__" and __package__ is None:
    main()
