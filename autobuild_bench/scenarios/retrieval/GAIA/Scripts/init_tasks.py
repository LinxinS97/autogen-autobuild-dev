#
# Run this file to download the human_eval dataset, and create a corresponding testbed scenario:
# (default: ../scenarios/human_eval_two_agents_gpt4.jsonl and ./scenarios/human_eval_two_agents_gpt35.jsonl)
#

import json
import os
import sys
from huggingface_hub import snapshot_download
from autogen.agentchat.contrib.agent_builder import AgentBuilder

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

SCENARIO_DIR = os.path.realpath(os.path.join(SCRIPT_DIR, os.path.pardir))
TEMPLATES_DIR = os.path.join(SCENARIO_DIR, "Templates")
TASKS_DIR = os.path.join(SCENARIO_DIR, "Tasks")
DOWNLOADS_DIR = os.path.join(SCENARIO_DIR, "Downloads")
REPO_DIR = os.path.join(DOWNLOADS_DIR, "GAIA")
SAVE_DIR = os.path.join(SCENARIO_DIR, "Saved_agents")


def download_gaia():
    """Download the GAIA benchmark from Hugging Face."""

    if not os.path.isdir(DOWNLOADS_DIR):
        os.mkdir(DOWNLOADS_DIR)

    """Download the GAIA dataset from Hugging Face Hub"""
    snapshot_download(
        repo_id="gaia-benchmark/GAIA",
        repo_type="dataset",
        local_dir=REPO_DIR,
        local_dir_use_symlinks=True,
    )


def create_jsonl(name, tasks, files_dir, template, agent_list = None):
    """Creates a JSONL scenario file with a given name, and template path."""

    if not os.path.isdir(TASKS_DIR):
        os.mkdir(TASKS_DIR)

    with open(os.path.join(TASKS_DIR, name + ".jsonl"), "wt") as fh:
        for task in tasks:
            print(f"Converting: [{name}] {task['task_id']}")

            template_cp_list = [template]
            if len(task["file_name"].strip()) > 0:
                template_cp_list.append(
                    [
                        os.path.join(files_dir, task["file_name"].strip()),
                        os.path.join("coding", task["file_name"].strip()),
                    ]
                )

            record = {
                "id": task["task_id"],
                "template": template_cp_list,
                "substitutions": {
                    "scenario.py": {
                        "__FILE_NAME__": task["file_name"],
                        "__PROMPT__": task["Question"],
                    },
                    "expected_answer.txt": {"__EXPECTED_ANSWER__": task["Final answer"]},
                    "agent_list.txt": {"__AGENT_LIST__": json.dumps(agent_list)}
                },
            }

            fh.write(json.dumps(record).strip() + "\n")


###############################################################################
def main():
    download_gaia()
    building_task = """We need a group of experts to solve a series of complex, real-world problems. 
These tasks involve reasoning, handling multi-modal data, browsing the web, and using tools proficiently.
They need to solve the problem collaboratively and check each other's answer. Also, they can write python code themselves to help solving the task if needed.
"""

    default_llm_config = {
        "temperature": 1,
        "top_p": 0.95,
        "max_tokens": 1024,
    }

    gaia_validation_files = os.path.join(REPO_DIR, "2023", "validation")
    gaia_test_files = os.path.join(REPO_DIR, "2023", "test")

    if not os.path.isdir(gaia_validation_files) or not os.path.isdir(gaia_test_files):
        sys.exit(f"Error: '{REPO_DIR}' does not appear to be a copy of the GAIA repository.")

    # Load the GAIA data
    gaia_validation_tasks = [[], [], []]
    with open(os.path.join(gaia_validation_files, "metadata.jsonl")) as fh:
        for line in fh:
            data = json.loads(line)
            gaia_validation_tasks[data["Level"] - 1].append(data)

    gaia_test_tasks = [[], [], []]
    with open(os.path.join(gaia_test_files, "metadata.jsonl")) as fh:
        for line in fh:
            data = json.loads(line)

            # A welcome message -- not a real task
            if data["task_id"] == "0-0-0-0-0":
                continue

            gaia_test_tasks[data["Level"] - 1].append(data)

    templates = {
        "single_llm": os.path.join(TEMPLATES_DIR, "SingleLLM"),
        "two_agents": os.path.join(TEMPLATES_DIR, "TwoAgents"),
        "meta_prompt_orig": os.path.join(TEMPLATES_DIR, "MetaPrompt_orig"),
        "meta_prompt_autogen": os.path.join(TEMPLATES_DIR, "MetaPrompt_autogen"),
        "autobuild": os.path.join(TEMPLATES_DIR, "AutoBuild"),
        "meta_agent": os.path.join(TEMPLATES_DIR, "MetaAgent")
    }

    # Add coding directories if needed (these are usually empty and left out of the repo)
    for template in templates.values():
        code_dir_path = os.path.join(template, "coding")
        if not os.path.isdir(code_dir_path):
            os.mkdir(code_dir_path)
    
    # build agents
    builder = AgentBuilder(config_file_or_env='OAI_CONFIG_LIST',
                           builder_model='gpt-4-1106-preview', # you can modify the model
                           agent_model='gpt-4-1106-preview',
                           max_agents=10)
    
    _, agent_configs = builder.build(building_task, default_llm_config, coding=True)
    builder.save(f"{SAVE_DIR}/autobuild.json")

    # Create the various combinations of [models] x [templates]
    for t in templates.items():
        create_jsonl(
            f"gaia_validation_level_1__{t[0]}",
            gaia_validation_tasks[0],
            gaia_validation_files,
            t[1],
            agent_list=agent_configs
        )
        create_jsonl(
            f"gaia_validation_level_2__{t[0]}",
            gaia_validation_tasks[1],
            gaia_validation_files,
            t[1],
            agent_list=agent_configs
        )
        create_jsonl(
            f"gaia_validation_level_3__{t[0]}",
            gaia_validation_tasks[2],
            gaia_validation_files,
            t[1],
            agent_list=agent_configs
        )
        create_jsonl(
            f"gaia_test_level_1__{t[0]}",
            gaia_test_tasks[0],
            gaia_test_files,
            t[1],
            agent_list=agent_configs
        )
        create_jsonl(
            f"gaia_test_level_2__{t[0]}",
            gaia_test_tasks[1],
            gaia_test_files,
            t[1],
            agent_list=agent_configs
        )
        create_jsonl(
            f"gaia_test_level_3__{t[0]}",
            gaia_test_tasks[2],
            gaia_test_files,
            t[1],
            agent_list=agent_configs
        )


if __name__ == "__main__" and __package__ is None:
    main()
