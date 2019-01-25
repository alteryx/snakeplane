# Snakeplane

## The Alteryx Python SDK Abstraction Layer

![alt text](./funny-snakes-on-a-plane-5.png)

Snakeplane is a toolkit to make building Python SDK tools for Alteryx simple, fun, and smooth.  This project is being created in order to support the development of the Code Free ML Tools. Snakeplane provides a way to perform rapid development of Alteryx tools, while maintaining quality. The abstraction provides lots of built functionality such as error checking on required input connections, record generation and pushing, etc.

## Overview

Snakeplane uses a framework similar to Flask. The user uses a ```PluginFactory``` class to build their plugin and through interfaces to the factory, can specify their choice of options and custom functionality.

## Example Batch Tool

```python
import pandas as pd

# Core Alteryx Python SDK Functionality
import AlteryxPythonSDK as Sdk

# Abstraction Layer
from snakeplane.plugin_factory import PluginFactory

# Create plugin factory
# NOTE: The string passed here is the name of the tool being created
# This must match the name of the tool directory in the tools directory
factory = PluginFactory("ExampleBatchTool")

# Initialize plugin
# There are three parameters for the initialization function:
# 1. workflow_config: An OrderedDict that contains the data passed to the plugin from the GUI
# 2. user_data: A catch-all location for the plugin developer to store data between
#    the initialization function call and the process_data call
# 3. logger: An object that is used by the plugin developer to raise info, warnings,
#    and errors to the Alteryx results panel
@factory.initialize_plugin
def init(workflow_config, user_data, logger):
    # workflow_config contains GUI specifications, save for later in the user_data
    user_data.workflow_config = workflow_config

    # We can produce errors or infos using the logger input
    if(False):
        logger.display_error_msg("Everythings broken.")

    # Or you can display info messages
    logger.display_info_msg("It's working!")

    # And warnings
    logger.display_warn_msg("Consider yourself warned.")


# Process the data: (specifying "batch" mode here means that all input records will be collected before processing the data and specifying input_type as dataframe means the input will be a pandas dataframe)
# There are four parameters for the process data function. The user_data
# and logger parameters are the same as listed above for the init function.
# The two new parameters are:
# 1. input_mgr: An object that is used to retrieve data/metadata from input anchors
# 2. output_mgr: An object that is used to send data/metadata to output anchors and downstream tools
@factory.process_data(mode="batch", input_type="dataframe")
def process_data(input_mgr, output_mgr, user_data, logger):
    # Gets the input anchor for the data we want, in this case there is only one input
    # anchor.
    # Since some anchors (multi-input anchors) can accept multiple inputs, the return
    # value of get_anchor is a list of anchors. In this case, there is only one, so we
    # just extract it inline.
    input_anchor = input_mgr.get_anchor("InputAnchorName")[0]

    # Get the batch data from that input as a dataframe
    # Calling get_data on an input_anchor will give you all of the data available for
    # that anchor. In this case, the specified input_type is a dataframe,
    # so the return value is a pandas dataframe
    input_data = input_anchor.get_data()

    # We can also get the alteryx types of each column in the dataframe
    col_types = input_anchor.get_col_types()

    # This tool will append a column of all zeros
    df = pd.DataFrame({'New Column': [0]*input_data.shape[0]})

    # Create output dataframe by appending our new column to the input data
    output_data = input_data.join(df)

    # Push the output data to the anchor of our choice
    output_anchor = output_mgr.get_anchor("OutputAnchorName")
    output_anchor.set_data(output_data)

# The build_metadata function takes the same parameters as the process_data function
@factory.build_metadata
def build_metadata(input_mgr, output_mgr, user_data, logger):
    # Get the input anchor as before
    input_anchor = input_mgr.get_anchor("InputAnchorName")[0]

    # Extract the input metadata
    metadata = input_anchor.get_col_metadata()

    # Add a new column that has a floating point value in it
    metadata.add_column("New Column", sdk.FieldType.float)

    # Get the output anchor
    output_anchor = output_mgr.get_anchor("Estimator")

    # Set the metadata for that anchor
    output_anchor.set_col_metadata(metadata)

# Export the plugin
AyxPlugin = factory.generate_plugin()
```

## PluginFactory

The plugin factory constructor takes the tool name as a single argument. __This name must match the directory name of the tool when installed in Alteryx.__ This is because the plugin factory interally uses this name to find the configuration XML file for the plugin, and therefore needs the path to the tool.

When using the abstraction layer, the first thing to do is to construct a new plugin factory:

```factory = PluginFactory("ExampleTool")```

Once you have completed specification of custom functionality (described below), you must export your plugin:

```AyxPlugin = factory.generate_plugin()```

__The name ```AyxPlugin``` must match exactly.__ The Python SDK expects to find a class named AyxPlugin in order to generate your plugin at run time.

