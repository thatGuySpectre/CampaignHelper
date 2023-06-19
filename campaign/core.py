import openai

import tenacity
import yaml

import logging

from campaign import tools

with open("config.yaml") as f:
    config = yaml.safe_load(f)
openai.api_key = config.get("OPENAI_API_KEY")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

messages = [
    {"role": "system", "content": config.get("prompt")}
]


def query(message, author):
    global messages
    maybe_relevant = tools.maybe_relevant(message)

    prompt = config.get("PROMPT").format(history=maybe_relevant)

    messages[0]["content"] = prompt

    messages += [{"role": "user", "name": author, "content": message}]

    for i in range(5):

        response = _do_req(i)

        func = response.choices[0].message.get("function_call")

        if func:
            tool_response = tools.evaluate(func)
            if tool_response is not None:
                messages += [
                    {"role": "assistant", "content": None, "function_call": {
                            "name": response.choices[0].message.function_call.name,
                            "arguments": response.choices[0].message.function_call.arguments
                        }
                    }
                ]
                messages += [
                    {"role": "function", "name": func.name, "content": tool_response}
                ]
            else:
                continue
        else:
            messages += [
                {k: v for k, v in response.choices[0].message.items()}
            ]

            if len(messages) > config.get("MEMORY_MAX"):
                messages = messages[:1] + messages[-config.get("MEMORY_MAX"):-1]

            tools.add_message(author=author, message=message)
            tools.add_message(author="Erebos", message=response.choices[0].message.content)

            return response.choices[0].message.content


@tenacity.retry(
    retry=tenacity.retry_if_exception_type(openai.error.APIError),
    after=tenacity.after_log(logger, log_level=logging.INFO),
    stop=tenacity.stop_after_attempt(10)
)
def _do_req(i):
    logger.info("trying")
    logger.info(f'{config["GPT"]["MODEL"]} : {config["GPT"]["TEMPERATURE"]} : {tools.TOOLS} : {messages}')
    if i < 4:
        response = openai.ChatCompletion.create(
            model=config["GPT"]["MODEL"],
            functions=tools.TOOLS,
            messages=messages,
            temperature=config["GPT"]["TEMPERATURE"]
        )

    else:
        response = openai.ChatCompletion.create(
            model=config["GPT"]["MODEL"],
            messages=messages,
            temperature=config["GPT"]["TEMPERATURE"]
        )

    return response
