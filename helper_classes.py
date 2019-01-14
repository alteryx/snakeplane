# Built in Libraries
import pickle
import pdb
import os
import logging
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
            self._state_vars.input_anchors[connection["@Name"]] = []

            # Track names of the inputs that are required for this tool to run
            if connection["@Optional"] == "False":
                self._state_vars.required_input_names.append(
                    connection["@Name"])

        for connection in plugin_utils.get_xml_config_output_connections(
            self._state_vars.config_data
        ):
            self._state_vars.output_anchors[connection["@Name"]] = OutputAnchor()

        # Custom data
        self.user_data = SimpleNamespace()

        # Set up a custom logger so that errors, warnings and info are sent to designer
        self.set_logging()

    def set_logging(self):
        plugin = self

        class AyxLogger(logging.Logger):
            def __init__(self, name, level=logging.NOTSET):
                self._plugin = plugin
                super(AyxLogger, self).__init__(name, level)

                # Set the log level for alteryx plugins
                self.setLevel(level)

            def debug(self, msg, *args, **kwargs):
                self._plugin.logging.display_info_msg(msg)
                super(AyxLogger, self).debug(msg, *args, **kwargs)

            def info(self, msg, *args, **kwargs):
                self._plugin.logging.display_info_msg(msg)
                super(AyxLogger, self).info(msg, *args, **kwargs)

            def warning(self, msg, *args, **kwargs):
                self._plugin.logging.display_warn_msg(msg)
                super(AyxLogger, self).warning(msg, *args, **kwargs)

            def error(self, msg, *args, **kwargs):
                self._plugin.logging.display_error_msg(msg)
                super(AyxLogger, self).error(msg, *args, **kwargs)

            def critical(self, msg, *args, **kwargs):
                self._plugin.logging.display_error_msg(msg)
                super(AyxLogger, self).critical(msg, *args, **kwargs)

            def exception(self, msg, *args, **kwargs):
                self._plugin.logging.display_error_msg(msg)
                super(AyxLogger, self).exception(msg, *args, **kwargs)

        logging.setLoggerClass(AyxLogger)

    def save_output_anchor_refs(self):
        # Get references to the output anchors
        for anchor_name in self._state_vars.output_anchors:
            self._state_vars.output_anchors[
                anchor_name
            ]._handler = self._engine_vars.output_anchor_mgr.get_output_anchor(
                anchor_name
            )

    def save_interface(self, name, interface):
        self._state_vars.input_anchors[name].append(interface)

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
                connections = self._state_vars.input_anchors[name]
                if len(connections) == 0 or not all(
                    [connection.is_complete() for connection in connections]
                ):
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
            for connection in anchor:
                connection._interface_record_vars.record_list_in = []

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
            record_info_in=None, record_list_in=[], column_metadata={}
        )

        self._interface_state = SimpleNamespace(
            input_complete=False, d_progress_percentage=0, data_processing_mode="batch"
        )

    def create_record_for_input_records_list(
        self: object, in_record: object
    ) -> Tuple[List[Union[int, float, bool, str, bytes]], dict]:
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
        Tuple[List[int, float, bool, str, bytes], dict]
            The return takes the form (record, metadata)
            where:
                record: A list of the parsed record values
                metadata: a dict containing the names, types, sizes, 
                sources, and descriptions of each field
        """
        record_info = self._interface_record_vars.record_info_in
        column_metadata = interface_utils.get_column_metadata(record_info)

        record = [
            interface_utils.get_dynamic_type_value(field, in_record)
            for field in record_info
        ]
        return record, column_metadata

    def accumulate_record(self, record):
        row, column_metadata = self.create_record_for_input_records_list(
            record
        )

        # Attach local column info to interface object
        self.set_col_metadata(column_metadata)
        self._interface_record_vars.record_list_in.append(row)

    def set_record_info_in(self, record_info):
        self._interface_record_vars.record_info_in = record_info

    def is_complete(self):
        return self._interface_state.input_complete

    def set_completed(self):
        self._interface_state.input_complete = True

    def get_col_metadata(self):
        return self._interface_record_vars.column_metadata

    def set_col_metadata(self, val):
        self._interface_record_vars.column_metadata = val

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
                err_str = "The Pandas library must be installed to allow dataframe as input_type."
                logger = logging.getLogger(__name__)
                logger.error(err_str)
                raise ImportError(err_str)

            return pd.DataFrame(
                self._interface_record_vars.record_list_in,
                columns=self._interface_record_vars.column_metadata['name'],
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
        self._metadata = {
            "name": [],
            "type": [],
            "size": [],
            "source": [],
            "description": []
        }
        self._record_info_out = None
        self._record_creator = None
        self._handler = None

    def set_data(self, data):
        self._data = data

    def set_col_metadata(self, metadata):
        self._metadata = metadata

    def get_data(self):
        return self._data

    def get_data_list(self):
        if interface_utils.is_dataframe(self._data):
            return interface_utils.dataframe_to_list(self._data)
        elif type(self._data) == list and not type(self._data[0]) == list:
            return [self._data]
        return self._data

    def get_col_metadata(self):
        # This just makes sure they are all the same size
        num_of_columns = len(self._metadata['name'])
        for attribute in self._metadata:
            if len(self._metadata[attribute]) < num_of_columns:
                self._metadata[attribute].extend(None for _ in range(
                    num_of_columns - len(self._metadata[attribute])))
        return self._metadata

    def push_metadata(self: object, plugin: object) -> None:
        out_col_metadata = self.get_col_metadata()

        if self._record_info_out is None:

            self._record_info_out = plugin.create_record_info()

            interface_utils.build_ayx_record_info(
                out_col_metadata, self._record_info_out
            )

            self._handler.init(self._record_info_out)

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
        out_col_metadata = self.get_col_metadata()

        # If there are no output records, just return
        if out_values_list is None:
            return

        if not self._record_info_out:
            self.push_metadata(plugin)

        for value in out_values_list:
            out_record, self._record_creator = interface_utils.build_ayx_record_from_list(
                value,
                out_col_metadata,
                self._record_info_out,
                self._record_creator,
            )

            self._handler.push_record(out_record, False)

        # Clear the data from the output_anchor
        self.set_data(None)
