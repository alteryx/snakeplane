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
"""Base classes for plugin, input/output anchors/managers."""

# Built in Libraries
import copy
import os
import sys
from collections import OrderedDict, UserDict
from functools import partial
from types import SimpleNamespace
from typing import Any, List, Tuple, Union

# Alteryx Libraries
import AlteryxPythonSDK as sdk

# 3rd Party Libraries
try:
    import pandas as pd
except ImportError:
    pd = None

# Custom libraries
import snakeplane.interface_utilities as interface_utils
import snakeplane.plugin_utilities as plugin_utils

import xmltodict


class AyxPlugin:
    """Base plugin class to be modified by snakeplane."""

    def __init__(
        self,
        n_tool_id: int,
        alteryx_engine: sdk.AlteryxEngine,
        output_anchor_mgr: sdk.OutputAnchorManager,
    ) -> None:
        # Initialization data
        self._engine_vars = SimpleNamespace()
        self._engine_vars.n_tool_id = n_tool_id
        self._engine_vars.alteryx_engine = alteryx_engine
        self._engine_vars.output_anchor_mgr = output_anchor_mgr
        self._raised_missing = False

        # Plugin State vars
        self._state_vars = SimpleNamespace(
            initialized=False,
            input_anchors={},
            output_anchors={},
            config_data=None,
            required_input_names=[],
        )

        # Pull in the config XML data from conf file using the name of the tool
        xml_files = [
            file
            for file in os.listdir(plugin_utils.get_tool_path(self.tool_name))
            if file.lower().endswith(".xml")
        ]
        with open(
            os.path.join(plugin_utils.get_tool_path(self.tool_name), xml_files[0])
        ) as fd:
            self._state_vars.config_data = xmltodict.parse(fd.read())

        # Plugin Error Methods
        self.logging = SimpleNamespace(
            display_error_msg=partial(
                self._engine_vars.alteryx_engine.output_message,
                self._engine_vars.n_tool_id,
                sdk.EngineMessageType.error,
            ),
            display_warn_msg=partial(
                self._engine_vars.alteryx_engine.output_message,
                self._engine_vars.n_tool_id,
                sdk.EngineMessageType.warning,
            ),
            display_info_msg=partial(
                self._engine_vars.alteryx_engine.output_message,
                self._engine_vars.n_tool_id,
                sdk.EngineMessageType.info,
            ),
        )

        # Default to no inputs or outputs
        for connection in plugin_utils.get_xml_config_input_connections(
            self._state_vars.config_data
        ):
            self._state_vars.input_anchors[connection["@Name"]] = []

            # Track names of the inputs that are required for this tool to run
            if connection["@Optional"] == "False":
                self._state_vars.required_input_names.append(connection["@Name"])

        for connection in plugin_utils.get_xml_config_output_connections(
            self._state_vars.config_data
        ):
            self._state_vars.output_anchors[connection["@Name"]] = OutputAnchor()

        # Custom data
        self.user_data = SimpleNamespace()

        # Configure managers, this must occur last so the instance
        # is properly configured
        self.input_manager = InputManager(self)
        self.output_manager = OutputManager(self)

    @property
    def initialized(self) -> bool:
        """Getter for plugin initialization state."""
        return self._state_vars.initialized

    @initialized.setter
    def initialized(self, value: bool) -> None:
        """Setter for plugin initialization state."""
        self._state_vars.initialized = bool(value)

    @property
    def update_only_mode(self) -> bool:
        """Getter for if designer is in update only mode."""
        return (
            self._engine_vars.alteryx_engine.get_init_var(
                self._engine_vars.n_tool_id, "UpdateOnly"
            )
            == "True"
        )

    @property
    def all_inputs_completed(self) -> bool:
        """
        Check that all required inputs have successfully completed.

        Parameters
        ----------
        current_plugin : object
            An AyxPlugin object

        Returns
        -------
        bool
            Boolean indication of if all inputs have completed.
        """
        all_inputs_completed = True
        if self.initialized:
            for name in self._state_vars.required_input_names:
                connections = self._state_vars.input_anchors[name]
                if len(connections) == 0 or not all(
                    [connection.completed for connection in connections]
                ):
                    all_inputs_completed = False
        else:
            all_inputs_completed = False
        return all_inputs_completed

    @property
    def all_required_inputs_initialized(self) -> bool:
        """Getter for checking if all required inputs have been initialized."""
        for anchor_name in self._state_vars.required_input_names:
            input = self._state_vars.input_anchors[anchor_name]
            if not input or not all([connection.initialized for connection in input]):
                return False

        return True

    def update_sys_path(self) -> None:
        """Update the sys path to include the current tools libs."""
        # Add lib to sys path
        tool_path = plugin_utils.get_tool_path(self.tool_name)
        sys.path.append(tool_path)
        sys.path.append(os.path.join(tool_path, "Lib", "site-packages"))

    def assert_all_inputs_connected(self) -> bool:
        """Raise an error if there are any missing input connections."""
        for anchor_name in self._state_vars.required_input_names:
            input = self._state_vars.input_anchors[anchor_name]
            if not input:
                if not self._raised_missing:
                    self.logging.display_error_msg("Missing Incoming Connection(s).")
                    self._raised_missing = True
                return False

        return True

    def save_output_anchor_refs(self) -> None:
        """Save all references to output anchors."""
        # Get references to the output anchors
        for anchor_name in self._state_vars.output_anchors:
            self._state_vars.output_anchors[
                anchor_name
            ]._handler = self._engine_vars.output_anchor_mgr.get_output_anchor(
                anchor_name
            )

    def save_interface(self, name: str, interface: object) -> None:
        """Save the interface internally."""
        self._state_vars.input_anchors[name].append(interface)

    def update_progress(self, d_percentage: float) -> None:
        """Update the progress on this anchor."""
        self._engine_vars.alteryx_engine.output_tool_progress(
            self._engine_vars.n_tool_id, d_percentage
        )  # Inform the Alteryx engine of the tool's progress.

        for _, anchor in self._state_vars.output_anchors.items():
            # Inform the downstream tool of this tool's progress.
            anchor._handler.update_progress(d_percentage)

    def close_all_outputs(self) -> None:
        """Force all output anchors to close."""
        # Close all output anchors
        for _, anchor in self._state_vars.output_anchors.items():
            anchor._handler.close()

        # Checks whether connections were properly closed.
        for anchor_name in self._state_vars.output_anchors:
            self._state_vars.output_anchors[anchor_name]._handler.assert_close()

    def push_all_output_records(self) -> None:
        """
        For each output anchor on the plugin, flush all the output records.

        Parameters
        ----------
        current_plugin: object
            The plugin for which to flush output records

        Returns
        -------
        None
        """
        for _, output_anchor in self._state_vars.output_anchors.items():
            output_anchor.push_records(self)

    def push_all_metadata(self) -> None:
        """Pushes all output anchor metadata downstream."""
        for _, anchor in self._state_vars.output_anchors.items():
            anchor.push_metadata(self)

    def clear_accumulated_records(self) -> None:
        """
        Clear all accumulated records from all plugin interfaces.

        Parameters
        ----------
        plugin: object
            The plugin to clear all records from

        Returns
        -------
        None
            This function has side effects on plugin, and therefore has no return
        """
        for _, anchor in self._state_vars.input_anchors.items():
            for connection in anchor:
                connection._interface_record_vars.record_list_in = []

    def create_record_info(self) -> sdk.RecordInfo:
        """Create a new record info object."""
        return sdk.RecordInfo(self._engine_vars.alteryx_engine)


