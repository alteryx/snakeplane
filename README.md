# Snakeplane
### The Alteryx Python SDK Abstraction Layer

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
factory = PluginFactory("ExampleBatchTool")

# Initialize plugin
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


# Process the data (specify "batch" mode here, specifying input_type as dataframe
# makes the "get_data" function on anchors return pandas dataframes)
@factory.process_data(mode="batch", input_type="dataframe")
def process_data(input_mgr, output_mgr, user_data, logger):
    # Gets the input anchor for the data we want
    input_anchor = input_mgr.get_anchor("InputAnchorName")

    # Get the batch data from that input as a dataframe
    input_data = input_anchor.get_data()

    # We can also get the alteryx types of each column in the dataframe
    col_types = input_anchor.get_col_types()

    # This tool will append a column of all zeros 
    df = pd.DataFrame({'Zeros': [0]*input_data.shape[0]})

    # The type of this column will be a double
    col_types.append(Sdk.FieldType.double)

    # Create output dataframe by appending our new column to the input data
    output_data = input_data.join(df)

    # Push the output data to the anchor of our choice
    output_anchor = output_mgr.get_anchor("OutputAnchorName")
    output_anchor.set_data(output_data)
    output_anchor.set_col_types(col_types)
    
# Export the plugin
AyxPlugin = factory.generate_plugin()
```

## PluginFactory
INSERT DOCSTRING HERE

The plugin factory constructor takes the tool name as a single argument. __This name must match the directory name of the tool when installed in Alteryx.__ This is because the plugin factory interally uses this name to find the configuration XML file for the plugin, and therefore needs the path to the tool.

When using the abstraction layer, the first thing to do is to construct a new plugin factory:

```factory = PluginFactory("ExampleTool")```

Once you have completed specification of custom functionality (described below), you must export your plugin:

```AyxPlugin = factory.generate_plugin()```

__The name ```AyxPlugin``` must match exactly.__ The Python SDK expects to find a class named AyxPlugin in order to generate your plugin at run time.

## Initialize Plugin
You can specify plugin initialization behavior by creating a function with the specified signature and decorating it with ```@factory.initialize_plugin``` (For a helpful guide on Python decorators see [here](https://realpython.com/primer-on-python-decorators/)). This registers your initialization function with the plugin factory to ensure it is called at the appropriate time. Your initialization function must have a signature with three arguments. They are: ```(workflow_config, user_data, logger)```. 
#### logger
The ```logger``` is an object containing methods for logging errors, warnings, and information to the Alteryx Designer canvas.
#### workflow_config
```workflow_config``` is an ```OrderedDict``` containing the settings specified by the user from the HTML GUI. This typically will contain information that you want to use later in ```process_data```. It is recommended to store any pertinent information in ```user_data```. 
#### user_data
```user_data``` is a Python ```SimpleNamespace``` object that is dedicated for the plugin developer to store any desired information in. This data is persistent between the ```initialize_plugin``` call and the ```process_data``` call, as well as between calls to ```process_data``` when operating in stream mode.

## Process Data
INSERT DOCSTRING HERE

```process_data``` is the place for the plugin designer to put the bulk of the plugin functionality. Similarly to ```initialize_plugin```, the way a user can register their own ```process_data``` function is by using the ```@factory.process_data``` decorator. The difference in this case, is that this decorator takes the following parameters:
- ```mode```: Registers what mode the designer wants the plugin to operate in. This options for this variable are:
    - ```"batch"``` : In this mode, the plugin will aggregate input records from all input anchors, and then call the ```process_data``` function. 
    - ```"stream"``` : In this mode, the plugin will call ```process_data``` every time that a record is received from any input interface. Input data will be a list representing a single row, with a value for each respective column. 
- ```input_type``` (Optional) : Tells the plugin what data type the user would like on the input. The options are:
    - ```"list"``` (Default) : The input data is a list of lists (for batch) or a single list (for stream), where each row is a record and each column is a field in the record.
    - ```"dataframe"```: The input data is a pandas dataframe

The user defined ```process_data``` function must have the following signature: ```process_data(input_mgr, output_mgr, user_data)```.

#### input_mgr
The ```input_mgr``` is an object through which the user can access data & metadata from the plugin input anchors. It has a single public method (```get_anchor```) which can be used to access an individual input anchor object:
- ```get_anchor(anchor_name)```: Takes a single parameter, the name of the requested input anchor as a string. Returns the corresponding anchor if it exists.

The returned value of ```get_anchor``` is an ```InputAnchor``` object, and has the following public methods that can be used to access data:
- ```get_data()```: Returns any data available on the anchor. The data type returned by this method can be a list, list of lists or a pandas data frame, depending on the what option was specified in the decorator.
- ```get_col_names()```: Returns a list of the column names from the data.
- ```get_col_types()```: Returns a list of the column types as per the Python SDK.

#### output_mgr
The ```output_mgr``` is similar to the ```input_mgr```, except that it only can access output anchors. It has the same interface as ```input_mgr```:
- ```get_anchor(anchor_name)```: Returns the output anchor if it exists.

Similarly, the return value of ```get_anchor()``` for ```output_mgr``` is ```OutputAnchor```, and has the following interface for the user to output data:
- ```set_data(data)```: Sets the data to write to the output anchor. Can be a list of lists or a dataframe. 
- ```set_col_names(col_names)```: Sets the column names of the data from a list of strings. Calling this function is not necessary if ```set_data``` is called with a data frame, since the column names are embedded in the data frame.
- ```set_col_types(col_types)```: Sets the column types from a list of types accessed from the Alteryx Python SDK library.

#### user_data
```user_data``` is the same as the one specified above. It is a ```SimpleNamespace``` that can be used by the plugin designer to save any data that they wish to persist between calls to ```initialize_plugin``` and consecutive calls to ```process_data```.