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
"""Example stream tool implementation."""

# 3rd Party Libraries
import AlteryxPythonSDK as sdk

from snakeplane.plugin_factory import PluginFactory

# Initialization of the plug in factory, used for making the AyxPlugin class
factory = PluginFactory("ExampleStreamTool")


@factory.initialize_plugin
def init(input_mgr, user_data, logger):
    """Initialize the example tool."""

    # Get the selected value from the GUI and save it for later use in the user_data
    user_data.val = float(input_mgr.workflow_config["Value"])

    # Display info on the selected value
    logger.display_info_msg(f"The value selected is {user_data.val}")

    # Throw a warning if greater than 0.5
    if user_data.val > 0.5:
        logger.display_warn_msg(f"The value selected is greater than 0.5")

    return True


@factory.process_data(mode="stream", input_type="list")
def process_data(input_mgr, output_mgr, user_data, logger):
    """Run alpha-beta filtering and stream the results."""
    # Get the input anchor
    input_anchor = input_mgr["Input"][0]

    # Get the input data. Since we're streaming, this is only a single row
    # Since we specified the input type to be "list", it will be a list
    data = input_anchor.data

    # Append our value to the data
    data.append(user_data.val)

    # Assign to the output
    output_anchor = output_mgr["Output"]
    output_anchor.data = data


@factory.build_metadata
def build_metadata(input_mgr, output_mgr, user_data, logger):
    """Build metadata for this example tool."""
    # Set up the metadata, we're adding a column of floats
    input_anchor = input_mgr["Input"][0]
    metadata = input_anchor.metadata

    # Add the new column
    metadata.add_column("Test", sdk.FieldType.float)

    # Assign the metadata to the output
    output_anchor = output_mgr["Output"]
    output_anchor.metadata = metadata


AyxPlugin = factory.generate_plugin()