class AyxPluginInterface:
    """Input interface base definition."""

    def __init__(self, parent: object, name: str) -> None:
        self.parent = parent
        self.name = name
        self.initialized = False

        self._interface_record_vars = SimpleNamespace(
            record_info_in=None, record_list_in=[], column_metadata=None
        )

        self._interface_state = SimpleNamespace(
            input_complete=False, d_progress_percentage=0, data_processing_mode="batch"
        )

    @property
    def metadata(self) -> object:
        """Input metadata getter."""
        return copy.deepcopy(self._interface_record_vars.column_metadata)

    @property
    def data(self) -> Union[object, List[List[Any]]]:
        """Input data getter."""
        if (
            self.parent.process_data_mode == "stream"
            and self.parent.process_data_input_type == "list"
        ):
            return self._interface_record_vars.record_list_in[0]
        elif self.parent.process_data_input_type == "list":
            return self._interface_record_vars.record_list_in
        else:
            try:
                return pd.DataFrame(
                    self._interface_record_vars.record_list_in,
                    columns=self.metadata.get_column_names(),
                )
            except ImportError:
                err_str = """The Pandas library must be installed to
                            allow dataframe as input_type."""
                self.parent.logging.display_error_msg(err_str)
                raise ImportError(err_str)

    @property
    def completed(self) -> bool:
        """Interface completed getter."""
        return self._interface_state.input_complete

    @completed.setter
    def completed(self, val) -> None:
        """Interface completed setter."""
        self._interface_state.input_complete = val

    @property
    def anchor_metadata(self):
        """Anchor metadata getter."""
        return self._interface_record_vars.column_metadata

    @anchor_metadata.setter
    def anchor_metadata(self, val) -> None:
        """Anchor metadata setter."""
        self._interface_record_vars.column_metadata = val

    @property
    def record_info(self):
        """Getter for Input Anchor record_info object."""
        return self._interface_record_vars.record_info_in

    def get_values_from_record(
        self: object, in_record: object
    ) -> Tuple[List[Union[int, float, bool, str, bytes]], dict]:
        """
        Get a list of values from an incoming record.

        Parameters
        ----------
        interface_obj : object
            An AyxPluginInterface object for the current interface

        in_record: object
            An Alteryx RecordRef object for the record to be processed
        Returns
        ---------
        Tuple[List[int, float, bool, str, bytes], dict]
            The return takes the form (record, metadata)
            where:
                record: A list of the parsed record values
                metadata: a dict containing the names, types, sizes,
                sources, and descriptions of each field
        """
        record_info = self._interface_record_vars.record_info_in

        row = [
            interface_utils.get_dynamic_type_value(field, in_record)
            for field in record_info
        ]
        return row

    def accumulate_record(self, record: sdk.RecordRef) -> None:
        """Accumulate an incoming record."""
        row = self.get_values_from_record(record)

        self._interface_record_vars.record_list_in.append(row)


