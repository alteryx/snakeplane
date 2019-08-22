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
"""Example Source Tool implementation."""

# 3rd Party Libraries
import AlteryxPythonSDK as sdk

import pandas as pd

from snakeplane.plugin_factory import PluginFactory

# Initialization of the plug in factory, used for making the AyxPlugin class
factory = PluginFactory("ExampleSourceTool")


@factory.initialize_plugin
def init(input_mgr, user_data, logger):
    """Initialize the example source tool."""
    # Get the selected value from the GUI and save it for later use in the user_data
    user_data.val = float(input_mgr.workflow_config["Value"])

    # Display info on the selected value
    logger.display_info_msg(f"The value selected is {user_data.val}")

    # This time throw an error if greater than 0.5
    if user_data.val > 0.5:
        logger.display_error_msg(f"The value selected is greater than 0.5")

    return True


@factory.process_data(
    mode="source"
)  # Input type not specified since this has no inputs
def process_data(
    output_mgr, user_data, logger
):  # I don't need an input_mgr, so it's not added to the function signature
    """Generate some data to source."""

    # Append results to records
    df = pd.DataFrame({"Value": [user_data.val]})

    # Return dictionary with data/metadata
    data_out = output_mgr["Output"]
    data_out.data = df


@factory.build_metadata
def build_metadata(output_mgr):
    """Build metadata for example source tool."""
    # This tool will output a single column with double data

    # Create a new metadata object
    metadata = output_mgr.create_anchor_metadata()

    metadata.add_column("Test", sdk.FieldType.double, source="ExampleSourceTool")

    data_out = output_mgr["Output"]
    data_out.metadata = metadata


AyxPlugin = factory.generate_plugin()
