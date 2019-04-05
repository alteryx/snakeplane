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
"""Implementation of a plugin factory for use in snakeplane framework."""

# Built in Libraries
from functools import wraps

# 3rd Party Libraries
import AlteryxPythonSDK as sdk

import snakeplane.interface_utilities as interface_utils
from snakeplane.helper_classes import AyxPlugin, AyxPluginInterface

import xmltodict

DEBUG = False


class PluginFactory:
    """
    Class for generating a plugin using the snakeplane framework.

    The PluginFactory follows a Flask-like paradigm of leveraging decorators to inject
    custom user methods while abstracting the boilerplate operations for input and
    output with the Alteryx Engine.

    Attributes
    ----------
    plugin : object
        The plugin property contains a reference to a dynamic class declaration for the
        AyxPlugin class required by the Alteryx Engine for a Python SDK Plugin tool.
        The plugin object gets updated and further defined by the user as they call
        methods on the PluginFactory instance (either directly or via decorators).

    plugin.plugin_interface : object
        Although not a direct attribute of the PluginFactory class, due to the
        metaprogramming nature of the PluginFactory, the plugin_interface object is
        also a reference to a dynamic class declaration for an Alteryx Plugin Interface
        that is used as a child class instance by the plugin object. The PluginFactory
        is also dynamically constructing this class declaration based on the user's use
        of the PluginFactory's methods (either directly or via decorators).
    """

    def __init__(self, tool_name: str) -> None:
        """
        Initialize a PluginFactory object.

        Parameters
        ----------
        tool_name : str
        The name of the tool you are generating Python SDK engine code for.
        It is important to note that this name must match the name of the tool
        specified in the name of its Config/Icon files.  For example, a tool called
        ExampleStream would have a config file called "ExampleStreamConfig.xml".
        PluginFactory uses this to find and read in the contents of the xml file
        to better automate input and output creation.

        Examples
        --------
            # Assuming that tool has ExampleToolConfig.xml file
            factory = PluginFactory("ExampleTool")
        """

        # Make local, per instance copies of the plugins so that multiple plugins
        # can be generated with the same library. Since the plugin factory does
        # metaprogramming, we can't modify the original definitions of
        # AyxPlugin/AyxPluginInterface without contaminating the package
        class Plugin(AyxPlugin):
            pass

        class Interface(AyxPluginInterface):
            pass

        self._plugin = Plugin
        self._plugin.plugin_interface = Interface

        setattr(self._plugin, "tool_name", tool_name)

        # Initialize all required methods with default behavior
        def noop(*args, **kwargs) -> None:
            pass

        def always_true(*args, **kwargs):
            return True

        self.build_pi_init(always_true),
        self.build_pi_add_incoming_connection(noop),
        self.build_pi_push_all_records(noop),
        self.build_pi_add_outgoing_connection(always_true)
        self.build_pi_close(noop)

        self.build_ii_init(always_true),
        self.build_ii_push_record(always_true),
        self.build_ii_update_progress(noop),
        self.build_ii_close(noop)
        self.build_metadata(noop)

        self._init_func = always_true

    def build_pi_init(self, func: object):
        """
        Register a custom pi_init method.

        Parameters
        ----------
        func: Callable[object, str]
        The user-defined function that will be called by the Alteryx Engine to
        initialize the plugin.

        Returns
        -------
        None
        This method produces side-effects by registering the user defined function
        """

        @_monitor("pi_init")
        @wraps(func)
        def wrap_pi_init(current_plugin, config_xml):
            current_plugin.update_sys_path()
            current_plugin.save_output_anchor_refs()

            # Parse XML and save
            current_plugin.workflow_config = xmltodict.parse(config_xml)[
                "Configuration"
            ]

            # Call decorated function
            val = func(current_plugin)

            if (
                current_plugin.update_only_mode
                and len(current_plugin._state_vars.required_input_names) == 0
            ):
                self._init_func(current_plugin)

            # Boilerplate Side Effects
            current_plugin.initialized = val

            return val

        setattr(self._plugin, "pi_init", wrap_pi_init)

    def build_pi_add_incoming_connection(self, func: object):
        """
        Register a custom pi_add_incoming_connection method.

        Parameters
        ----------
        func: Callable[object, str, str]
        The user-defined function that will be called by the Alteryx Engine for each
        incoming connection.  It is expected that this function returns an initialized
        AyxInterface object.

        Returns
        -------
        None
        This method produces side-effects by registering the user defined function
        """

        @_monitor("pi_add_incoming_connection")
        @wraps(func)
        def wrap_pi_add_incoming_connection(
            current_plugin: object, str_type: str, str_name: str
        ):
            # Call decorated function
            func(current_plugin, str_type, str_name)

            # Generate the interface
            interface = current_plugin.plugin_interface(current_plugin, str_type)

            # Save it to the plugin
            current_plugin.save_interface(str_type, interface)

            # Return it
            return interface

        setattr(
            self._plugin, "pi_add_incoming_connection", wrap_pi_add_incoming_connection
        )

    def build_pi_push_all_records(self, func: object):
        """
        Register a custom pi_push_all_records method.

        Parameters
        ----------
        func: Callable[object, int]
        The user-defined function that will be called by the Alteryx Engine when
        no incoming interface exists.  Typically this is for generating records from
        sources outside of Alteryx, such as an API or database.
        It is expected that this function returns a True if no errors are present,
        otherwise False.

        Returns
        -------
        None
        This method produces side-effects by registering the user defined function
        """
        @_monitor("push_all_records")
        @wraps(func)
        def wrap_push_all_records(current_plugin: object, n_record_limit: int):
            if len(current_plugin._state_vars.required_input_names) == 0:
                if current_plugin.update_only_mode:
                    self._build_metadata(current_plugin)
                    for _, anchor in current_plugin._state_vars.output_anchors.items():
                        anchor.push_metadata(current_plugin)
                else:
                    # Only call the users defined function when there are no required
                    # inputs, since this is the only scenario where something interesting
                    # happens in this function
                    func(current_plugin, n_record_limit)
            else:
                current_plugin.assert_all_inputs_connected()

            return True

        setattr(self._plugin, "pi_push_all_records", wrap_push_all_records)

    def build_pi_add_outgoing_connection(self, func: object):
        """
        Register a custom pi_add_outgoing_connection method.

        Parameters
        ----------
        func: Callable[object, str]
        The user-defined function that will be called by the Alteryx Engine, once for
        each defined output connection in the Plugin's Config.xml file.
        The function will return True to signify that the connection has been accepted.

        Returns
        -------
        None
        This method produces side-effects by registering the user defined function
        """

        @_monitor("pi_add_outgoing_connection")
        @wraps(func)
        def wrap_pi_add_outgoing_connection(current_plugin: object, str_name: str):
            return func(current_plugin, str_name)

        setattr(
            self._plugin, "pi_add_outgoing_connection", wrap_pi_add_outgoing_connection
        )

    def build_pi_close(self, func: object) -> None:
        """
        Register a custom pi_close method.

        Parameters
        ----------
        func: Callable[object, bool]
        The user-defined function that will be called by the Alteryx Engine, after
        all records for each of the defined incoming connections have been processed.

        Returns
        -------
        None
        This method produces side-effects by registering the user defined function
        """

        @_monitor("pi_close")
        @wraps(func)
        def wrap_pi_close(current_plugin: object, b_has_errors: bool) -> None:
            if current_plugin.all_inputs_completed:
                func(current_plugin)

        setattr(self._plugin, "pi_close", wrap_pi_close)

    def build_ii_init(self, func: object):
        """
        Register a custom ii_init method.

        Parameters
        ----------
        func: Callable[object, object] -> bool
        The user-defined function that will be called by the Alteryx Engine to
        refresh metadata tracked by the plugin after changes to config or new tools are
        dragged onto the canvas.

        Returns
        -------
        None
        This method produces side-effects by registering the user defined function
        """

        @_monitor("ii_init")
        @wraps(func)
        def wrap_ii_init(current_interface: object, record_info_in: object):
            current_plugin = current_interface.parent
            current_plugin.update_sys_path()
            current_interface._interface_record_vars.record_info_in = record_info_in
            current_interface.initialized = True

            metadata = interface_utils.get_column_metadata(record_info_in)

            current_interface.anchor_metadata = metadata

            init_success = func(current_interface, record_info_in)

            if not init_success:
                current_plugin.initialized = False
                current_interface.initialized = False
                return False

            if (
                current_plugin.update_only_mode
                and current_plugin.all_required_inputs_initialized
            ):
                ret_val = self._init_func(current_plugin)
                if ret_val:
                    self._build_metadata(current_plugin)
                    for _, anchor in current_plugin._state_vars.output_anchors.items():
                        anchor.push_metadata(current_plugin)

            return True

        setattr(self._plugin.plugin_interface, "ii_init", wrap_ii_init)

    def build_ii_push_record(self, func: object):
        """
        Register a custom ii_push_record method.

        Parameters
        ----------
        func: Callable[object, object] -> bool
        The user-defined function that will be called by the Alteryx Engine, once
        for each incoming record for each input connection.

        Returns
        -------
        None
        This method produces side-effects by registering the user defined function
        """

        @_monitor("ii_push_record")
        @wraps(func)
        def wrap_ii_push_record(current_interface: object, in_record: sdk.RecordRef):
            current_plugin = current_interface.parent

            if not current_plugin.initialized or current_plugin.update_only_mode:
                return False

            func(current_plugin, current_interface, in_record)
            return True

        setattr(self._plugin.plugin_interface, "ii_push_record", wrap_ii_push_record)

    def build_ii_update_progress(self, func: object):
        """
        Register a custom ii_update_progress method.

        Parameters
        ----------
        func: Callable[object, float]
        The user-defined function that will be called by the upstream tool,
        reporting the number of records it has pushed to the plugin.

        Returns
        -------
        None
        This method produces side-effects by registering the user defined function
        """

        @_monitor("ii_update_progress")
        @wraps(func)
        def wrap_ii_update_progress(current_interface: object, d_percentage: float):
            current_plugin = current_interface.parent
            if current_plugin.update_only_mode:
                return

            current_plugin.update_progress(d_percentage)

            return func(current_interface, d_percentage)

        setattr(
            self._plugin.plugin_interface, "ii_update_progress", wrap_ii_update_progress
        )

    def build_ii_close(self, func: object):
        """
        Register a custom ii_close method.

        Parameters
        ----------
        func: Callable[object]
        The user-defined function that will be called by the Alteryx Engine,
        once for each incoming connection, after all records have been passed through
        ii_push_record step.

        Returns
        -------
        None
        This method produces side-effects by registering the user defined function
        """

        @_monitor("ii_close")
        @wraps(func)
        def wrap_ii_close(current_interface: object):
            current_plugin = current_interface.parent

            current_plugin.assert_all_inputs_connected()

            if current_plugin.update_only_mode:
                return

            current_interface.completed = True

            return func(current_plugin)

        setattr(self._plugin.plugin_interface, "ii_close", wrap_ii_close)

    def initialize_plugin(self, func: object):
        """
        Decorate a user defined function to inject custom intialization.

        Parameters
        ----------
        func : Callable[[object, dict, object], bool]
        The user is expected to define a function which takes in
            User Defined Function Parameters (passed in at runtime):
            -------------------------------------------------------
                logger: An object which provides methods for logging to
                        Alteryx Designer results window
                workflow_config: A dictionary which is populated with the
                        values from the tool's configuration GUI, keys that
                        match the XML tags in the GUI.
                user_data: A SimpleNamespace object that allows the user to
                        store variables (for example values from the workflow_config)
                        to be accessed globally in later steps for the PluginFactory,
                        such as process_data.

            User Defined Function Returns
            -----------------------------
                bool
                    True if the variables needed to be passed  to tool for
                    data processing are present, False if otherwise.  This
                    manifests in Alteryx Designer as an error if the user
                    tries to run the tool but hasn't passed in proper values
                    to meet conditions that evaluate True.

        Returns
        -------
        This method doesn't return a value.  It creates side-effects by altering
        the state of the AyxPlugin class declaration that is returned by the
        PluginFactory.generate_plugin() method.

        Examples
        --------
            @factory.initialize_plugin
            def init(workflow_config, user_data, logger):
                user_data.some_variable = workflow_config.get(
                    "SomeVarInGuiXml")

                if user_data.some_variable is None:
                    logger.display_error_msg("User needs to input SomeVar")
                    init_success = False
                else:
                    init_success = True

                return init_success
        """

        @wraps(func)
        def wrap_init(current_plugin: object):
            current_plugin.initialized = _apply_parameter_requests(func)(current_plugin)
            return current_plugin.initialized

        self._init_func = wrap_init

    def build_metadata(self, func: object):
        """Decorate a function to inject user defined build metadata function."""

        def decorated_build_metadata(plugin: object):
            return _apply_parameter_requests(func)(plugin)

        self._build_metadata = decorated_build_metadata
        return

    def process_data(self, mode: str = "batch", input_type: str = "list"):
        """
        Decorate a function to inject user defined functionality.

        The process_data method is used to allow a user to inject
        Python code for processing records without having to specify
        boilerplate for input/output.

        The process data plugin method takes both direct parameters,
        mode and input_type, as well as indirect parameter of a user
        defined function, explained in greater detail below.

        Parameters
        ----------
        mode : str
        One of two options: 'batch' or 'stream'

        Batch mode will cause the tool to pull in all input records for
        a given input anchor, collect them into a single data
        structure (defined by input_type) and make this collection of records
        available to the User Defined Function in the respective input_anchor
        object.
        An important note for batch is that the User Defined Function will be
        executed one time, on the entire set of records at once.

        Stream mode will cause the tool to pull one input record in at a time,
        and make this single record available to the User Defined Function in
        the respective input_anchor object.
        An important note for stream is that the User Defined Function will be
        executed once for every incoming record.

        input_type : str
        One of two options: 'list' or 'dataframe'
        Depending on the value set by user, the input data made available to
        the UDF by the respective input_anchor contained in the input_mgr
        will either contain records in the form of a Python list or a
        Pandas DataFrame object.

        Returns
        -------
        Callable[[Callable[object, object, Any], None]]
            The process_data method is a method which returns a
            higher order function.  This higher order function
            takes a user defined function as its parameter.

            The User Defined Function is a function defined by the
            user that will be called at runtime by the Alteryx Engine.
            It needs to meet specific requirements as to the parameters
            it accepts and the side effects it produces:

        Parameters
        ----------
        input_mgr : object
        The UDF will be given an input_mgr object as its first parameter.
        This object allows the user to reference any of a given plugin's
        defined input anchors, which facilitate fetching input data.

        output_mgr : object
        The UDF will be given an output_mgr object as its second parameter.
        This object allows the user to reference any of a given plugin's
        defined output anchors, which facilitate setting output data.

        user_data : object
        A SimpleNamespace object that allows the user to store variables
        (for example values from the workflow_config) to be accessed
        globally in later steps for the PluginFactory.  In the context of
        the UDF, this is a way to fetch values set in the initialize_plugin
        step to use for the process_data logic.

        Returns
        -------
        None
        The UDF doesn't return any values.  Instead, it needs to 'send'
        data as a side effect, by calling methods on the output_anchor
        object it gets from the output_mgr object it is provided.

        Examples
        --------
        @factory.process_data(mode="batch", input_type="dataframe")
        def process_data(input_mgr, output_mgr, user_data, logger):
            input_anchor = input_mgr.get_anchor("AnchorNameFromConfigXmlFile")
            input_df = input_anchor.get_data()

            output_df = input_df ## do stuff with data here

            output_anchor = output_mgr.get_anchor(
                "OutputAnchorNameFromConfigXmlFile")
            output_anchor.set_col_types(
                [sdk.FieldType.v_string, sdk.FieldType.int64])
            output_anchor.set_data(output_df)

        @factory.process_data(mode="stream")
        def process_each_record(input_mgr, output_mgr, user_data, logger):
            input_anchor = input_mgr.get_anchor("AnchorNameFromConfigXmlFile")
            input_row = input_anchor.get_data()
            col_names = input_anchor.get_col_names()
            col_types = input_anchor.get_col_types()

            output_row = []
            output_col_names = col_names + ["new_col_name"]
            output_col_types = col_types + [sdk.FieldType.v_string]

            for col in input_row:
                output_row.append(some_function(col))
            output_row.append("value for a new column")

            output_anchor = output_mgr.get_anchor(
                "OutputAnchorNameFromConfigXml")
            output_anchor.set_col_names(output_col_names)
            output_anchor.set_col_types(output_col_types)
            output_anchor.set_data(output_row)

        """
        # Save the requested data type for later
        setattr(self._plugin, "process_data_input_type", input_type)
        setattr(self._plugin, "process_data_mode", mode)

        def decorator_process_data(func: object):
            # Decorate user function to push all records and metadata
            func = _apply_parameter_requests(func)
            func = _push_all_metadata_and_records(func)

            @_run_only_if_pi_initialized
            def batch_ii_close(plugin: object):
                if plugin.all_inputs_completed:
                    # Run initialization here
                    if not self._init_func(plugin):
                        return

                    # Build metadata
                    self._build_metadata(plugin)

                    # Call user function to batch process data
                    func(plugin)

            @_run_only_if_pi_initialized
            def stream_ii_push_record(
                plugin: object, current_interface: object, in_record: sdk.RecordRef
            ):
                # Since we're streaming, we should clear any accumulated records
                plugin.clear_accumulated_records()

                # Then we can accumulate, this guarantees only one interface at a time
                # ever has a record
                current_interface.accumulate_record(in_record)

                self._build_metadata(plugin)

                func(plugin)

            @_run_only_if_pi_initialized
            def source_pi_push_all_records(plugin: object, n_record_limit: int):
                if not self._init_func(plugin):
                    return

                self._build_metadata(plugin)
                func(plugin)

            if mode.lower() == "batch":
                self.build_ii_push_record(
                    lambda plugin, interface, in_record: interface.accumulate_record(
                        in_record
                    )
                )
                self.build_ii_close(batch_ii_close)
            elif mode.lower() == "stream":
                # Streaming is the unique case for initialization
                # It should be ran in pi_init.
                self.build_pi_init(self._init_func)
                self.build_ii_push_record(stream_ii_push_record)
            elif mode.lower() == "source":
                self.build_pi_push_all_records(source_pi_push_all_records)
            else:
                err_str = """Mode parameter of process_data must be one of
                    'batch'|'stream'|'source'"""
                raise ValueError(err_str)

        return decorator_process_data

    def generate_plugin(self):
        """
        Return the constructed class definition for an AyxPlugin object.

        The AyxPlugin class definition is initialized by the Alteryx Engine via the
        Alteryx Python SDK.

        Parameters
        ----------
        None

        Returns
        -------
        object: AyxPlugin class definition
        The returned object is a modified AyxPlugin class definition, updated with
        the user definied functions injected by use of the various decorators the user
        has called.

        Example
        -------
            AyxPlugin = factory.generate_plugin()

        """
        return self._plugin


