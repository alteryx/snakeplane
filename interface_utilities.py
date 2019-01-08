# Built in Libraries
import os
from collections import namedtuple
from typing import Union, Any, List, Optional, cast, Set, Dict, Tuple
import pdb

# 3rd Party Libraries
try:
    import pandas as pd
except:
    pd = None

# Alteryx Libraries
import AlteryxPythonSDK as sdk

# Custom libraries
from . import plugin_utilities as plugin_utils

# Create a column named tuple for use in below functions
Column = namedtuple("Column", ["name", "type", "value"])


def get_dynamic_type_value(field: object, record: object) -> Any:
    """
    Takes an Alteryx Field object associated with record metadata (record_info_in) 
    and a single record and extracts the data from the record using the getter 
    function assoicated with the type of that field (e.g. get_as_int32, etc.)

    Parameters
    ----------
    field : object
        An Alteryx Field object that is present in an Alteryx RecordInfo object.
        Alteryx Field objects contain various attributes, including type, as well
        as the actual methods that allow for getting/setting values in the 
        RecordRef passed in via C++ engine.  

    record : object 
        A single record object from Alteryx that contains a row of data.

    Returns
    ---------
    Any
        The return value of this function can be any of types blob, int32, int64,
        dobule, bool, or string. The returned value represents the parsed/typed 
        value of the desired field from the input record
    """
    field_type = str(field.type)
    if field_type == "blob":
        return field.get_as_blob(record)
    elif any(field_type in s for s in ["byte", "int16", "int32"]):
        return field.get_as_int32(record)
    elif field_type == "int64":
        return field.get_as_int64(record)
    elif any(field_type in s for s in ["float"]):
        return field.get_as_double(record)
    elif field_type == "bool":
        return field.get_as_bool(record)
    else:
        return field.get_as_string(record)


# interface
def get_column_names_list(record_info_in: object) -> List[str]:
    """
    Collects the column names from an Alteryx record info object

    Parameters
    ----------
    record_info_in : object
        An Alteryx RecordInfo object
    Returns
    ---------
    List[str]
        A list of the column names in string format
    """
    return [field.name for field in record_info_in]


# interface
def get_column_types_list(record_info_in: object) -> List[object]:
    """
    Collects the column types from an Alteryx record info object

    Parameters
    ----------
    record_info_in : object
        An Alteryx RecordInfo object
    Returns
    ---------
    List[object]
        A list of the column types as per the AlteryxSDK
    """
    return [field.type for field in record_info_in]


# interface
def set_field_value(field: object, value: Any, record_creator: object) -> None:
    """
    Takes a python value and writes it to its respective field in a given 
    record_creator object.

    Parameters
    ----------
    field : object
        An Alteryx Field object that is present in an Alteryx RecordInfo object.
        Alteryx Field objects contain various attributes, including type, as well
        as the actual methods that allow for getting/setting values in the 
        RecordRef passed in via C++ engine.  

    value : Any 
        This is the actual Python object of any type to pass into the field.  It
        is the user's responsibility to know whether this Python object is
        compatible with the destination Field's type.

    record_creator : object
        An Alteryx RecordCreator object.  The RecordCreator object is created by
        calling the construct_record_creator method on an Alteryx RecordInfo
        object.  It is a stateful object which is populated with values as a 
        side-effect of this function.  When its finalize method is called, it 
        returns an actual reference to the record's data, in the form of an
        Alteryx RecordRef object.  

    Returns
    ---------
    None
        This is a stateful function that produces side effects by modifying
        the record_creator object.  
    """
    if field.type == sdk.FieldType.bool:
        field.set_from_bool(record_creator, value)
    elif field.type == sdk.FieldType.blob:
        field.set_from_blob(record_creator, value)
    elif field.type == sdk.FieldType.double:
        field.set_from_double(record_creator, value)
    elif field.type in {sdk.FieldType.byte, sdk.FieldType.int16, sdk.FieldType.int32}:
        field.set_from_int32(record_creator, value)
    elif field.type == sdk.FieldType.int64:
        field.set_from_int64(record_creator, value)
    elif field.type in {
        sdk.FieldType.string,
        sdk.FieldType.v_string,
        sdk.FieldType.v_wstring,
        sdk.FieldType.wstring,
        sdk.FieldType.date,
        sdk.FieldType.datetime,
        sdk.FieldType.time,
    }:
        field.set_from_string(record_creator, value)


