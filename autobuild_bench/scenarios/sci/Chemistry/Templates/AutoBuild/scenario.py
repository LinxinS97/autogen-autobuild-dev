import autogen
import testbed_utils
from autogen.agentchat.contrib.agent_builder import AgentBuilder

testbed_utils.init()

PROBLEM = ""
with open("prompt.txt", "rt") as fh:
    PROBLEM = fh.read()

UNIT = ""
with open("unit.txt", "rt") as fh:
    UNIT = fh.read()

ANSWER = ""
with open("expected_answer.txt", "rt") as fh:
    ANSWER = fh.read()

AGENT_CONFIGS = ""
with open("agent_list.txt", "rt") as fh:
    AGENT_CONFIGS = fh.read()


####################
# Task parameters
max_agents = 10
config1 = '__CONFIG_LIST_PATH__'
config2 = '__CONFIG_LIST_PATH2__'
default_llm_config = {
    "temperature": 1,
    "top_p": 0.95,
    "max_tokens": 1024,
}

## build agents
logging_session_id = autogen.runtime_logging.start(config={"dbname": "logs.db"})
builder = AgentBuilder(config_file_or_env=config1,
                       builder_model_tags=["gpt-4", "0125", "1106", "claude3", "haiku"],
                       agent_model_tags=["gpt-4", "0125", "1106", "claude3", "haiku"],
                       max_agents=max_agents)
agent_list, agent_configs = builder.load(config_json=AGENT_CONFIGS)

## Run task
group_chat = autogen.GroupChat(agents=agent_list, messages=[], max_round=20, allow_repeat_speaker=agent_list[:-1] if agent_configs['coding'] is True else agent_list)
manager = autogen.GroupChatManager(
    groupchat=group_chat, code_execution_config={'use_docker': False}, llm_config={
        "config_list": autogen.config_list_from_json(config2, filter_dict={"tags": ["gpt-4", "0125", "1106", "claude3", "haiku"]}), 
        **default_llm_config
    }
)
question = """Please solve the following chemistry problem: 
{problem}
Try to approximate by python instead of exact solutions for some problems that may be difficult to calculate. 
The following python packages are pre-installed: sympy numpy scipy
Do not plot any figure.
The required unit of the answer is {unit}.
After verification, reply with the final answer in \\box{{}}."""
agent_list[0].initiate_chat(manager, message=question.format(problem=PROBLEM, unit=UNIT))

## collect response
messages = []
key = list(agent_list[-1].chat_messages.keys())[0]
chat_messages = agent_list[-1].chat_messages[key]
for item in chat_messages:
    messages.append(item)
messages.reverse()

response_with_ans = "No answer."
for msg in messages:
    if (
        msg["content"] != "TERMINATE"
        and msg["content"] != "TERMINATE."
        and msg['role'] != 'assistant'
    ):
        response_with_ans = msg["content"]
        break

# ---------between "answer_checker" and "checker_proxy"---------
# define answer checker chat

check_sys_msg = """You are a helpful AI assistant. You will use your coding and language skills to verify the answer.
You are given:
    1. A problem.
    2. A reply with the answer to the problem.
    3. A ground truth answer.
Please do the following:
1. Extract the answer in the reply: "The answer is <answer extracted>".
2. Check whether the answer in the reply matches the ground truth answer. When comparison is not obvious (for example, 3*\\sqrt(6) and 7.348), you may write code to check the answer and wait for the user to execute the code.
3. After everything is done, please choose a reply from the following options:
    - "The answer is correct."
    - "The answer is approximated but should be correct. Correct Answer: <ground truth answer> | Answer extracted: <answer extracted>."
    - "The answer is incorrect. Correct Answer: <ground truth answer> | Answer extracted: <answer extracted>."
    - "The reply doesn't contain an answer." """
checker_config_list = autogen.config_list_from_json(config2, filter_dict={"tags": ["gpt-4", "0125", "1106", "claude3", "haiku"]})
checker_llm_config = testbed_utils.default_llm_config(checker_config_list, timeout=180)
answer_checker = autogen.AssistantAgent(
    name="checker",
    llm_config=checker_llm_config,
    system_message=check_sys_msg
)
checker_proxy = autogen.UserProxyAgent(
    "checker_proxy",
    human_input_mode="NEVER",
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
    max_consecutive_auto_reply=5,
    default_auto_reply="TERMINATE",
    is_termination_msg=lambda x: x.get("content", "").lower()
    and (
        "the answer is correct" in x.get("content", "").lower()
        or "the answer is incorrect" in x.get("content", "").lower()
        or "the reply doesn't contain an answer" in x.get("content", "").lower()
        or "the answer is approximated but should be correct" in x.get("content", "").lower()
    ),
)

message_to_check = "[Problem]: " + PROBLEM + f"\n[Reply]: {response_with_ans}\n\n[Ground truth answer]: " + ANSWER
checker_proxy.initiate_chat(answer_checker, message=message_to_check)
autogen.runtime_logging.stop()

####################
testbed_utils.finalize(agents=agent_list + [answer_checker, checker_proxy])
