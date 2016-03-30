<!--
Copyright 2016, 2017 IBM Corp.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->
# Table of contents

- [Rationale](#rationale)
- [File organization](#file-organization)
    - [Use spaces instead of tabulations for indentation](#use-spaces-instead-of-tabulations-for-indentation)
    - [Ensure each file has the sections: "imports", "constants and definitions" and "code"](#ensure-each-file-has-the-sections-imports-constants-and-definitions-and-code-)
    - [Do not mix classes and functions in the same file](#do-not-mix-classes-and-functions-in-the-same-file)
    - [Break lines at column 80](#break-lines-at-column-80)
    - [Break multiline subroutine calls in the standard way](#break-multiline-subroutine-calls-in-the-standard-way)
    - [Break multiline data structure definitions in the standard way](#break-multiline-data-structure-definitions-in-the-standard-way)
    - [Split methods that have more than 50 lines](#split-methods-that-have-more-than-50-lines)
    - [Sort methods and functions by name](#sort-methods-and-functions-by-name)
    - [Sort imports by name and type](#sort-imports-by-name-and-type)
    - [Never import *](#never-import-)
- [Naming conventions](#naming-conventions)
    - [Class names](#class-names)
    - [Callable names (functions, methods)](#callable-names-functions-methods)
    - [Non-callable names (attributes, values)](#non-callable-names-attributes-values)
    - [Constants](#constants)
- [Code documentation](#code-documentation)
    - [Document all classes, methods and functions with docstrings](#document-all-classes-methods-and-functions-with-docstrings)
    - [Write a comment for each logical block of code](#write-a-comment-for-each-logical-block-of-code)
    - [Ensure there is a comment at least every 5 lines](#ensure-there-is-a-comment-at-least-every-5-lines)
    - [Always comment if, elif and else like: # condition: action](#always-comment-if-elif-and-else-like-condition-action)
- [Branching: if, elif and else](#branching-if-elif-and-else)
    - [Do not use 'else' after an 'if' that always returns](#do-not-use-else-after-an-if-that-always-returns)
    - [If an 'else' always returns make it be the 'if' by inverting the condition](#if-an-else-always-returns-make-it-be-the-if-by-inverting-the-condition)

# Rationale

This document defines the project's coding guidelines so that we can spend less time trying to understand our code and avoid bugs that are more likely introduced in code that is not well understood.

# File organization

## Use spaces instead of tabulations for indentation

- **Rationale I:** mixing up spaces and tabs might confuse other developers and even the python interpreter
- **Rationale II:** tabs have variable size and are user-configurable, spaces aren't
- use 4 spaces for each indentation block
- don't mix indent levels. i.e. always use 4 spaces, regardless of how nested the block is (**Tip** - On Vim use: `:set expandtab`)

## Ensure each file has the sections: "imports", "constants and definitions" and "code"

- **Rationale:** improve code organization
- separate each section with a blank line
- put imports only the in the section `IMPORTS`
- define constants only in the section `CONSTANTS AND DEFINITIONS`
- define classes or functions only in the section `CODE`

### Noncompliant example

```python
    BUFFER_SIZE = 4096

    import os
    from moduleB.submodule import objectB
    import sys

    from moduleA import objectA

    TEMPLATES_DIR = '/opt/templates'

    class SomeClass(object):
        ...
    # SomeClass
```

### Compliant example

```python
    #
    # IMPORTS
    #
    from moduleA import objectA
    from moduleB.submodule import objectB

    import os
    import sys


    #
    # CONSTANTS AND DEFINITIONS
    #
    BUFFER_SIZE = 4096
    TEMPLATES_DIR = '/opt/templates'


    #
    # CODE
    #
    class SomeClass(object):
        ...
    # SomeClass
```

## Do not mix classes and functions in the same file

- **Rationale:** improve code organization and modularization (one file, one module)
- define a single class or single library of functions in a file
- Do not define more than one class in the same file. Acceptable exception is if it's an internal class for module's internal use (which must be explicitly stated in the class documentation then).

## Break lines at column 80

- **Rationale I:** the bigger a line is, the harder it is to follow and read it
- **Rationale II:** ensure the code can be easily read in a terminal
- **Exception:** do not break string definitions

## Break multiline subroutine calls in the standard way

- **Rationale:** straight alignment makes multiline calls easier to read
- this only applies to lines that must be broken due to the rule *Break lines at column 80*

### Noncompliant example

```python
result = myLongModuleName.myLongInstanceName(parameterA,
    parameterB,
    parameterC)
```

### Compliant examples

```python
# preferred way
result = myLongModuleName.myLongInstanceName(parameterA,
                                             parameterB,
                                             parameterC)

# alternative when the preferred way does not work
result = myLongModuleName.myLongInstanceName(
    parameterA,
    parameterB,
    parameterC
)
```

## Break multiline data structure definitions in the standard way

- **Rationale I:** straight alignment makes data structures easier to read
- **Rationale II:** less error prone when adding/removing entries to variable
- this applies to lines that must be broken due to the rule *Break lines at column 80*
- it may also be used in other cases, as the developer prefers

### Noncompliant examples

```python
# list definition
listA = [
    elementA,
    elementB,
    elementC]

# tuple definition
tupleA = (elementA,
elementB,
elementC)

# set definition
setA = set([
    elementA,
    elementB,
    elementC,
    ])

# dict definition
dictA = {
'keyA': 'valueA',
'keyB': 'valueB',
'keyC': 'valueC',}
```

### Compliant examples

```python
# list definition
listA = [
    elementA,
    elementB,
    elementC,
]

# tuple definition
tupleA = (
    elementA,
    elementB,
    elementC,
)

# set definition
setA = set([
    elementA,
    elementB,
    elementC,
])

# dict definition
dictA = {
    'keyA': 'valueA',
    'keyB': 'valueB',
    'keyC': 'valueC',
}
```

## Split methods that have more than 50 lines

- **Rationale I:** the smaller a method is, the faster it is to understand what it does
- **Rationale II:** the bigger a method is, more likely it will have a bug

## Sort methods and functions by name

- **Rationale:** make it easier to find a method in a class or a function in a module

### Noncompliant example

```python
    class SomeClass(object):

        def methodB(self):
            ...
        # methodB

        def __privateB(self):
            ...
        # __privateB

        def methodA(self):
            ...
        # methodA

        def methodC(self):
            ...
        # methodC

        def __privateA(self):
            ...
        # __privateA

    # SomeClass
```

### Compliant example

```python
    class SomeClass(object):

        def __privateA(self):
            ...
        # __privateA

        def __privateB(self):
            ...
        # __privateB

        def methodA(self):
            ...
        # methodA

        def methodB(self):
            ...
        # methodB

        def methodC(self):
            ...
        # methodC

    # SomeClass
```

## Sort imports by name and type

- **Rationale:** make it easier to find an import in the list
- do not import more than one object in the same line
- group imports of the type `from module import something`
- group imports of the type `import module`
- sort the imports by module name inside a group

### Noncompliant example

```python
    import moduleC
    from moduleA.submoduleB import objectC
    from moduleA import objectA
    import moduleD, moduleE
    from moduleB import objectD, objectE
    from moduleA.submoduleA import objectB
```

### Compliant example

```python
    from moduleA import objectA
    from moduleA.submoduleA import objectB
    from moduleA.submoduleB import objectC
    from moduleB import objectD
    from moduleB import objectE

    import moduleC
    import moduleD
    import moduleE
```

## Never import *

- **Rationale:** avoid problems to find out where a name referenced in a file has been defined

### Noncompliant example

```python
    from moduleA import *
    from moduleB import *

    # can you tell where someVariable has been defined?
    print someVariable

    # can you tell where otherVariable has been defined?
    print otherVariable
```

### Compliant example

```python
    from moduleA import someVariable
    from moduleB import otherVariable

    # now you easily know that someVariable is defined in moduleA
    print someVariable

    # now you easily know that otherVariable is defined in moduleB
    print otherVariable
```

# Naming conventions

- in a nutshell:
    - use lowercase with underscores for non-callables (attributes, values)
    - camelCase for callables (functions, methods)
    - SomeClass for classes
- **Rationale:** make it easy to tell if a variable is some value (has underscores) or some function (no underscores)
- see detailed explanation below

## Class names

- capitalize each and every part of the name: `SomeClass`
- never use underscore to separate the parts of the name

### Noncompliant examples

```python
    class someClass:
        ...
    # someClass

    class Some_Class:
        ...
    # Some_Class

    class SOME_CLASS:
        ...
    # SOME_CLASS
```

### Compliant example

```python
    class SomeClass:
        ...
    # SomeClass
```

## Callable names (functions, methods)

- capitalize each part of the name, *except* the first one: `publicMethodName`
- names of class private methods start with 2 underscores: `__privateMethodName`
- never use underscore to separate the parts of the name

### Noncompliant examples

```python
    def PublicMethodName(...):
        ...
    # PublicMethodName

    def public_method_name(...):
        ...
    # public_method_name

    def PUBLIC_METHOD_NAME(...):
        ...
    # PUBLIC_METHOD_NAME
```

### Compliant examples

```python
    def __privateMethodName(...):
        ...
    # __privateMethodName

    def publicMethodName(...):
        ...
    # publicMethodName
```
```python
    def someFunction(...):
        ...
    # someFunction

    def someOtherFunction(...):
        ...
    # someOtherFunction
```

## Non-callable names (attributes, values)

- lowercase each part of the name, and separate them by underscore: `local_variable`

### Noncompliant examples

```python
    localVariable = 123
    LocalVariable = 123
    LOCAL_VARIABLE = 123
```

### Compliant examples

```python
    local_variable = 123
    some_other_variable = 'Error message'
```

## Constants

- the names of constants and definitions are always uppercased
- if non-callable, use underscores to separate the parts of the name

### Noncompliant examples

```python
bufferSize = 4096
buffer_size = 4096
BufferSize = 4096
MAIN_PROC = someModule
mainProc = someModule
main_proc = someModule
```

### Compliant example

```python
BUFFER_SIZE = 4096
MAINPROC = someModule
```

# Code documentation

## Document all classes, methods and functions with docstrings

- **Rationale:** ensure the classes, methods and functions have well-defined and documented roles and interfaces
- docstrings should be writen following [Google Style](https://google.github.io/styleguide/pyguide.html#Comments)

### Noncompliant example

```python
    class Calculator(object):
        ...

        def add(self, paramA, paramB)
            ...
        # add()

    # Calculator
```

### Compliant example
```python
    class Calculator(object):
        """
        This class represents a calculator. It can do addition and
        multiplication.
        """

        def add(self, paramA, paramB = 0.0)
            """
            Returns the sum of paramA and paramB. If paramB is not
            passed, assume 0.0 as its value.

            Args:
                paramA: first float number to be added
                paramB: second float number to be added

            Returns:
                sum of paramA and paramB

            Raises:
                TypeError: if paramA or paramB is not a float
            """
            ...
        # add()

        ...

    # Calculator
```

## Write a comment for each logical block of code

- **Rationale:** clearly describe the algorithm implemented by the code, making it easier to understand
- any algorithm has well-defined steps and each step is implemented by one or more lines of code
- a logical block is the group of lines that implement a step of the algorithm
- use a comment to describe what a logical block (algorithm step) does
- separate each logical block with a blank line

### Noncompliant example

```python
    stream = open('/etc/resolv.conf', 'r')
    data = stream.data()
    stream.close()
    output = []
    for line in data.readlines():
        if len(line) > 0:
            output.append(line)
    stream = open('/etc/resolv.conf', 'w')
    stream.write('\n'.join(output))
    stream.close()
```

### Compliant example

```python
    # read the data from /etc/resolv.conf
    stream = open('/etc/resolv.conf', 'r')
    data = stream.data()
    stream.close()

    # get only the non-empty lines
    output = []
    for line in data.readlines():
        if len(line) > 0:
            output.append(line)

    # write the chosen lines to the file
    stream = open('/etc/resolv.conf', 'w')
    stream.write('\n'.join(output))
    stream.close()
```

## Ensure there is a comment at least every 5 lines

- **Rationale:** more than 5 lines without a comment start to make code harder to understand than it should be
- every logical block (algorithm step) should have a comment
- if a logical block has more than 5 lines of code, it can likely be split into smaller ones

## Always comment if, elif and else like: # condition: action

- **Rationale:** make it *immediately clear* what condition is being checked and what action is taken on it

### Noncompliant example

```python
    if  not os.stat(dir)[0] & 16384 or os.stat(dir)[6] < MIN:
        ... line one ...
        ... line two ...
        ... line tree ...

    elif os.stat(dir)[6] % 2 != 0:
        ... line one ...
        ... line two ...
        ... line tree ...
        ... line four ...
        ... line five ...
        ... line six ...
        ... line seven ...

    else:
        ... line one ...
        ... line two ...

```

### Compliant example

```python
    # not a directory or no space enough available: cleanup and abort
    if  not os.stat(dir)[0] & 16384 or os.stat(dir)[6] < MIN:
        ... line one ...
        ... line two ...
        ... line tree ...

    # size is not a multiple of 2: run the code in special mode
    elif os.stat(dir)[6] % 2 != 0:
        ... line one ...
        ... line two ...
        ... line tree ...
        ... line four ...
        ... line five ...
        ... line six ...
        ... line seven ...

    # directory with space enough: run the code
    else:
        ... line one ...
        ... line two ...
```

# Branching: if, elif and else

## Do not use 'else' after an 'if' that always returns

- **Rationale:** linear code is easier to follow and understand than nested code

### Noncompliant example

```python
    # some condition: do something
    if condition == True:
        ... do something ...
        return

    # or: do other thing
    else:
        ... first line ...
        ... second line ...
        ... third line ...

        # other condition: run my nested if
        if other < 10:
            ... fourth line ...
            ... fitth line ...
            ... sixth line ...

        # run a few more lines
        ... seventh line ...
        ... eighth line ...
```

### Compliant example

```python
    # some condition: do something
    if condition == True:
        ... do something ...
        return False

    # or: do other thing
    ... first line ...
    ... second line ...
    ... third line ...

    # other condition: run my (no longer) nested if
    if other < 10:
        ... fourth line ...
        ... fitth line ...
        ... sixth line ...

    # run a few more lines
    ... seventh line ...
    ... eighth line ...
```

## If an 'else' always returns make it be the 'if' by inverting the condition

- **Rationale:** linear code is easier to follow and understand than nested code
- in case the *if* will always return too, then the case is covered in the [in this guideline](#do-not-use-else-after-an-if-that-will-always-return)

### Noncompliant example

```python
    # condition is ok: run many lines
    if condition == True:
        ... first line ...
        ... second line ...

        # other condition: run my nested if
        if other < 10:
            ... third line ...
            ... fitth line ...
            ... sixth line ...
            ... seventh line ...
            ... eighth line ...

        # run a few more lines
        ... nineth line ...
        ... tenth line ...
        ... eleventh line ...

    # error: stop here
    else:
        return False
```

### Compliant example

```python
    # error: stop here
    if condition != True:
        return False

    # condition is ok: run many lines
    ... first line ...
    ... second line ...

    # other condition: run my (no longer) nested if
    if other < 10:
        ... third line ...
        ... fitth line ...
        ... sixth line ...
        ... seventh line ...
        ... eighth line ...

    # run a few more lines
    ... nineth line ...
    ... tenth line ...
    ... eleventh line ...
```
