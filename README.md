# SnakePlane

## The Alteryx Python SDK Abstraction Layer

![alt text](./SnakePlane.jpg)

Snakeplane is a toolkit to make building Python SDK tools for Alteryx simple, fun, and smooth. Snakeplane provides a way to perform rapid development of Alteryx tools, while maintaining quality. The abstraction provides lots of built functionality such as error checking on required input connections, record generation and pushing, etc.

## Support

Copyright 2019 Alteryx Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Setup

Snakeplane is designed to be used with the Alteryx Python SDK in Alteryx Designer v2018.4+.

For examples on how to develop tools/leverage a built in build system, please see the **pilot** directory.

## Issues

Any issues found should be reported as GitHub issues on this repository.

## Overview

Snakeplane uses a framework similar to Flask. The user uses a `PluginFactory` class to build their plugin and through interfaces to the factory and can specify their choice of options and custom functionality.

There are three functions that a developer must define when using snakeplane.

1. `initialize_plugin`: This function defines behavior that happens a single time at the initialization of the tool. This area is typically used to validate settings from the GUI, and do any required variable initialization.

2. `process_data`: This function defines the behvior used to generate output records from inputs (when present).

3. `build_metadata`: One of the things that makes the Alteryx Designer Platform so powerful is the propagation of metadata at configuration time. As a result, tool developers must specify the schema for the output data in a separate location that can be used at configuration time in Designer to propagate this metadata to downstream tools.

Following is an example tool that implements these three functions.

## Example Batch Tool

```python
import pandas as pd

# Core Alteryx Python SDK Functionality
import AlteryxPythonSDK as sdk

# Abstraction Layer
from snakeplane.plugin_factory import PluginFactory

# Create plugin factory
# NOTE: The string passed here is the name of the tool being created
# This must match the name of the tool in the tools directory
factory = PluginFactory("ExampleBatchTool")

# Use the factory initialize_plugin decorator to register this function with snakeplane
@factory.initialize_plugin
def init(input_mgr, user_data, logger) -> bool:
    # We can access Alteryx data items from the workflow_config attribute of the input_mgr
    # The workflow_config is a dictionary of items.
    setting = input_mgr.workflow_config["ExampleSetting"]

    # We can produce errors or infos using the logger input
    if(int(setting) < 10):
        logger.display_error_msg("An error has occurred, setting less than 10.")
        return False

    # Or you can display info messages
    logger.display_info_msg(f"Setting is {setting}")

    # And warnings
    if "ExampleSetting2" not in input_mgr.workflow_config:
        logger.display_warn_msg("Setting2 not available.")


# Process the data:
# Again, decorate with a factory method to register this function.
# The parameters for this decorators specify:
# mode: (Options)
#   "batch": all records accumulates and process_data called once
#   "stream": process_data is called any time a record is recieved by this tool
#   "source": process_data is called once to generate records. This should only
#             be used when there are no input anchors
# input_type: (Options)
#   "dataframe": data retrieved from input anchors will be in the form of a pandas dataframe
#   "list": data retrieved from input anchors will be a list of lists
@factory.process_data(mode="batch", input_type="dataframe")
def process_data(input_mgr, output_mgr, user_data, logger):
    # Gets the input anchor for the data we want, in this case there is only one input
    # anchor.
    # Since some anchors (multi-input anchors) can accept multiple inputs, the return
    # value of accessing an anchor by name is a list of connections. In this case, there is
    # only one, so we just extract it inline.
    # NOTE: The input/output anchor names must match those specified in tools config XML file.
    input_anchor = input_mgr["InputAnchorName"]
    input_connection = input_anchor[0]

    # Get the batch data from that input as a dataframe
    # Calling data on an input connection will give you all of the data available for
    # that anchor. In this case, the specified input_type is a dataframe, so the return
    # value is a pandas dataframe.
    input_data = input_connection.data

    # This tool will append a column of all zeros
    df = pd.DataFrame({'New Column': [0]*input_data.shape[0]})

    # Create output dataframe by appending our new column to the input data
    output_data = input_data.join(df)

    # Push the output data to the anchor of our choice
    output_anchor = output_mgr["OutputAnchorName"]
    output_anchor.data = output_data

# The build_metadata function takes the same parameters as the process_data function
@factory.build_metadata
def build_metadata(input_mgr, output_mgr, user_data, logger):
    # Get the input anchor as before
    input_anchor = input_mgr.data("InputAnchorName")
    input_connection = input_anchor[0]

    # Extract the input metadata
    metadata = input_connection.metadata

    # Add a new column that has a floating point value in it
    metadata.add_column("New Column", sdk.FieldType.float)

    # Get the output anchor
    output_anchor = output_mgr["OutputAnchorName"]

    # Set the metadata for that anchor
    output_anchor.metadata = metadata

# Export the plugin.
AyxPlugin = factory.generate_plugin()
```

