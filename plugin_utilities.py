# Built in Libraries
import os
from typing import Union, Any, List, Optional, cast, Set, Dict, Tuple
import pdb

# 3rd Party Libraries
try:
    import pandas as pd
except:
    pd = None

# Alteryx Libraries
import AlteryxPythonSDK as sdk


def get_tools_location():
    return f"{os.environ['APPDATA']}\\Alteryx\\Tools"


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
    return f"{get_tools_location()}\\{tool_name}"


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
    connections = get_xml_config_gui_settings(xml_dict)["InputConnections"][
        "Connection"
    ]

    if type(connections) is not list:
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


# plugin
def get_class_attributes(cls: object) -> List[str]:
    """
    Gets all of the attributes of a class

    Parameters
    ----------
    cls: object
        Any object

    Returns
    ---------
    List[str]
        List of attribute names
    """
    return [
        a for a in dir(cls) if not a.startswith("__") and not callable(getattr(cls, a))
    ]
