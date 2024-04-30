### Security Label Builder

#### Overview

The Security Label Builder is designed to construct security label expressions. It supports single or multiple value 
labels and allows for complex expressions using logical OR and AND operations. 

This functionality enables management of data accessibility and ensuring compliance with UK security standards - when
used in the context of UKIHM

#### Classes

1. **Label**: Base class for labels in a Security Label Expression.
   - `__init__(self, name: str, label_type: str)`: Initializes a label with a name and type.
   - `create_label(self, value)`: Returns a label expression.
   - `construct(self, *values)`: Abstract method for constructing label expressions.
   
    A label represents an element within a Security Label Expression.

    It is used to define possible labels within a schema, specifically
    dictating how the label is created and importantly defining a construct
    function to be used as part of the Builder pattern

2. **MultiValueLabel (inherits Label)**: Allows multiple values in a label, typically using OR logic.
   - `construct(self, *values)`: Constructs a label expression with multiple values using OR logic.
    
     A data label which can take on multiple values in an expression, usually using an OR logic
   
3. **SingleValueLabel (inherits Label)**: Restricts to a single value in a label.
   - `construct(self, *values)`: Constructs a label expression with a single value. Raises error if multiple values are provided.

4. **SecurityLabelHelper**: Abstract class providing a structure for label manipulation.
   - `add(self, label: SingleValueLabel, value: str)`: Abstract method for adding a single label expression.
   - `add_multiple(self, label: MultiValueLabel, *values)`: Abstract method for adding multiple label expressions.
   - `add_or_expression(self, expression: str)`: Abstract method for adding complex expressions using OR logic.
   - `build(self) -> str`: Abstract method for building the final expression.
   
5. **SecurityLabelBuilder (inherits SecurityLabelHelper)**: Core class for creating valid Security Label expressions.
   - `__init__(self)`: Initializes the builder with empty label sets and expressions.
   - `add(self, label: Label, value: str)`: Adds a label expression. Warns if the label is already used.
   - `add_multiple(self, label: MultiValueLabel, *values)`: Adds a label expression with multiple values.
   - `add_or_expression(self, expression: str)`: Adds an OR expression. Validates the syntax.
   - `build(self)`: Constructs the final Security Label expression.
   
   Method calls can be chained until build is run. 

#### Usage Examples

1. **Creating a Single Value Label**
   ```python
   confidentiality_label = SingleValueLabel("confidentiality", "data_type")
   builder = SecurityLabelBuilder()
   builder.add(confidentiality_label, "classified")
   label_expression = builder.build()
   ```
2. **Creating Multi Value Label**
  ```python
  access_label = MultiValueLabel("access", "user_type")
  builder = SecurityLabelBuilder()
  builder.add_multiple(access_label, "admin", "user")
  label_expression = builder.build()
  ```
3. Adding OR Expressions
   ```python
   builder = SecurityLabelBuilder()
   builder.add_or_expression("(confidentiality=classified)")
   builder.add_or_expression("(access=admin|user)")
   complex_label_expression = builder.build()
   ```

The label builder could be used with any data, a fully working example can be found under `access/ukihm/edh_model.py`,
data validation is enforced by enums which reference labels and model which verifies the user inputs.

In the context of EDH, the label builder would extract a subset of data from EDH Policy, the fields of interest described
by an enum are then passed to the builder where they get transformed to a fully valid label representation that can
be evaluated by Access.

