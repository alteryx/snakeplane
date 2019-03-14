# Snakeplane Pilot

## The Alteryx Python SDK Development Environment

Snakeplane Pilot is a build system to make the [Alteryx Python SDK](https://help.alteryx.com/developer/current/Python/Overview.htm) developer experience simple, fun, and smooth. As you may determine from it's name, it is centered around Alteryx's open-source Python SDK abstraction layer Snakeplane. Think of Snakeplane Pilot as a combination of scaffolding and build system that incorporates best practices for using snakeplane to build Python based tools for Alteryx Designer.

Snakeplane itself was created in order to support the development of Alteryx's upcoming Code Free Machine Learning Tools, and over time a development pipeline started to take shape. We've stripped away all of our tool code, leaving just the environment that we used to make the Code Free ML Tools. This includes an intuitive file structure, and helpful commandline tools to increase velocity.

## Support

Copyright 2019 Alteryx Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Setup

Snakeplane is designed to be used with the Alteryx Python SDK in Alteryx Designer v2018.4+.

## Issues

Any issues found should be reported as GitHub issues on this repository.

## Key Features

1. Packages source code into [YXIs](https://help.alteryx.com/current/AlteryxFiles.htm?#YXI__Packaged_tool_) for distribution.
2. Builds tool source code and places in Designer tool directory for easy, iterative development and testing.
3. Provides a template for structuring and testing tool source code.
4. Snakeplane is built-in, with example tools for different modes.
   - Batch mode - All records will be pulled into the tool before it is operated on, for things like sorting and aggregations.
   - Streaming mode - One record at a time is processed, for operations that are independent, such as filtering or transforming.
   - Source mode - For tools which either generate data or pull it from a non-Alteryx source such as an API.

## Overview

This document will go over how to setup your environment, how to structure your tools, building, debugging, and packaging. For specifics on how to use snakeplane itself, refer to the readme located in the root of the repository.

## Setting Up Your Environment

After the repo has been forked, you'll need to setup your environment.

Follow the steps below to complete the environment setup:

1. Complete the steps found under `Python installation` of [Python SDK](https://help.alteryx.com/developer/current/Python/Overview.htm).
2. Run `env/setup_environ.bat` from within the `pilot` directory. This script will create a virtual environment, using Alteryx's install of python, install snakeplane's dependencies, as well as Alteryx SDK's dependencies.

## Activating Your Environment

After you have run the script, make sure you are in the pilot directory of the snakeplane folder. Then run the following command in Powershell:

`.\env\Scripts\activate.ps1`

or for Command Prompt:

`.\env\Scripts\activate.bat`

You should now see that your terminal is preceded by `(env)`.

Always activate your environment before attempting to use the invoke commands.

## Creating Your First Tool

1. Create a copy of an example tool folder and place it in the src directory.
   - src\ExampleBatchTool - For tools that requires all records to be pulled into the tool before processing - for things like sorting and aggregations.
   - src\ExampleStreamTool - For tools that process one record at a time - for operations that are independent, such as filtering or transforming.
   - src\ExampleSourceTool - For tools which either generate data or pull it from a non-Alteryx source such as an API.
2. Rename all of the internal files, with your tool folder, with your tool name to match the proper schema. (e.g. snakeplane_exampleGui.html -> newtoolGui.html).
3. Edit the config and gui files.
   - Reference [Package a Tool](https://help.alteryx.com/developer/current/PackageTool.htm) for additional guidance on editing the config files.
   - Reference [HTML GUI SDK](https://help.alteryx.com/developer/current/HTML/Overview.htm) for additional guidance on editing the gui files.
4. Create your tool logic in main.py.

## Building

After you've setup the initial stages of your tool, you probably want to test and debug it. Somehow we need to get all of the files from this environment over into Alteryx's environment. Luckily, we have done 99% of the work for you here.

_Perform these steps from the pilot directory of your repo and make sure you have run `.\env\Scripts\activate.ps1` in PowerShell and see `(env)` in the terminal_

1. If you installed any dependencies with pip, you will need to freeze them. `invoke freeze`
2. Now all we have to do is use the `invoke build <name> -u` command. The `-u` updates our dependencies.
3. Subsequent builds don't need the `-u` flag.
4. Now your tool should exist in designer! The tool files will be found in `C:\Users\your-username\AppData\Roaming\Alteryx\Tools`
5. You will have to restart Alteryx Designer if this is your first time changing your tool, or if any changes to the config.xml file have been made.

## Invoke Commands

We use a framework called **Invoke** to create our console commands. They require you to have activated your virtual environment (env/Scripts/activate.ps1).

    * Use ```inv[oke] -l``` to see a list of commands
    * Use ```inv[oke] --help <command>``` for help with a specific command

## Adding Additional Files or Directories to Tool

Sometimes, there is a need to include additional files or directories with a tool. For example, a machine learning tool will often have a pre-trained model stored in a file that needs to be present to operate. To add these kinds of custom files or directories, do the following:

1. Open the tasks.py file in a text editor.
2. At the top of the file, on line 22, you will see a line that contains the following:
   `extras = []`
3. In the case of including a file in your tool, simply place it in a directory at the top level of your individual tool, for example ExampleBatchTool/src/machine_learning_model_files
4. Change the line in the tasks.py file to this: `extras = ['machine_learning_model_files']`
5. Now your build command will pick up the directory and package it with the tool.

## Debugging

You'll have to do a bit more heavy lifting with the debugging process.

_Perform these steps from the pilot directory of your repo and make sure you have run `.\env\Scripts\activate.ps1` in PowerShell and see `(env)` in the terminal_

1. Create a workflow that uses your tool, and configure it.
2. Save the workflow into the 'debug_workflows' directory with the same name as your tool.
3. Use the `invoke debug <name>` command to run your workflow in the console. This will allow you to interact with your code at breakpoints, and see the full stack trace for any python errors.

For additional information on debugging Alteryx Python SDK tools running in Alteryx Designer, see [this blog post.](https://community.alteryx.com/t5/Dev-Space/Python-SDK-How-to-Debug-an-Error-using-pdb-package/td-p/93523)

## Packaging

Now that you have perfected your tool, you probably want to share it using a '.yxi'. There is a folder named 'package' that contains all of your built tools, a config.xml file, and an icon. The config.xml and icon are purely for your installer. This allows you to bundle multiple tools into one '.yxi' file.

_Perform these steps from the pilot directory of your repo and make sure you have run `.\env\Scripts\activate.ps1` in PowerShell and see `(env)` in the terminal_

1. Edit the config and icon to your liking.
2. Run the `invoke package <name>` command, where name is the desired output name.
3. Find your package in the 'target_yxis' folder.

## Submitting Issues

This framework is in no way finished, and likely has many flaws. We will continue to update it as we work on our tools, but don't hesitate to submit issues that you find.
