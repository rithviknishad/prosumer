import os
import re

import yaml
from yaml.loader import SafeLoader

path_matcher = re.compile(r"\$\{([^}^{]+)\}")


def path_constructor(_loader, node):
    """Extract the matched value, expand env variable, and replace the match"""
    value = node.value
    match = path_matcher.match(value)
    env_var = match.group()[2:-1]
    return os.environ.get(env_var) + value[match.end() :]


yaml.add_implicit_resolver("!path", path_matcher, None, SafeLoader)
yaml.add_constructor("!path", path_constructor, SafeLoader)


def load_config() -> dict[str, any]:
    with open("prosumer.yaml", "r", encoding="utf-8") as file:
        return yaml.safe_load(file)