class InputManager(UserDict):
    """Manager of input anchors with helper functions."""

    def __init__(self, plugin: object) -> None:
        self._plugin = plugin
        self.data = self._plugin._state_vars.input_anchors

    @property
    def tool_id(self) -> int:
        """Getter for the current tool ID."""
        return self._plugin._engine_vars.n_tool_id

    @property
    def workflow_config(self) -> OrderedDict:
        """Getter for the workflow config."""
        return self._plugin.workflow_config


class OutputManager(UserDict):
    """Manager of output anchors."""

    def __init__(self, plugin: object) -> None:
        self._plugin = plugin
        self.data = self._plugin._state_vars.output_anchors

    def get_temp_file_path(self) -> str:
        """Create a temp file using the Alteryx Engine."""
        return self._plugin._engine_vars.alteryx_engine.create_temp_file_name()

    @staticmethod
    def create_anchor_metadata():
        """Create a new anchor metadata object."""
        return AnchorMetadata()


class OutputAnchor:
    """Output anchor bookkeeping class with helpers."""

    def __init__(self) -> None:
        self._data = None
        self._metadata = None
        self._record_info_out = None
        self._record_creator = None
        self._handler = None

    @property
    def data(self) -> Union[object, List[List[Any]]]:
        """Getter for anchor data."""
        return self._data

    @data.setter
    def data(self, data: Union[object, List[List[Any]]]) -> None:
        """Setter for anchor data."""
        self._data = data

    @property
    def metadata(self) -> object:
        """Getter for the anchor metadata."""
        return copy.deepcopy(self._metadata)

    @metadata.setter
    def metadata(self, metadata):
        """Setter for anchor metadata."""
        self._metadata = metadata

    def get_data_list(self) -> List[List[Any]]:
        """Get the list of data to push downstream as a list of lists."""
        if interface_utils.is_dataframe(self._data):
            return interface_utils.dataframe_to_list(self._data)
        elif type(self._data) == list and not type(self._data[0]) == list:
            return [self._data]
        return self._data

    def push_metadata(self: object, plugin: object) -> None:
        """Propagate the metadata downstream for this anchor."""
        out_col_metadata = self.metadata
        if out_col_metadata is None:
            return

        if self._record_info_out is None:

            self._record_info_out = plugin.create_record_info()

            interface_utils.build_ayx_record_info(
                out_col_metadata, self._record_info_out
            )

            self._handler.init(self._record_info_out)

    def push_records(self, plugin: object) -> None:
        """
        Flush all records for an output anchor.

        Parameters
        ----------
        current_plugin: object
            The plugin that the output belongs to

        output_anchor: object
            The output anchor to flush

        Returns
        -------
        None
        """
        out_values_list = self.get_data_list()
        out_col_metadata = self.metadata

        # If there are no output records, just return
        if out_values_list is None:
            return

        if not self._record_info_out:
            self.push_metadata(plugin)

        for value in out_values_list:
            record_and_creator = interface_utils.build_ayx_record_from_list(
                value, out_col_metadata, self._record_info_out, self._record_creator
            )
            out_record, self._record_creator = record_and_creator

            self._handler.push_record(out_record, False)

        # Clear the data from the output_anchor
        self.data = None


