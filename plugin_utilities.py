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


def get_tools_location():
    """Get the path to the Alteryx Python SDK Tools directory."""
    return os.path.join(os.environ["APPDATA"], "Alteryx", "Tools")


# plugin
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


# plugin
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


# plugin
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


# plugin
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
