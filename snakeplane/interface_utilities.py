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
"""Interface utilities for the snakeplane library."""

# Standard Library
from collections import namedtuple
from typing import Any, List, Optional, Tuple

# Alteryx Libraries
import AlteryxPythonSDK as sdk

# 3rd Party Libraries
import numpy as np
try:
    import pandas as pd
except ImportError:
    pd = None


# Create a column named tuple for use in below functions
Column = namedtuple(
    "Column", ["name", "type", "size", "scale", "source", "description", "value"]
)


def get_dataframe_from_records(
    record_info: sdk.RecordInfo, record_list: List[sdk.RecordRef]
):
    """Convert a list of records into a dataframe."""
    if pd is None:
        err_str = f"Pandas must be installed."
        raise NotImplementedError(err_str)

    col_names = get_column_names_list(record_info)

    data = []
    for record in record_list:
        row = [get_dynamic_type_value(field, record) for field in record_info]
        data.append(row)

    try:
        return pd.DataFrame(data, columns=col_names)
    except ImportError:
        err_str = """The Pandas library must be installed to
                    allow dataframe as input_type."""
        raise ImportError(err_str)


def get_dynamic_type_value(field: sdk.Field, record: sdk.RecordRef) -> Any:
    """
    Extract a field from a record, dynamically calculating its type.

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
    -------
    Any
        The return value of this function can be any of types blob, int32, int64,
        dobule, bool, or string. The returned value represents the parsed/typed
        value of the desired field from the input record
    """
    try:
        return {
            "blob": field.get_as_blob,
            "byte": field.get_as_int32,
            "int16": field.get_as_int32,
            "int32": field.get_as_int32,
            "int64": field.get_as_int64,
            "float": field.get_as_double,
            "double": field.get_as_double,
            "date": field.get_as_string,
            "time": field.get_as_string,
            "datetime": field.get_as_string,
            "bool": field.get_as_bool,
            "string": field.get_as_string,
            "v_string": field.get_as_string,
            "v_wstring": field.get_as_string,
            "wstring": field.get_as_string,
            "fixeddecimal": field.get_as_double,
        }[str(field.type)](record)
    except KeyError:
        # The type wasn't found, throw an error to let the use know
        err_str = f"""Failed to automatically convert field type "{str(field.type)}"
                    due to unidentified type name. This is due to a currently unsupported type."""
        raise TypeError(err_str)


def get_column_names_list(record_info_in: sdk.RecordInfo) -> List[str]:
    """
    Extract the column names from an Alteryx record info object.

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


def get_column_metadata(record_info_in: sdk.RecordInfo) -> dict:
    """
    Extract record metadata from an Alteryx record info object.

    Parameters
    ----------
    record_info_in : object
        An Alteryx RecordInfo object

    Returns
    -------
    List[dict]
        A list of column metadata
    """
    from snakeplane.helper_classes import AnchorMetadata

    metadata = AnchorMetadata()

    for field in record_info_in:
        metadata.add_column(
            field.name,
            field.type,
            size=field.size,
            source=field.source,
            scale=field.scale,
            description=field.description,
        )

    return metadata


def get_column_types_list(record_info_in: sdk.RecordInfo) -> List[object]:
    """
    Collect the column types from an Alteryx record info object.

    Parameters
    ----------
    record_info_in : object
        An Alteryx RecordInfo object
    Returns
    -------
    List[object]
        A list of the column types as per the AlteryxSDK
    """
    return [field.type for field in record_info_in]


def set_field_value(
    field: sdk.Field, value: Any, record_creator: sdk.RecordCreator
) -> None:
    """
    Write a value to its respective field in a given record_creator object.

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
    -------
    None
        This is a stateful function that produces side effects by modifying
        the record_creator object.
    """
    if value is None:
        field.set_null(record_creator)
    elif field.type == sdk.FieldType.bool:
        field.set_from_bool(record_creator, bool(value))
    elif field.type == sdk.FieldType.blob:
        field.set_from_blob(record_creator, bytes(value))
    elif field.type in {
        sdk.FieldType.double,
        sdk.FieldType.float,
        sdk.FieldType.fixeddecimal,
    }:
        if np.isnan(value):
            field.set_null(record_creator)
        else:
            field.set_from_double(record_creator, float(value))
    elif field.type in {sdk.FieldType.byte, sdk.FieldType.int16, sdk.FieldType.int32}:
        if np.isnan(value):
            field.set_null(record_creator)
        else:
            field.set_from_int32(record_creator, int(value))
    elif field.type == sdk.FieldType.int64:
        if np.isnan(value):
            field.set_null(record_creator)
        else:
            field.set_from_int64(record_creator, int(value))
    elif field.type in {
        sdk.FieldType.string,
        sdk.FieldType.v_string,
        sdk.FieldType.v_wstring,
        sdk.FieldType.wstring,
        sdk.FieldType.date,
        sdk.FieldType.datetime,
        sdk.FieldType.time,
    }:
        field.set_from_string(record_creator, str(value))
    else:
        raise ValueError("Unsupported field type found on output.")


def add_new_field_to_record_info(
    record_info: object,
    field_name: str,
    field_type: object,
    field_size: int,
    field_scale: int,
    field_source: str,
    field_desc: str,
) -> None:
    """
    Attaches a field to the specified Alteryx RecordInfo object.

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

    field_source : str
        Where this field came from

    field_desc
        A short description of what this field is

    Returns
    -------
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

    record_info.add_field(
        field_name,
        field_type,
        size=field_size,
        scale=field_scale,
        source=field_source,
        description=field_desc,
    )


