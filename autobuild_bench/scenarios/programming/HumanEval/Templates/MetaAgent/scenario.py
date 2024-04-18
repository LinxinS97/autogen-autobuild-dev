import autogen
import testbed_utils
from datetime import datetime
from autogen.agentchat.contrib.meta_agent import MetaAgent
from autogen.agentchat.contrib.meta_user_proxy_agent import MetaUserProxyAgent

# NOTE:
# This scenario runs Human Eval in a slightly unconventional way:
# The agents have access to the unit tests, and can keep trying
# until they pass.

testbed_utils.init()
##############################

work_dir = "coding"

# Read the prompt
PROMPT = ""
with open("prompt.txt", "rt") as fh:
    PROMPT = fh.read()


####################
# Task parameters
general_llm_config = {
    "temperature": 0,
    "config_list": autogen.config_list_from_json("OAI_CONFIG_LIST", filter_dict={"model": ["gpt-4-1106"]}),
}

nested_mode_config = {
    "autobuild_init_config": {
        "config_file_or_env": "OAI_CONFIG_LIST",
        "builder_model": "gpt-4-1106",
        "agent_model": "gpt-4-1106",
    },
    "autobuild_build_config": {
        "default_llm_config": {
            "temperature": 1,
            "top_p": 0.95,
            "max_tokens": 1500,
        },
        "code_execution_config": {
            "last_n_messages": 1,
            "use_docker": False,
            "timeout": 10,
            "work_dir": work_dir,
        },
        "coding": True,
        "library_path_or_json": "/home/ubuntu/disklinxin/llm/autogen-autobuild-dev/autobuild_bench/scenarios/agent_library.json",
    },
    "autobuild_tool_config": {
        "tool_corpus": "/home/ubuntu/disklinxin/llm/autogen-autobuild-dev/tools/tool_description.tsv",
        "tool_root": "/home/ubuntu/disklinxin/llm/autogen-autobuild-dev/tools",
        "retriever": "all-mpnet-base-v2",
    },
    "group_chat_config": {"max_round": 15},
    "group_chat_llm_config": general_llm_config.copy(),
}

## build agents
logging_session_id = autogen.runtime_logging.start(config={"dbname": "logs.db"})

meta_agent = MetaAgent(name="meta_agent", llm_config=general_llm_config, nested_mode="autobuild")
meta_user_proxy = MetaUserProxyAgent(
    name="meta_user_proxy",
    nested_mode_config=nested_mode_config,
    code_execution_config={
        "last_n_messages": 2,
        "use_docker": False,
        "timeout": 10,
        "work_dir": work_dir,
    },  # you can modify the setting
    # modify the path
    agent_config_save_path="__AGENT_SAVE_PATH__"
)

## Run task
meta_user_proxy.initiate_chat(
    meta_agent,
    message=f"""The following python code imports the `run_tests(candidate)` function from my_tests.py, and runs it on the function `__ENTRY_POINT__`. This will run a set of automated unit tests to verify the correct implementation of `__ENTRY_POINT__`. 
However, `__ENTRY_POINT__` is only partially implemented in the code below. 
Complete the implementation of `__ENTRY_POINT__` and output a new stand-alone code block that contains everything needed to run the tests, including: importing `my_tests`, calling `run_tests(__ENTRY_POINT__)`, as well as __ENTRY_POINT__'s complete definition, such that this code block can be run directly in Python.

```python
from my_tests import run_tests

{PROMPT}

# DO NOT MODIFY. 
# Run the unit tests
# It will return "all test passed" if the code pass all tests.
run_tests(__ENTRY_POINT__)
```

""")
autogen.runtime_logging.stop()
####################
testbed_utils.finalize(agents=[meta_agent, meta_user_proxy])