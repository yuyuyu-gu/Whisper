"""这个模块提供了两个函数：一个用于加载服务器配置文件，另一个用于读取环境变量。加载服务器配置文件的函数使用了lru_cache装饰器来缓存结果，以提高性能。读取环境变量的函数也使用了lru_cache装饰器，并且在读取环境变量之前会加载指定的dotenv文件。
配置文件位置："""
from dotenv import load_dotenv
import os
from modules.utils.paths import SERVER_CONFIG_PATH, SERVER_DOTENV_PATH
from modules.utils.files_manager import load_yaml, save_yaml

import functools


@functools.lru_cache
def load_server_config(config_path: str = SERVER_CONFIG_PATH) -> dict:
    if os.getenv("TEST_ENV", "false").lower() == "true":
        server_config = load_yaml(config_path)
        server_config["whisper"]["model_size"] = "tiny"
        server_config["whisper"]["compute_type"] = "float32"
        save_yaml(server_config, config_path)

    return load_yaml(config_path)


@functools.lru_cache
def read_env(key: str, default: str = None, dotenv_path: str = SERVER_DOTENV_PATH):
    load_dotenv(dotenv_path)
    value = os.getenv(key, default)
    return value

