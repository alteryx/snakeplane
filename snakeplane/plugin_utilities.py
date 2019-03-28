# Copyright (C) 2019 Alteryx, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Snakeplane plugin utilities."""

# Built in Libraries
import os
from typing import Any, Dict, List


def split_abs_path(path: str) -> List[str]:
    """Split an absolute path into its parts, doing reduction on double dots."""
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:  # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])

    drop_idxs = []
    for idx, part in enumerate(allparts):
        if part == "..":
            drop_idxs.extend([idx - 1, idx])

    ret_val = []
    for idx, part in enumerate(allparts):
        if idx not in drop_idxs:
            ret_val.append(part)

    return ret_val


def contains_path(full: str, part: str) -> bool:
    """Return a boolean indicating if the part path is a subset of the full path."""
    full_parts = split_abs_path(full)
    part_parts = split_abs_path(part)

    for idx, name in enumerate(part_parts):
        if full_parts[idx] != name:
            return False

    return True


def get_tools_location() -> str:
    """Get the path to the Alteryx Python SDK Tools directory."""
    admin_path = os.path.join(os.environ["APPDATA"], "Alteryx", "Tools")
    user_path = os.path.join(os.environ["PROGRAMDATA"], "Alteryx", "Tools")
    if contains_path(__file__, admin_path):
        return admin_path

    if contains_path(__file__, user_path):
        return user_path

    raise RuntimeError("Tool is not located in Alteryx install locations.")


def get_tool_path(tool_name: str) -> str:
    """
    Generate the path to the installed location of the specified tool.

    Parameters
    ----------
    tool_name: str
        Name of the tool

    Returns
    -------
    str
        Absolute file path to the tool specified
    """
    return os.path.join(get_tools_location(), tool_name)


def get_xml_config_gui_settings(xml_dict: Dict[Any, Any]) -> Dict[Any, Any]:
    """
    Get the tool configuration from the config XML.

    Parameters
    ----------
    xml_dict: OrderedDictionary
        Parsed XML Tool configuration

    Returns
    -------
    OrderedDict
        GUI settings extracted from the parsed XML
    """
    return xml_dict["AlteryxJavaScriptPlugin"]["GuiSettings"]


def get_xml_config_input_connections(xml_dict: Dict[Any, Any]) -> List[Dict[Any, Any]]:
    """
    Get the input connection configuration from the tool XML.

    Parameters
    ----------
    xml_dict: OrderedDictionary
        Parsed XML Tool configuration

    Returns
    -------
    List[OrderedDict]
        List where each entry corresponds to an input anchor. Each entry
        is an ordered dictionary with anchor metadata.
    """
    connections = []
    inputs = get_xml_config_gui_settings(xml_dict).get("InputConnections")
    if inputs:
        connections = inputs.get("Connection")

    if connections and not isinstance(connections, List):
        connections = [connections]

    return connections


def get_xml_config_output_connections(xml_dict: Dict[Any, Any]) -> List[Dict[Any, Any]]:
    """
    Get the output connection configuration from the tool XML.

    Parameters
    ----------
    xml_dict: OrderedDictionary
        Parsed XML Tool configuration

    Returns
    -------
    List[OrderedDict]
        List where each entry corresponds to an output anchor. Each entry
        is an ordered dictionary with anchor metadata.
    """
    if "OutputConnections" not in get_xml_config_gui_settings(xml_dict):
        return []

    connections = get_xml_config_gui_settings(xml_dict)["OutputConnections"][
        "Connection"
    ]

    if not isinstance(connections, list):
        connections = [connections]

    return connections
