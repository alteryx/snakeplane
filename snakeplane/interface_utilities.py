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
from typing import Any, List, Optional, Tuple

import AlteryxPythonSDK as sdk


type_dict = {
    "blob": "get_as_blob",
    "byte": "get_as_int32",
    "int16": "get_as_int32",
    "int32": "get_as_int32",
    "int64": "get_as_int64",
    "float": "get_as_double",
    "double": "get_as_double",
    "date": "get_as_string",
    "time": "get_as_string",
    "datetime": "get_as_string",
    "bool": "get_as_bool",
    "string": "get_as_string",
    "v_string": "get_as_string",
    "v_wstring": "get_as_string",
    "wstring": "get_as_string",
    "fixeddecimal": "get_as_double",
    "spatialob": "get_as_blob"
}


def get_getter_from_field(field):
    return getattr(field, type_dict[str(field.type)])


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
        return getattr(field, type_dict[str(field.type)])(record)
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


type_cast_dict = {
    sdk.FieldType.bool: ("set_from_bool", bool),
    sdk.FieldType.blob: ("set_from_blob", bytes),
    sdk.FieldType.double: ("set_from_double", float),
    sdk.FieldType.float: ("set_from_double", float),
    sdk.FieldType.fixeddecimal: ("set_from_double", float),
    sdk.FieldType.byte: ("set_from_int32", int),
    sdk.FieldType.int16: ("set_from_int32", int),
    sdk.FieldType.int32: ("set_from_int32", int),
    sdk.FieldType.int64: ("set_from_int64", int),
    sdk.FieldType.string: ("set_from_string", str),
    sdk.FieldType.v_string: ("set_from_string", str),
    sdk.FieldType.v_wstring: ("set_from_string", str),
    sdk.FieldType.wstring: ("set_from_string", str),
    sdk.FieldType.date: ("set_from_string", str),
    sdk.FieldType.datetime: ("set_from_string", str),
    sdk.FieldType.time: ("set_from_string", str),
}


def get_field_setter_from_type(field):
    set_attr_name, caster = type_cast_dict[field.type]
    setter = getattr(field, set_attr_name)

    def setter_func(record_creator, value):
        setter(record_creator, caster(value))

    return setter_func


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
        import pandas as pd
    except ImportError:
        err_str = """The Pandas library must be installed to
                    allow dataframe as input_type."""
        raise ImportError(err_str)
    else:
        return isinstance(input, pd.DataFrame)


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
    import numpy as np

    df.replace(np.nan, None, inplace=True)
    return df.values.tolist()
