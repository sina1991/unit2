# Indicator Plugin Architecture

## Overview

The Indicator Plugin Architecture provides a standard way to add, register,
configure and execute technical indicators without modifying core system logic.

The main goals are:

- Add new indicators without changing CLI or Worker code.
- Allow users to configure indicators through CLI.
- Store indicator configurations in Database.
- Support multiple parameter sets for the same indicator.
- Keep calculation logic isolated from execution infrastructure.

---

# Plugin Structure

Each indicator must be implemented as an independent plugin.

Recommended structure:

```text
app/indicators/plugins/

moving_average/
├── indicator.py
├── schema.py
├── README.md
└── tests/
````
Contains calculation logic.
Example:
```
class MovingAverage(Indicator):    ...
```
The implementation must follow the Indicator contract.
Defines user configurable parameters.
The CLI uses this schema to generate input questions.
Example:
```
PARAMETERS = {    "periods": {        "type": "multiple_integer",        "required": true,        "default": [20]    }}
```
Contains indicator documentation:
- Description
- Parameters
- Output fields
- Examples
Every indicator must implement:
```
class Indicator(ABC):    @property    def metadata(self) -> IndicatorMetadata:        ...    def calculate(        self,        candles,        parameters    ):        ...
```
The calculation layer must not access:
- Database
- CLI
- Worker
- API
The indicator only receives input data and returns calculated output.
Each indicator provides metadata:
```
identifier
display_name
implementation_version
description
default_parameters
required_lookback
```
Metadata is stored in:
```
indicators
```
Database table.
Example:
```
{
 "identifier": "moving_average",
 "version": "1",
 "required_lookback": 20
}
```
Parameters define how users configure an indicator.
Example:
Moving Average:
```
{
 "periods": [5,20,50]
}
```
A parameter set is stored in:
```
indicator_parameter_sets
```
Multiple configurations can exist for one indicator.
Example:
```
Moving Average

Parameter Set 1:
period = 5

Parameter Set 2:
period = 20
```
The system discovers available indicators from the plugin directory.
Flow:
```
CLI
 |
 |
Indicator Discovery
 |
 |
Load Plugin Metadata
 |
 |
Display Available Indicators
```
Example:
```
Available Indicators:

1. Moving Average
2. RSI
3. MACD
```
An indicator instance represents a configured execution target.
Example:
```
{
 "indicator_id": "moving_average",
 "parameter_set_id": "xxxx",
 "symbol": "XAUUSD",
 "interval": "1m"
}
```
Instances are stored in:
```
indicator_instances
```
Lifecycle:
```
Created
 |
Active
 |
Running
 |
Disabled/Error
```
CLI provides interactive number based menus.
Example:
```
DB Analytics

1. Indicators
2. Instances
3. Run Calculation
4. Worker
0. Exit
```
Indicator creation flow:
```
Select Indicator

        |
        v

Enter Parameters

        |
        v

Select Symbol

        |
        v

Select Interval

        |
        v

Create Instance
```
The user does not need to know file locations or Python implementation details.
Worker operates on indicator instances.
Flow:
```
Worker

 |
 |
Load Active Instances

 |
 |
Load Indicator Plugin

 |
 |
Load Parameter Set

 |
 |
Fetch Candles

 |
 |
Execute Indicator Engine

 |
 |
Store Results
```
Results are stored in:
```
indicator_values
```
Calculation history is stored in:
```
calculation_runs
```
To add a new indicator:
1. Create plugin directory.
2. Implement Indicator class.
3. Define parameter schema.
4. Add tests.
5. Register indicator.
6. Verify CLI discovery.
7. Enable instance execution.
No modification should be required in:
- Worker
- Engine
- Database schema
- CLI menus

