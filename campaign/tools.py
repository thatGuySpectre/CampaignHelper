import datetime
import json
import yaml
import logging
import chromadb
import openai
import uuid
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

with open("config.yaml") as f:
    config = yaml.safe_load(f)
openai.api_key = config.get("OPENAI_API_KEY")

logger = logging.getLogger()

db = chromadb.Client(chromadb.Settings(chroma_api_impl="rest",
                                       chroma_server_host="chroma-discord",
                                       chroma_server_http_port="7123"
))

world = db.get_or_create_collection(
    name=f"{config.get('NAME')}-world",
    embedding_function=OpenAIEmbeddingFunction(api_key=openai.api_key)
)

history = db.get_or_create_collection(
    name=f"{config.get('NAME')}-history",
    embedding_function=OpenAIEmbeddingFunction(api_key=openai.api_key)
)


def world_info(**kwargs):
    if len(kwargs) != 1:
        return None

    query = kwargs.get("query")
    if query is None:
        return None

    results = world.query(query_texts=query, n_results=8)

    out = ""

    for metadata, document in zip(results["metadatas"][0], results["documents"][0]):
        if metadata is None:
            out += f"unknown document: {document}\n\n"
        else:
            out += f"{metadata.get('name')} (part {metadata.get('num')}/{metadata.get('total')}): {document}\n"

    return out


def chat_history(**kwargs):
    if len(kwargs) != 1:
        return None

    topic = kwargs.get("topic")
    if topic is None:
        return None

    results = history.query(query_texts=topic, n_results=8)

    out = ""

    for metadata, document in zip(results["metadatas"][0], results["documents"][0]):
        if metadata is None:
            out += f"unkown author: {document}\n\n"
        else:
            out += f"{metadata.get('author')} [{metadata.get('time')}] (part {metadata.get('num')}/{metadata.get('total')}): {document}\n"

    return out


def maybe_relevant(message):
    results = history.query(query_texts=message, n_results=4)
    out = ""
    for metadata, document in zip(results["metadatas"][0], results["documents"][0]):
        out += f"{metadata.get('author')} [{metadata.get('time')}] (part {metadata.get('num')}/{metadata.get('total')}): {document}\n"
    return out


def evaluate(call):
    func_name = call.get("name")
    args = call.get("arguments")

    if func_name is None or args is None:
        logger.info("name or arguments missing")
        return None

    func = TOOL_MAP.get(func_name)

    if func_name is None:
        logger.info(f"function {func_name} does not exist")
        return None

    try:
        arguments = json.loads(args)
    except json.decoder.JSONDecodeError as err:
        logger.info("invalid json")
        return None

    return func(**arguments)


def add_message(author, message):
    chunks = map_split(message)
    chunk_amount = len(chunks)

    time = datetime.datetime.now().isoformat(timespec="minutes", sep=" ")

    for i, chunk in enumerate(chunks):
        history.add(
            ids=str(uuid.uuid4()),
            documents=message,
            metadatas={"time": time, "author": author, "num": i+1, "total": chunk_amount}
        )
    db.persist()


def add_world_info(name, content):
    chunks = map_split(content, hard_min=400, hard_max=1000)
    chunk_amount = len(chunks)

    for i, chunk in enumerate(chunks):
        world.add(
            ids=str(uuid.uuid4()),
            documents=chunk,
            metadatas={"name": name, "num": i+1, "total": chunk_amount}
        )
    db.persist()


def map_split(content, hard_min=50, hard_max=400):
    split = content.split("\n\n")

    while any([len(i) > hard_max for i in split]):
        new_split = []
        steps = enumerate(split)
        for i, val in steps:
            logger.info(val)
            if len(val) > hard_max:
                for char in [".\n", ".", "  ", ";", ", ", " "]:
                    if char in val:
                        mid = len(val) // 2
                        split_index = min(val.rfind(char, 0, mid), val.find(char, mid), key=lambda x: abs(mid - x))
                        if len(val[:split_index].strip()) < hard_min or len(val[split_index:].strip()) < hard_min:
                            continue
                        new_split.append(val[:split_index+1])
                        new_split.append(val[split_index+1:])
                        break
            elif len(val) < hard_min and i < len(split) - 1:
                if len(split[i+1]) < hard_max//2:
                    new_split.append(val + split[i+1])
                    next(steps)
            else:
                if val.strip():
                    new_split.append(val.strip())
        split = new_split

    logger.debug(f"{split=}")

    return split


TOOL_MAP = {
    "world_info": world_info,
    "conversation_history": chat_history
}
TOOLS = [
    {
        "name": "world_info",
        "description": "Get information about the world, specific planets, creatures or people.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The query to use for similarity search.",
                    },
            },
        "required": ["query"],
        },
    },
    {
        "name": "conversation_history",
        "description": "Recall previous conversations with the crew. Should only be used when world_info returns no useful information.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The topic you want to remember things about",
                    },
            },
        "required": ["topic"],
        },
    },
]