def build_ayx_record_info(metadata: dict, record_info: sdk.RecordInfo) -> None:
    """
    Create a record info object from a metadata dictionary.

    Populates a an Alteryx RecordInfo object with field objects based on the
    contents of the names and types specified in names_list and types_list,
    respectively.

    Parameters
    ----------
    metadata : dict
        A dict containing all of the names, types, sizes, sources,
        and descriptions of each field. These are used to generate
        the Alteryx RecordInfo object (if it doesn't already exist)
        for the names of each respective Field object.

    record_info : object
        An Alteryx RecordInfo object.
        Alteryx RecordInfo objects act as containers for the necessary metadata
        needed by the Alteryx engine to generate, identify, and manipulate
        each record of data passing through the tool.

    Returns
    -------
    None
        This is a stateful function that produces side effects by modifying
        the record_info object.

    """
    output_columns = metadata.columns

    for output_column in output_columns:
        add_output_column_to_record_info(output_column, record_info)


def build_ayx_record_from_list(
    values_list: List[Any],
    metadata_list: List[dict],
    record_info: sdk.RecordInfo,
    record_creator: Optional[sdk.RecordCreator] = None,
) -> Tuple[object, object]:
    """
    Build a record from a list of values.

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

    metadata_list : List[dict]
        (This might not be a list)
        A list of the names, types, sizes, sources, and descriptions
        for each respective column. These are used to generate
        the Alteryx RecordInfo object (if it doesn't already exist) for the names
        of each respective Field object.

    record_info : object
        An Alteryx RecordInfo object.
        Alteryx RecordInfo objects act as containers for the necessary metadata
        needed by the Alteryx engine to generate, identify, and manipulate
        each record of data passing through the tool.

    record_creator : Optional[object]
        An optional Alteryx RecordCreator object. The RecordCreator object is created
        by calling the construct_record_creator method on an Alteryx RecordInfo
        object.  It is a stateful object which is populated with values as a
        side-effect of this function.  When its finalize method is called, it
        returns an actual reference to the record's data, in the form of an
        Alteryx RecordRef object.
        If no record_creator object is passed into the function, one will be created
        using the record_info object.
        The function will automatically reset the record_creator if one is passed in.

    Returns
    -------
    Tuple(object, object)
        First value in tuple:
            Alteryx RecordRef object, with each Field populated with the respective
            values in the values_list parameter.
        Second value in tuple:
            Alteryx RecordCreator object.  If one was passed in as a parameter, it
            returns it after creating a record with it.
            If one is not passed in, it creates a new one from the RecordInfo param,
            uses it to create a record, and returns it.
    """
    columns = [
        Column(
            metadata_list[i].name,
            metadata_list[i].type,
            metadata_list[i].size,
            metadata_list[i].scale,
            metadata_list[i].source,
            metadata_list[i].description,
            values_list[i],
        )
        for i in range(len(metadata_list))
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


def add_output_column_to_record_info(
    output_column: tuple, record_info_out: sdk.RecordInfo
) -> None:
    """
    Add a column to a RecordInfo object.

    Parameters
    ----------
    output_column: tuple
        A tuple containing the metadata on the new column (name, type)

    record_info_out: object
        RecordInfo object to append the new column to

    Returns
    -------
    None
    """
    add_new_field_to_record_info(
        record_info_out,
        output_column.name,
        output_column.type,
        output_column.size,
        output_column.scale,
        output_column.source,
        output_column.description,
    )


def is_dataframe(input: Any) -> bool:
    """
    Check if the input variable is a pandas dataframe.

    Parameters
    ----------
    input
        Any variable

    Returns
    -------
    bool
        Indication if the input is a pandas dataframe
    """
    try:
        return isinstance(input, pd.DataFrame)
    except ImportError:
        err_str = """The Pandas library must be installed to
                    allow dataframe as input_type."""
        raise ImportError(err_str)


def dataframe_to_list(df: object) -> List[List[Any]]:
    """
    Convert a pandas dataframe to a list of lists.

    Parameters
    ----------
    df: object
        A pandas dataframe

    Returns
    -------
    List[List[Any]]
        A list of lists of the pandas dataframe data
    """
    return df.values.tolist()