# interface
def add_new_field_to_record_info(
    record_info: object, field_name: str, field_type: object, field_size: int = None
) -> None:
    """
    Attaches a field of specified name, type, and size to the specified Alteryx
    RecordInfo object.   

    Parameters
    ----------
    record_info : object
        An Alteryx RecordInfo object.
        Alteryx RecordInfo objects act as containers for the necessary metadata
        needed by the Alteryx engine to generate, identify, and manipulate 
        each record of data passing through the tool.  

    field_name : str
        A string representing the desired name of the field.

    field_type : object
        An Alteryx FieldType object.  It can be one of the following:
            sdk.FieldType.string,
            sdk.FieldType.v_string,
            sdk.FieldType.v_wstring,
            sdk.FieldType.wstring,
            sdk.FieldType.bool,
            sdk.FieldType.blob,
            sdk.FieldType.byte,
            sdk.FieldType.int16,
            sdk.FieldType.int32,
            sdk.FieldType.int64,
            sdk.FieldType.float,
            sdk.FieldType.double,
            sdk.FieldType.date,
            sdk.FieldType.datetime,
            sdk.FieldType.time,
            sdk.FieldType.spatial

    field_size : int 
        An integer specifying the size of the desired Alteryx Field. This
        option is ignored for primitive types, and is only used for string,
        blob, and spatial types.   

    Returns
    ---------
    None
        This is a stateful function that produces side effects by modifying
        the record_info object.  
    """
    string_field_set = {
        sdk.FieldType.string,
        sdk.FieldType.v_string,
        sdk.FieldType.v_wstring,
        sdk.FieldType.wstring,
    }
    default_string_size = 255
    if (field_size is None) and (field_type in string_field_set):
        field_size = default_string_size
    elif field_size is None:
        field_size = 0

    record_info.add_field(field_name, field_type, field_size)


# interface
def build_ayx_record_info(
    names_list: List[str], types_list: List[object], record_info: object
) -> None:
    """
    Populates a an Alteryx RecordInfo object with field objects based on the 
    contents of the names and types specified in names_list and types_list,
    respectively.   

    Parameters
    ---------- 
    names_list : List[str] 
        A list of the names for each respective column.  These are used to generate
        the Alteryx RecordInfo object (if it doesn't already exist) for the names
        of each respective Field object. 

    types_list : List[object] 
        A list of the respective Alteryx FieldType objects for each column in the 
        values_list.  

    record_info : object
        An Alteryx RecordInfo object.
        Alteryx RecordInfo objects act as containers for the necessary metadata
        needed by the Alteryx engine to generate, identify, and manipulate 
        each record of data passing through the tool.

    Returns
    ---------
    None
        This is a stateful function that produces side effects by modifying
        the record_info object. 
    """
    output_columns = [
        Column(names_list[i], types_list[i], None) for i in range(len(names_list))
    ]

    for output_column in output_columns:
        add_output_column_to_record_info(output_column, record_info)


