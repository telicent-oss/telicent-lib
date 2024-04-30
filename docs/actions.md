# Actions

Actions represent components of the Telicent Core platform that do some form of data processing, they provide automation
and progress monitoring of the action. Currently, there are three kinds of actions defined:

- An [`Adapter/AutomaticAdapter`](adapters.md) for importing data into Telicent Core e.g. from legacy systems.
- A [`Mapper`](mappers.md) for performing data transformations within Telicent Core e.g. cleaning, augmenting and
  transforming data.
- A [`Projector`](projectors.md) for exporting data from Telicent Core e.g. into a Smart Cache.

## Automation

Actions provide automated progress monitoring and reporting and where possible fully automate the action. The degree of
automation depends on whether an action is considered to be Automatic or Manual.

An Automatic action is fully automated, and you simply create it and call its `run()` function to perform the action.

A Manual action provides the progress monitoring portion of the API but is managed manually by the caller, i.e. you must
call `report_progress()` and other methods yourself as needed.

You can check whether an action is automatic/manual by calling `is_automatic()` on it. The documentation for individual
action types shows expected usage for each.

## Coloured Output

Actions are configured to support coloured output, allowing different actions to have output in different colours.  
This can be useful in development, test and demo environments where being able to visually distinguish between different
running actions is useful. The desired color is supplied via the `text_colour` parameter of the action constructors.
This should be an ANSI control code for the desired text colour and/or formatting.

Colourised output uses the Python [`colored`][1] library for supporting functions. This has lots of useful constants
available for supplying text colours and styles. Note that if the action detects that it isn't being run in a TTY, or
you supplied `None` as the text colour, then colourised output is disabled. If you want to force it regardless
export the `FORCE_COLOR` environment variable to a non-zero value in your environment.

Note that if you have colourised output enabled and the output is going somewhere that doesn't support it you may see
"junk" sequences in the output which represent the ANSI control codes.

## Startup Banner

When an action runs it displays a Startup banner e.g.

```text
--------------------------------------------------------------------------------
|                                                                              |
|                                TELICENT CORE                                 |
|                                  Projector                                   |
|                                Example Action                                |
|                                                                              |
--------------------------------------------------------------------------------
Started work...
```

This displays the type of action and the name of the action, it may also include some additional information depending
on the action in question e.g.

```text
--------------------------------------------------------------------------------
|                                                                              |
|                                TELICENT CORE                                 |
|                                    Mapper                                    |
|                            Uppercase Transformer                             |
|                                                                              |
--------------------------------------------------------------------------------
Waiting for data from In-Memory Dictionary(4 items) - will write out to In-Memory Dictionary
```

Above we see a mapper action named `Uppercase Transformer` which displays the data source and sink it is using.

You can ask for the startup banner to be shown by calling `action.display_startup_banner()`. Note that an action
remembers whether it has displayed the banner so calling this function multiple times will not display the banner
multiple times.

## Progress Reporting

Progress reporting is provided for all actions in the form of regular print statements that note the current progress
and processing rate of the action. The frequency and level of detail in these statements can be customised to some
extent. Internally a number of progress counters and timers are stored to allow progress to be monitored and reported.
An example progress report statement is shown below:

```text
 25,171 records processed.  Last 25,171 records took 1.46 seconds. Batch rate was 17,260.78 records/seconds. Overall rate is 17,260.75 records/seconds.
```

This includes how many records were processed in the last batch and how long it took. It also incorporates a calculation
of the processing rates of the action both on a batch and an overall level. This is useful because action performance
can fluctuate since some records may require more/less time to process, or they may be pauses while the action is
waiting for new records if some actions run faster than other actions.

Frequency of progress reporting is controlled via the `reporting_batch_size` parameter to the various action
constructors. This takes an `int` denoting the number of records that should be processed before a progress report
statement is issued. For example, the default is `25000` meaning that progress is reporting every 25,000 records,
depending on the performance of your action this should be set higher/lower to ensure that progress is regularly
reported but that we don't spend too much time reporting it. Choosing a suitable value for this is usually a matter of
experimentation with the action you are building.

### Expected Records

If you are processing a data source that has a known number of records you can call `expect_records()` with the expected
number of records, e.g. `action.expect_records(1000000)`, would indicate that 1 million records are expected. When this
has been called progress statements are prefixed with a percentage progress in brackets e.g.

```text
[5.02%] 75,328 records processed.  Last 25,196 records took 1.42 seconds. Batch rate was 17,751.89 records/seconds. Overall rate is 18,854.24 records/seconds.
```

This can be useful in allowing users to see how far along an action is in its processing.

If when the action finishes it has not processed the number of records you declared to be expected it issues a warning
e.g.

```text
Expected number of records was incorrect, expected 1,500,001 but processed 806,641
```

### Incrementing Progress Counters

If you are using an automatic action then incrementing progress counters happens automatically for you, and triggers
[Progress Reporting](#progress-reporting) at appropriate intervals.

For manual actions you may need to call `record_processed()` or `records_processed(10)` as your code runs, the former
increments the internal progress counters by 1 while the latter increments it by the given quantity, this is useful if
your code processes records in batches. There is no requirement for your batch size to align with the
configuring `reporting_batch_size`, as soon as your progress crosses the next reporting boundary a progress report is
triggered.

### Manually Triggering Progress Reports

You can manually trigger a progress report by calling `action.report_progress()`, note that if progress has already been
reported at the current point then calling this has no effect.

### Reporting Final Progress Statistics

For automatic actions final progress statistics are reported when the action is either aborted, e.g. via the process
receiving a `SIGINT` or encountering an unexpected error, or when it naturally finishes i.e. all input records are
processed.

For manual actions you will need to call either `action.aborted()` or `action.finished()` as appropriate. See the
[`Adapter`](adapters.md#example-usage) documentation for an example of this.

Example final statistics are shown below for an aborted action:

```text
Aborted!  Processed 816,216 records in 42.40 seconds at 19,248.78 records/seconds
```

Or for a finished action:

```text
Finished Work, processed 806,641 records in 42.26 seconds at 19,089.25 records/seconds
```

In both cases the statistics show the total records processed, total elapsed time and overall processing rate.

[1]: https://pypi.org/project/colored/