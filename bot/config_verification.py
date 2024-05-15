"""
To read configuration files, parse them and validate each configuration.
This module defines the following function:

- `read_and_validate_config()`: read a config file and validate all configs in it
"""

from configparser import ConfigParser
import sys

def read_and_validate_config(server_config: ConfigParser, config_file_path):
    """
    Take in a `ConfigParser` object along with the path to a config file.
    Read the file into the parser and then validate each configuration in it,
    by checking for unknown or missing keys.

    Parameters:
    - `server_config`: a `ConfigParser` object, parses a list of config files
    - `config_file_path`: a string, the path to the file containing server configurations
    """

    server_config.read(config_file_path)

    for section in server_config.sections():
        section_obj = server_config[section]
        req_keys = {"grantroles", "serverid"}
        all_keys = req_keys | {
            "deleteroles",
            "is_academic",
            "setrealname",
        }

        for key in section_obj.keys():
            if key not in all_keys:
                print(f"Unknown key: {key} in section {section}")
                return False
            req_keys.discard(key)
        if len(req_keys) != 0:
            print(f"Missing keys: {' ,'.join(req_keys)} in section {section}")
            return False
        
        print(f"{section} config is valid!")
    
    return True

if __name__ == "__main__":
    if not read_and_validate_config(ConfigParser(), "server_config.ini"):
        sys.exit(1)