class ColumnMetadata:
    """Column Metadata tracking class."""

    def __init__(
        self,
        name: str,
        col_type: sdk.FieldType,
        size: int,
        scale: int,
        source: str,
        description: str,
    ):
        self.name = name
        self.type = col_type
        self.size = size
        self.scale = scale
        self.source = source
        self.description = description

    def __deepcopy__(self, memo):
        """Override of deep copy method."""
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k not in ["type"]:
                setattr(result, k, copy.deepcopy(v, memo))

        setattr(result, "type", self.type)
        return result

    def __iter__(self):
        """Generate the iterable for this class."""
        for el in [
            self.name,
            self.type,
            self.size,
            self.scale,
            self.source,
            self.description,
        ]:
            yield el


class AnchorMetadata:
    """Class for tracking column metadata for a given anchor."""

    def __init__(self):
        self.columns = []

    @property
    def columns(self) -> List[ColumnMetadata]:
        """Getter for columns."""
        return self._columns

    @columns.setter
    def columns(self, value: List[ColumnMetadata]):
        """Setter for columns."""
        self._columns = value

    def add_column(
        self,
        name: str,
        col_type: sdk.FieldType,
        size: int = 256,
        scale: int = 0,
        source: str = "",
        description: str = "",
    ):
        """Add a column to this anchor."""
        self.columns.append(
            ColumnMetadata(name, col_type, size, scale, source, description)
        )

    def index_of(self, name: str):
        """Get the column index of a given column name."""
        try:
            return [c.name for c in self.columns].index(name)
        except ValueError:
            return None

    def get_column_by_name(self, name: str) -> ColumnMetadata:
        """Get the column given the column name."""
        index = self.index_of(name)
        if index is None:
            return None
        return self.columns[index]

    def get_column_names(self) -> List[str]:
        """Get a list of the column names available."""
        return [c.name for c in self.columns]

    def __getitem__(self, key: int) -> ColumnMetadata:
        """Get the column specified by key (an index)."""
        return self.columns[key]

    def __len__(self) -> int:
        """Return the number of columns as the length."""
        return len(self.columns)
