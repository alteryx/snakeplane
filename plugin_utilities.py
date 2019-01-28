# Built in Libraries
import os
from typing import Any, Dict, List

# 3rd Party Libraries
try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None


def get_tools_location():
    return os.path.join(os.environ["APPDATA"], "Alteryx", "Tools")


# plugin
def get_tool_path(tool_name: str) -> str:
    """
    Generates the path to the installed location of the specified
    tool.

    Parameters
    ----------
    tool_name: str
        Name of the tool

    Returns
    ---------
    str
        Absolute file path to the tool specified
    """
    return os.path.join(get_tools_location(), tool_name)


# plugin
def get_xml_config_gui_settings(xml_dict: Dict[Any, Any]) -> Dict[Any, Any]:
    """
    Gets the Tool XML configuration given the dictionary
    generated from xmltodict and the tool Config.xml

    Parameters
    ----------
    xml_dict: OrderedDictionary
        Parsed XML Tool configuration

    Returns
    ---------
    OrderedDict
        GUI settings extracted from the parsed XML
    """
    return xml_dict["AlteryxJavaScriptPlugin"]["GuiSettings"]


# plugin
def get_xml_config_input_connections(xml_dict: Dict[Any, Any]) -> List[Dict[Any, Any]]:
    """
    Gets the Tool XML Input connection configuration given
    the dictionary generated from xmltodict and the tool Config.xml

    Parameters
    ----------
    xml_dict: OrderedDictionary
        Parsed XML Tool configuration

    Returns
    ---------
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
    Gets the Tool XML Output connection configuration given
    the dictionary generated from xmltodict and the tool Config.xml

    Parameters
    ----------
    xml_dict: OrderedDictionary
        Parsed XML Tool configuration

    Returns
    ---------
    List[OrderedDict]
        List where each entry corresponds to an output anchor. Each entry
        is an ordered dictionary with anchor metadata.
    """
    if "OutputConnections" not in get_xml_config_gui_settings(xml_dict):
        return []

    connections = get_xml_config_gui_settings(xml_dict)["OutputConnections"][
        "Connection"
    ]

    if connections is not list:
        connections = [connections]

    return connections
