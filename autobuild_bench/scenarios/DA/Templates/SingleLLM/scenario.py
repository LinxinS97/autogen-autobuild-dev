import os
import json
import autogen
import testbed_utils

testbed_utils.init()

CONSTRAINT = ""
with open("constraint.txt", "rt") as fh:
    CONSTRAINT = fh.read()

FORMATS = ""
with open("format.txt", "rt") as fh:
    FORMATS = fh.read()

FILE = ""
with open("file.txt", "rt") as fh:
    FILE = fh.read()

QUESTION = ""
with open("question.txt", "rt") as fh:
    QUESTION = fh.read()

PROMPT = """Let's solve a data analysis problem. Given an absolute csv file path, you are required to answer a question following a constraint. When you have reached a final answer, conclude your response and end it with 'TERMINATE'.

FILE PATH: {file}
QUESTION: {question}
CONSTRAINT: {constraint}
After verification, reply with the final answer as the format of {formats}.
"""

ANSWER = ""
with open("expected_answer.txt", "rt") as fh:
    ANSWER = fh.read()

####################
config_list = autogen.config_list_from_json("OAI_CONFIG_LIST", filter_dict={"model": ["gpt-4-1106"]})
llm_config = testbed_utils.default_llm_config(config_list, timeout=180)

build_manager = autogen.OpenAIWrapper(config_list=config_list)
response_with_ans = build_manager.create(
    messages=[
        {
            "role": "user",
            "content": PROMPT.format(problem=PROMPT.format(file=FILE, question=QUESTION, constraint=CONSTRAINT, formats=FORMATS)),
        }
    ]
).choices[0].message.content

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

answer_checker = autogen.AssistantAgent(name="checker", llm_config=llm_config, system_message=check_sys_msg)
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

message_to_check = "Problem: " + QUESTION + f"\n\nReply: {response_with_ans}\n\nGround truth answer: " + ANSWER
checker_proxy.initiate_chat(answer_checker, message=message_to_check)


####################
testbed_utils.finalize(agents=[answer_checker, checker_proxy])
