__license__ = """
Copyright (c) Telicent Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


class Label:

    """
    A label represents an element within a Security Label Expression.

    It is used to define possible labels within a schema, specifically
    dictating how the label is created and importantly defining a construct
    function to be used as part of the Builder pattern
    """

    def __init__(self, name: str, label_type: str):
        self.name = name
        self.label_type = label_type

    def create_label(self, value):
        return f"{self.name}={value}"

    def construct(self, *values):
        raise NotImplementedError()


class MultiValueLabel(Label):
    """
    The basic implementation for a data label which can take on multiple values
    in an expression, usually using an OR logic
    """

    def construct(self, *values):
        condition = "|".join(map(self.create_label, values))
        return f"({condition})"


class SingleValueLabel(Label):
    """
    The basic implementation for a data label which can take on a single label
    in an expression
    """

    def construct(self, *values):
        if len(values) > 1:
            raise ValueError('SingleValueLabel may only have one value')
        return self.create_label(values[0])


class SecurityLabelHelper:
    def add(self, label: SingleValueLabel, value: str):
        """
        Adds single label expression
        """
        raise NotImplementedError()

    def add_multiple(self, label: MultiValueLabel, *values):
        """
        Adds a single label expression with multiple values, evaluated usually with OR logic
        """
        raise NotImplementedError()

    def add_or_expression(self, expression: str):
        """
        Adds an expression as an or, allowing for complex SecurityLabel expressions
        """
        raise NotImplementedError()

    def build(self) -> str:
        raise NotImplementedError()


class SecurityLabelBuilder(SecurityLabelHelper):
    """
    Core requires all messages to have a security label.

    The Security Label Builder is a helper function to make sure Security Labels created are both valid in terms of
    syntax and valid in terms of standards

    The base label set is the current created Security Label Expression, the or expressions are a way to chain multiple
    expressions together e.g

    """

    def __init__(self):
        self.labels = []
        self.or_expressions = []
        self.used_labels = []

    def add(self, label: Label, value: str):
        if label.name in self.used_labels:
            print(
                "WARNING: Be careful adding multiple expressions with the same label - it could make data inaccessible"
            )
        else:
            self.used_labels.append(label.name)
        self.labels.append(label.construct(value))
        return self

    def add_multiple(self, label: MultiValueLabel, *values):
        if label.name in self.used_labels:
            print(
                "WARNING: Be careful adding multiple expressions with the same label - it could make data inaccessible"
            )
        else:
            self.used_labels.append(label.name)
        self.labels.append(label.construct(*values))
        return self

    def add_or_expression(self, expression: str):
        trimmed = expression.strip()
        if trimmed is None or not len(trimmed) >= 2:
            raise ValueError("Valid security label expression required")
        if trimmed[0] != "(" or trimmed[-1] != ")":
            raise ValueError("Valid security label expression should be enclosed "
                             "with brackets (security-label expression)")
        self.or_expressions.append(trimmed)
        return self

    def build(self):
        open_expression = "("
        expression = "&".join(self.labels)
        close_expression = ")" if len(self.or_expressions) == 0 else ")|"
        base_expression = (
            ""
            if len(expression.strip()) == 0
            else f"{open_expression}{expression}{close_expression}"
        )
        ors = "|".join(self.or_expressions)
        return f"{base_expression}{ors}"