# interface
def build_ayx_record_from_list(
    values_list: List[Any],
    names_list: List[str],
    types_list: List[object],
    record_info: object,
    record_creator: Optional[object] = None,
) -> Tuple[object, object]:
    """
    Takes a list of values that represents a single row of data, along with metadata
    and a blank or already populated Alteryx RecordInfo object, and returns a tuple
    containing a populated Alteryx RecordRef object and an already initialized
    RecordCreator object.  
    The returned RecordCreator object can optionally be passed back into the function,
    allowing for improved performance when looping through a list of new values.

    Parameters
    ----------
    values_list : List[Any] 
        A list of Python objects of any type that represents a single record of
        data.  The 0th index of the list represents data in the first column
        of the record, and so on.    

    names_list : List[str] 
        A list of the names for each respective column.  These are used to generate
        the Alteryx RecordInfo object (if it doesn't already exist) for the names
        of each respective Field object. 

    types_list : List[object] 
        A list of the respective Alteryx FieldType objects for each column in the 
        values_list.  

    record_info : object
        An Alteryx RecordInfo object.
        Alteryx RecordInfo objects act as containers for the necessary metadata
        needed by the Alteryx engine to generate, identify, and manipulate 
        each record of data passing through the tool.

    record_creator : Optional[object]
        An optional Alteryx RecordCreator object.  The RecordCreator object is created by
        calling the construct_record_creator method on an Alteryx RecordInfo
        object.  It is a stateful object which is populated with values as a 
        side-effect of this function.  When its finalize method is called, it 
        returns an actual reference to the record's data, in the form of an
        Alteryx RecordRef object.  
        If no record_creator object is passed into the function, one will be created using
        the record_info object.
        The function will automatically reset the record_creator if one is passed in.  

    Returns
    ---------
    Tuple(object, object)
        First value in tuple:
            Alteryx RecordRef object, with each Field populated with the respective values
            in the values_list parameter.
        Second value in tuple:
            Alteryx RecordCreator object.  If one was passed in as a parameter, it returns it
            after creating a record with it.  
            If one is not passed in, it creates a new one from the RecordInfo param, uses it to
            create a record, and returns it.  
    """
    columns = [
        Column(names_list[i], types_list[i], values_list[i])
        for i in range(len(names_list))
    ]

    if record_info.num_fields == 0:
        for column in columns:
            add_output_column_to_record_info(column, record_info)
    if record_creator:
        record_creator.reset()
    else:
        record_creator = record_info.construct_record_creator()

    for column in columns:
        field = record_info.get_field_by_name(column.name)
        set_field_value(field, column.value, record_creator)

    ayx_record = record_creator.finalize_record()

    return (ayx_record, record_creator)


# interface
def add_output_column_to_record_info(
    output_column: tuple, record_info_out: object
) -> None:
    """
    Adds a column to a RecordInfo object

    Parameters
    ----------
    output_column: tuple
        A tuple containing the metadata on the new column (name, type)

    record_info_out: object
        RecordInfo object to append the new column to

    Returns
    ---------
    None
    """
    add_new_field_to_record_info(
        record_info_out, output_column.name, output_column.type
    )


# interface
def get_all_interfaces_batch_records(plugin: object) -> Dict[str, Any]:
    batch_records = {}
    for input_name, input_interface in plugin.state_vars.input_anchors.items():
        col_types = input_interface.interface_record_vars.column_types
        if plugin.process_data_input_type == "list":
            input_data = input_interface.interface_record_vars.record_list_in
            col_names = input_interface.interface_record_vars.column_names
        else:
            if pd is None:
                plugin_utils.log_and_raise_error(
                    plugin.logging,
                    ImportError,
                    "The Pandas library must be installed to use the dataframe type.",
                )

            input_data = pd.DataFrame(
                input_interface.interface_record_vars.record_list_in,
                columns=input_interface.interface_record_vars.column_names,
            )
            col_names = None

        batch_records[input_name] = {
            "data": input_data,
            "metadata": {"col_names": col_names, "col_types": col_types},
        }

    return batch_records


# interface
def is_dataframe(input: Any) -> bool:
    """
    Checks if the input variable is a pandas dataframe

    Parameters
    ----------
    input
        Any variable

    Returns
    ---------
    bool
        Indication if the input is a pandas dataframe
    """
    if pd is None:
        # Can't be a dataframe because pandas isn't available for import
        return False

    return isinstance(input, pd.DataFrame)


# interface
def dataframe_to_list(df: object) -> List[List[Any]]:
    """
    Converts a pandas dataframe to a list of lists

    Parameters
    ----------
    df: object
        A pandas dataframe

    Returns
    ---------
    List[List[Any]]
        A list of lists of the pandas dataframe data
    """
    return df.values.tolist()

