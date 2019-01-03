# Built in Libraries
import pickle
import pdb
import os
from functools import partial
from types import SimpleNamespace
from typing import Callable, Iterable, Union, Optional, List, Tuple

# 3rd Party Libraries
try:
    import pandas as pd
except:
    pd = None

import xmltodict

# Alteryx Libraries
import AlteryxPythonSDK as sdk

# Custom libraries
import snakeplane.interface_utilities as interface_utils
import snakeplane.plugin_utilities as plugin_utils


class AyxPlugin:
    def __init__(
        self, n_tool_id: int, alteryx_engine: object, output_anchor_mgr: object
    ):
        self.input_manager = InputManager(self)
        self.output_manager = OutputManager(self)

        # Initialization data
        self._engine_vars = SimpleNamespace()
        self._engine_vars.n_tool_id = n_tool_id
        self._engine_vars.alteryx_engine = alteryx_engine
        self._engine_vars.output_anchor_mgr = output_anchor_mgr

        # Plugin State vars
        self._state_vars = SimpleNamespace(
            is_initialized=False,
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
            f"{plugin_utils.get_tool_path(self.tool_name)}\\{xml_files[0]}"
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
            self._state_vars.input_anchors[connection["@Name"]] = None

            # Track names of the inputs that are required for this tool to run
            if connection["@Optional"] == "False":
                self._state_vars.required_input_names.append(connection["@Name"])

        for connection in plugin_utils.get_xml_config_output_connections(
            self._state_vars.config_data
        ):
            self._state_vars.output_anchors[connection["@Name"]] = OutputAnchor()

        # Custom data
        self.user_data = SimpleNamespace()

    def save_output_anchor_refs(self):
        # Get references to the output anchors
        for anchor_name in self._state_vars.output_anchors:
            self._state_vars.output_anchors[
                anchor_name
            ]._handler = self._engine_vars.output_anchor_mgr.get_output_anchor(
                anchor_name
            )

    def save_interface(self, name, interface):
        self._state_vars.input_anchors[name] = interface

    def is_update_only_mode(self):
        return (
            self._engine_vars.alteryx_engine.get_init_var(
                self._engine_vars.n_tool_id, "UpdateOnly"
            )
            == "True"
        )

    def update_progress(self, d_percentage):
        self._engine_vars.alteryx_engine.output_tool_progress(
            self._engine_vars.n_tool_id, d_percentage
        )  # Inform the Alteryx engine of the tool's progress.

        for _, anchor in self._state_vars.output_anchors.items():
            # Inform the downstream tool of this tool's progress.
            anchor._handler.update_progress(d_percentage)

    def all_inputs_completed(self: object) -> bool:
        """
        Checks that all inputs have successfully completed on all 
        required inputs. Optional inputs are not checked. 

        Parameters
        ----------
        current_plugin : object
            An AyxPlugin object

        Returns
        ---------
        bool
            Boolean indication of if all inputs have completed.
        """
        all_inputs_completed = True
        if self.is_initialized():
            for name in self._state_vars.required_input_names:
                anchor = self._state_vars.input_anchors[name]
                if anchor is None or not anchor.is_complete():
                    all_inputs_completed = False
        else:
            all_inputs_completed = False
        return all_inputs_completed

    def close_all_outputs(self):
        # Close all output anchors
        for _, anchor in self._state_vars.output_anchors.items():
            anchor._handler.close()

        # Checks whether connections were properly closed.
        for anchor_name in self._state_vars.output_anchors:
            self._state_vars.output_anchors[anchor_name]._handler.assert_close()

    def is_initialized(self):
        return self._state_vars.is_initialized

    def set_initialization_state(self, state):
        self._state_vars.is_initialized = state

    def push_all_output_records(self: object) -> None:
        """
        For each output anchor on the plugin, flush all the output records

        Parameters
        ----------
        current_plugin: object
            The plugin for which to flush output records

        Returns
        ---------
        None
        """
        for _, output_anchor in self._state_vars.output_anchors.items():
            output_anchor.push_records(self)

    def clear_accumulated_records(self: object) -> None:
        """
        Clears out all accumulated records from all plugin interfaces

        Parameters
        ----------
        plugin: object
            The plugin to clear all records from

        Returns
        ---------
        None
            This function has side effects on plugin, and therefore has no return
        """
        for _, anchor in self._state_vars.input_anchors.items():
            anchor._interface_record_vars.record_list_in = []

    def create_record_info(self):
        return sdk.RecordInfo(self._engine_vars.alteryx_engine)


class AyxPluginInterface:
    def __init__(self, parent: object):
        """
            Constructor for IncomingInterface.
            :param parent: AyxPlugin
            """
        self.parent = parent

        self._interface_record_vars = SimpleNamespace(
            record_info_in=None, record_list_in=[], column_names=[], column_types=[]
        )

        self._interface_state = SimpleNamespace(
            input_complete=False, d_progress_percentage=0, data_processing_mode="batch"
        )

    def create_record_for_input_records_list(
        self: object, in_record: object
    ) -> Tuple[List[Union[int, float, bool, str, bytes]], List[str], List[object]]:
        """
        Creates a list of values "record" from an Alteryx RecordRef object

        Parameters
        ----------
        interface_obj : object
            An AyxPluginInterface object for the current interface

        in_record: object
            An Alteryx RecordRef object for the record to be processed
        Returns
        ---------
        Tuple[List[int, float, bool, str, bytes], List[str], List[object]]
            The return takes the form (record, column_names, column_types)
            where:
                record: A list of the parsed record values
                column_names: A list of the column names in string form
                column_types: A list of the column names per the AlteryxSDK
        """
        record_info = self._interface_record_vars.record_info_in
        column_names = interface_utils.get_column_names_list(record_info)
        column_types = interface_utils.get_column_types_list(record_info)

        record = [
            interface_utils.get_dynamic_type_value(field, in_record)
            for field in record_info
        ]
        return record, column_names, column_types

    def accumulate_record(self, record):
        row, column_names, column_types = self.create_record_for_input_records_list(
            record
        )

        # Attach local column info to interface object
        self.set_col_names(column_names)
        self.set_col_types(column_types)

        self._interface_record_vars.record_list_in.append(row)

    def set_record_info_in(self, record_info):
        self._interface_record_vars.record_info_in = record_info

    def is_complete(self):
        return self._interface_state.input_complete

    def set_completed(self):
        self._interface_state.input_complete = True

    def get_col_names(self):
        return self._interface_record_vars.column_names

    def get_col_types(self):
        return self._interface_record_vars.column_types

    def set_col_names(self, val):
        self._interface_record_vars.column_names = val

    def set_col_types(self, val):
        self._interface_record_vars.column_types = val

    def get_data(self):
        if (
            self.parent.process_data_mode == "stream"
            and self.parent.process_data_input_type == "list"
        ):
            return self._interface_record_vars.record_list_in[0]
        elif self.parent.process_data_input_type == "list":
            return self._interface_record_vars.record_list_in
        else:
            if pd is None:
                plugin_utils.log_and_raise_error(
                    self.parent.logging,
                    ImportError,
                    "The Pandas library must be installed to allow dataframe as input_type.",
                )

            return pd.DataFrame(
                self._interface_record_vars.record_list_in,
                columns=self._interface_record_vars.column_names,
            )


class InputManager:
    def __init__(self, plugin):
        self._plugin = plugin

    def get_anchor(self, name):
        return self._plugin._state_vars.input_anchors.get(name)


class OutputManager:
    def __init__(self, plugin):
        self._plugin = plugin

    def get_anchor(self, name):
        return self._plugin._state_vars.output_anchors.get(name)

    def get_temp_file_path(self):
        return self._plugin._engine_vars.alteryx_engine.create_temp_file_name() 


class OutputAnchor:
    def __init__(self):
        self._data = None
        self._col_names = None
        self._col_types = None
        self._record_info_out = None
        self._record_creator = None
        self._handler = None

    def set_data(self, data):
        self._data = data

    def set_col_names(self, col_names):
        self._col_names = col_names

    def set_col_types(self, col_types):
        self._col_types = col_types

    def get_data(self):
        return self._data

    def get_data_list(self):
        if interface_utils.is_dataframe(self._data):
            return interface_utils.dataframe_to_list(self._data)
        elif type(self._data) == list and not type(self._data[0]) == list:
            return [self._data]
        return self._data

    def get_col_names(self):
        if interface_utils.is_dataframe(self._data):
            return list(self._data)
        return self._col_names

    def get_col_types(self):
        return self._col_types

    def push_records(self: object, plugin: object) -> None:
        """
        Flush all records for an output anchor

        Parameters
        ----------
        current_plugin: object
            The plugin that the output belongs to

        output_anchor: object
            The output anchor to flush

        Returns
        ---------
        None
        """
        out_values_list = self.get_data_list()
        out_col_names_list = self.get_col_names()
        out_col_types_list = self.get_col_types()

        # If there are no output records, just return
        if out_values_list is None:
            return

        if not self._record_info_out:
            # TODO repackage all of this into a util function.
            # use out_col_names_list and out_col_types_list to
            # create new record info out
            self._record_info_out = plugin.create_record_info()

            interface_utils.build_ayx_record_info(
                out_col_names_list, out_col_types_list, self._record_info_out
            )

            self._handler.init(self._record_info_out)

        for value in out_values_list:
            out_record, self._record_creator = interface_utils.build_ayx_record_from_list(
                value,
                out_col_names_list,
                out_col_types_list,
                self._record_info_out,
                self._record_creator,
            )

            self._handler.push_record(out_record, False)

        # Clear the data from the output_anchor
        self.set_data(None)