## PluginFactory

The plugin factory constructor takes the tool name as a single argument. **This name must match the directory name of the tool when installed in Alteryx.** This is because the plugin factory interally uses this name to find the configuration XML file for the plugin, and therefore needs the path to the tool.

When using the abstraction layer, the first thing to do is to construct a new plugin factory:

`factory = PluginFactory("ExampleTool")`

Once you have completed specification of custom functionality (described below), you must export your plugin:

`AyxPlugin = factory.generate_plugin()`

**The name `AyxPlugin` must match exactly.** The Python SDK expects to find a class named AyxPlugin in order to generate your plugin at run time.

## Initialize Plugin

You can specify plugin initialization behavior by creating a function with the specified signature and decorating it with `@factory.initialize_plugin` (For a helpful guide on Python decorators see [here](https://realpython.com/primer-on-python-decorators/)). This registers your initialization function with the plugin factory to ensure it is called at the appropriate time.

## Process Data

`process_data` is the place for the plugin designer to put the bulk of the plugin functionality. Similarly to `initialize_plugin`, the way a user can register their own `process_data` function is by using the `@factory.process_data` decorator. The difference in this case, is that this decorator takes the following parameters:

- `mode`: Registers what mode the designer wants the plugin to operate in. This options for this variable are:

  - `"batch"` : In this mode, the plugin will aggregate input records from all input anchors, and then call the `process_data` function.
  - `"stream"` : In this mode, the plugin will call `process_data` every time that a record is received from any input interface. Input data will be a list representing a single row, with a value for each respective column.

- `input_type` (Optional) : Tells the plugin what data type the user would like on the input. The options are:

  - `"list"` (Default) : The input data is a list of lists (for batch) or a single list (for stream), where each row is a record and each column is a field in the record.
  - `"dataframe"`: The input data is a pandas dataframe

## Build Metadata

`build_metadata` is where you can specify the output metadata for your tool. It is done using a combination of the input/output managers and the `AnchorMetadata` object

## Function inputs

The `initialize_plugin`,`process_data`, and `build_metadata` functions may accept any combination of the following inputs:

### input_mgr

The `input_mgr` is an object through which the user can access data & metadata from the plugin input anchors. It can be treated as a Python dictionary for the purpose of retrieving input anchors, i.e. with an input anchor name of `example`, one can get the `example` anchor by calling `input_mgr["example"]`. The return value of this is a list of `InputAnchors`, described below.

The `input_mgr` also has several other helpful properties:

1. `tool_id -> int`: The tool ID of the current tool.

2. `workflow_config -> OrderedDict`: The configuration of Alteryx data items registered through the GUI SDK.

### output_mgr

The `output_mgr` is similar to the `input_mgr`, except that it only can access output anchors. It has the same interface as `input_mgr` in terms of dictionary-like access to anchors, except that the return value is only a single `OutputAnchor` object instead of a list of `InputAnchor`.

The `output_mgr` also has several helpful properties/methods:

1. `get_temp_file_path()`: Method that creates a temporary file that only exists for the lifetime of a running workflow. Returns the path to the file.

2. `create_anchor_metadata()`: Method that creates a new anchor metadata object. Details below.

### user_data

`user_data` is a `SimpleNamespace` that can be used by the plugin designer to save any data that they wish to persist between calls to `initialize_plugin`, `build_metadata` and consecutive calls to `process_data`.

### logger

The `logger` is an object containing methods for logging errors, warnings, and information to the Alteryx Designer canvas.

It contains the following methods:

1. `display_info_msg(msg: str)`: Prints an info message to Alteryx designer.

2. `display_warn_msg(msg: str)`: Prints a warning message to Alteryx designer.

3. `display_error_msg(msg: str)`: Prints an error message to Alteryx designer.

### workflow_config

`workflow_config` is an `OrderedDict` containing the settings specified by the user from the HTML GUI. This typically will contain setting information that you want to use in `process_data`.

`user_data` is a Python `SimpleNamespace` object that is dedicated for the plugin developer to store any desired information in. This data is persistent between the `initialize_plugin` call and the `process_data` call, as well as between calls to `process_data` when operating in stream mode.

## Class Descriptions:

### InputAnchor (also called AyxPluginInterface)

Used to retrieve data and metadata for a given input anchor.

Properties:

1. `data -> [List[List[Any]] or pandas.DataFrame]`: Contains the record data on the anchor. Is either a list of lists of a pandas dataframe depending on the `input_type` setting of process data. This data is read only since a downstream tool cannot affect its incoming data.

2. `metadata -> AnchorMetadata`: Contains the anchor metadata for this anchor. This metadata is read only since a downstream tool cannot affect its incoming metadata.

### OutputAnchor

Used to retrieve and set data and metadata for a given output anchor.

Properties:

1. `data -> [List[List[Any]] or pandas.DataFrame]`: Contains the record data on the anchor. Can be a list of lists of a pandas dataframe. This tool can set the data for the output anchor in the `process_data` function.

2. `metadata -> AnchorMetadata`: Contains the anchor metadata for this anchor. This metadata is read only since a downstream tool cannot affect its incoming metadata.

### AnchorMetadata

The `AnchorMetadata` class contains all the metadata for a given input/output anchor and contains helper methods for inspecting/creating those settings.

To create a new `AnchorMetadata` object, you can use the `create_anchor_metadata` method of the `output_mgr`.

Properties:

1. `columns -> List[ColumnMetadata]`: Contains the list of `ColumnMetadata` objects.

Methods:

1. `add_column(name: str, col_type: AlteryxSdk.FieldType, size: Optional(int), scale: Optional(int), source: Optional(str), description: Optional(str)) -> None`: A method for adding a new column to the AnchorMetadata. The only two required inputs are the column name and column type. The name may be any string that is unique from other column names, and the type must be one of the supported Alteryx SDK FieldTypes, described below under **Alteryx SDK Field Types**.

2. `index_of(name: str) -> int`: Gets the column index of the column name specified. Returns `None` if the column does not exist.

3. `get_column_by_name(name: str) -> ColumnMetadata`: Gets the `ColumnMetadata` object for a given column name.

4. `get_column_names() -> List[str]`: Gets a list of the available column names.

### ColumnMetadata

The `ColumnMetadata` class contains all of the metadata for a single column of data. Each object has the following properties:

1. `name -> str`: (Required) Name of the column.

2. `type -> Sdk.FieldType`: (Required) Type of the column.

3. `size -> int`: (Optional) Number of characters for strings, or size in bytes for blob and spatial types. Ignored for primitive types.

4. `scale -> int`: (Optional) Scaling factor for fixed decimal types. Ignored for other data.

5. `source -> str`: (Optional) Source of the data.

6. `description -> str`: (Optional) Description of the column.

The descriptions for these properties can also be found [here](https://help.alteryx.com/developer/current/Python/use/RecordInfoClass.htm?tocpath=SDKs%7CBuild%20Custom%20Tools%7CPython%20SDK%7CClasses%7CRecordInfo%7C_____0#add_fiel).

## Alteryx SDK Field Types

All Alteryx FieldTypes must be referenced using the `AlteryxPythonSDK` dependency. These can be found as properties of `AlteryxPythonSDK.FieldType`. The following types are supported as properties of this object: `boolean,byte, int16, int32, int64, fixeddecimal, float, double, string, wstring, v string, v_wstring, date, time, datetime, and blob`. NOTE: spatial objects are not supported at this point.

Descriptions of these field types can be found [here](https://help.alteryx.com/developer/current/Python/use/FieldClass.htm?tocpath=SDKs%7CBuild%20Custom%20Tools%7CPython%20SDK%7CClasses%7C_____3) and [here](https://help.alteryx.com/current/Reference/DataFieldType.htm).