def _run_only_if_pi_initialized(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        plugin = args[0]
        if not plugin.initialized:
            return

        return func(*args, **kwargs)

    return wrapper


def _push_all_metadata_and_records(func):
    @wraps(func)
    def wrapper(plugin):
        func(plugin)

        plugin.push_all_metadata()
        plugin.push_all_output_records()

        if plugin.all_inputs_completed:
            plugin.close_all_outputs()

    return wrapper


def _apply_parameter_requests(func):
    @wraps(func)
    def wrapped(plugin):
        import inspect

        sig = inspect.signature(func)

        func_params = {
            "input_mgr": plugin.input_manager,
            "output_mgr": plugin.output_manager,
            "workflow_config": plugin.input_manager.workflow_config,
            "user_data": plugin.user_data,
            "logger": plugin.logging,
        }

        try:
            # Get the expected parameter names
            param_names = [name for name, param in sig.parameters.items()]
            passed_params = {name: func_params[name] for name in param_names}
        except KeyError:
            # Failed to build the requested params, using defaults
            return func(
                plugin.input_manager,
                plugin.output_manager,
                plugin.user_data,
                plugin.logging,
            )
        else:
            return func(**passed_params)

    return wrapped


def _monitor(name):
    def _monitor_decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if DEBUG:
                import time
                from pathlib import Path
                import pandas as pd

                start_time = time.time()
                val = func(*args, **kwargs)
                end_time = time.time()
                time_diff_ms = (end_time - start_time) * 1000

                # Write to a file
                file_name = Path("C:/debug.csv")

                if not file_name.is_file():
                    data = {"Func": [name], "Time": [time_diff_ms]}
                    df = pd.DataFrame(data)
                else:
                    data = {"Func": [name], "Time": [time_diff_ms]}
                    df_new = pd.DataFrame(data)
                    df_old = pd.read_csv(file_name)
                    df = pd.concat([df_old, df_new])

                df.to_csv(file_name, index=False)
                return val
            else:
                return func(*args, **kwargs)

        return wrapped

    return _monitor_decorator