## Initialize Plugin

You can specify plugin initialization behavior by creating a function with the specified signature and decorating it with ```@factory.initialize_plugin``` (For a helpful guide on Python decorators see [here](https://realpython.com/primer-on-python-decorators/)). This registers your initialization function with the plugin factory to ensure it is called at the appropriate time. Your initialization function must have a signature with three arguments. They are: ```(workflow_config, user_data, logger)```.

### workflow_config

```workflow_config``` is an ```OrderedDict``` containing the settings specified by the user from the HTML GUI. This typically will contain information that you want to use later in ```process_data```. It is recommended to store any pertinent information in ```user_data```.

### user_data

```user_data``` is a Python ```SimpleNamespace``` object that is dedicated for the plugin developer to store any desired information in. This data is persistent between the ```initialize_plugin``` call and the ```process_data``` call, as well as between calls to ```process_data``` when operating in stream mode.

### logger

The ```logger``` is an object containing methods for logging errors, warnings, and information to the Alteryx Designer canvas.

## Process Data

```process_data``` is the place for the plugin designer to put the bulk of the plugin functionality. Similarly to ```initialize_plugin```, the way a user can register their own ```process_data``` function is by using the ```@factory.process_data``` decorator. The difference in this case, is that this decorator takes the following parameters:
- ```mode```: Registers what mode the designer wants the plugin to operate in. This options for this variable are:
    - ```"batch"``` : In this mode, the plugin will aggregate input records from all input anchors, and then call the ```process_data``` function.
    - ```"stream"``` : In this mode, the plugin will call ```process_data``` every time that a record is received from any input interface. Input data will be a list representing a single row, with a value for each respective column.
- ```input_type``` (Optional) : Tells the plugin what data type the user would like on the input. The options are:
    - ```"list"``` (Default) : The input data is a list of lists (for batch) or a single list (for stream), where each row is a record and each column is a field in the record.
    - ```"dataframe"```: The input data is a pandas dataframe

The user defined ```process_data``` function must have the following signature: ```process_data(input_mgr, output_mgr, user_data)```.

### input_mgr

The ```input_mgr``` is an object through which the user can access data & metadata from the plugin input anchors. It has a single public method (```get_anchor```) which can be used to access an individual input anchor object:
- ```get_anchor(anchor_name)```: Takes a single parameter, the name of the requested input anchor as a string. Returns a corresponding a list of connections since a single anchor can accept multiple connections in some cases.

The returned value of ```get_anchor``` is an ```InputAnchor``` object, and has the following public methods that can be used to access data:
- ```get_data()```: Returns any data available on the anchor. The data type returned by this method can be a list, list of lists or a pandas data frame, depending on the what option was specified in the decorator.
- ```get_col_metadata()```: Returns a metadata object.

### output_mgr

The ```output_mgr``` is similar to the ```input_mgr```, except that it only can access output anchors. It has the same interface as ```input_mgr```:
- ```get_anchor(anchor_name)```: Returns the output anchor if it exists.

Similarly, the return value of ```get_anchor()``` for ```output_mgr``` is ```OutputAnchor```, and has the following interface for the user to output data:
- ```set_data```: Sets the data to write to the output anchor. Can be a list of lists or a dataframe.
- ```set_col_metadata```: Sets the column names of the data from a list of strings. Calling this function is not necessary if ```set_data``` is called with a data frame, since the column names are embedded in the data frame.

### user_data

```user_data``` is the same as the one specified above. It is a ```SimpleNamespace``` that can be used by the plugin designer to save any data that they wish to persist between calls to ```initialize_plugin``` and consecutive calls to ```process_data```.

The user defined ```process_data``` function must have the following signature: ```process_data(input_mgr, output_mgr, user_data, logger)```.

### logger

The ```logger``` is an object containing methods for logging errors, warnings, and information to the Alteryx Designer canvas.

## Build Metadata

```build_metadata``` is where you can specify the output metadata for your tool. It is done using a combination of the input/output managers and the ```AnchorMetadata``` object

The user defined ```build_metadata``` function must have the following signature: ```build_metadata(input_mgr, output_mgr, user_data)```.

### AnchorMetadata

This ```AnchorMetadata``` class is used to inspect metadata from input connections, and to generate metadata for output connections.

To create a new ```AnchorMetadata``` object, you can use the ```create_anchor_metadata``` function. Additionally, you can call the ```get_col_metadata``` method of an input anchor. To add a new column, call the ```add_column``` function on the object with the following signature:

```add_column(self, name, col_type, size=256, scale=0, source="", description="")```

Additionally, to inspect the metadata, call ```get_columns``` on the object to receive a list of named tuples that contain the metadata for each column on the anchor.