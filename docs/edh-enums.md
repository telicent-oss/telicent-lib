### EDH Security Labels ENUMS

#### Overview

EDH Security Labels provide enumerations to use with the Security Label Builder. They define specific labels for the 
CORE environment, adhering to the EDH/UKIHM standard. The system supports multiple and single value labels, 
as well as complex group logic.

#### Classes and Enums

1. **EDHSecurityLabelsV1 (Enum)**: Represents a simplified version of the EDH standard for the CORE environment.
   - `PERMITTED_ORGANISATIONS`: A `MultiValueLabel` for specifying multiple allowed organizations.
   - `PERMITTED_NATIONALITIES`: A `MultiValueLabel` for defining multiple permitted nationalities.
   - `CLASSIFICATION`: A `SingleValueLabel` for indicating the clearance level.

2. **AndGroups (inherits MultiValueLabel)**: Used for creating conditions where all specified groups must be met (AND logic).
   - `construct(self, *values)`: Constructs a label expression where all values must be true.
   - `create_label(self, value: str)`: Formats the value for AND group logic.

3. **OrGroups (inherits MultiValueLabel)**: Used for creating conditions where any of the specified groups must be met (OR logic).
   - `construct(self, *values)`: Constructs a label expression where any value can be true.
   - `create_label(self, value: str)`: Formats the value for OR group logic.

4. **EDHSecurityLabelsV2 (Enum)**: A more comprehensive representation of the EDH standard.
   - `PERMITTED_ORGANISATIONS`: A `MultiValueLabel` for multiple allowed organizations.
   - `PERMITTED_NATIONALITIES`: A `MultiValueLabel` for multiple permitted nationalities.
   - `CLASSIFICATION`: A `SingleValueLabel` for clearance level.
   - `AND_GROUPS`: An `AndGroups` label for specifying groups where all conditions must be met.
   - `OR_GROUPS`: An `OrGroups` label for specifying groups where any condition can be met.

#### Usage Examples

1. **Using EDHSecurityLabelsV1**
   ```python
   builder = SecurityLabelBuilder()
   builder.add(EDHSecurityLabelsV1.CLASSIFICATION.value, "TopSecret")
   builder.add_multiple(EDHSecurityLabelsV1.PERMITTED_ORGANISATIONS.value, "Org1", "Org2")
   label_expression = builder.build()
   ```
