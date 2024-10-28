from __future__ import annotations

import hashlib
import inspect
import os
import re
import socket
from inspect import Parameter
from itertools import islice
from typing import Any

from confluent_kafka.admin import AdminClient

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


def __get_signature__(function: Any) -> inspect.Signature | None:
    """
    Gets the signature for a function (if any)
    :param function: A function or class
    :return: Signature, or None if not a valid function object
    """
    try:
        return inspect.signature(function)
    except TypeError:
        return None
    except ValueError:
        return None


def __get_nth_value__(dictionary: dict[Any, Any], n: int) -> Any:
    """
    Gets the Nth value in a dictionary, only reliable if the dictionary is an ordered dictionary
    :param dictionary: Dictionary
    :param n: Index of value to return
    :return: Value, or None if no Nth value
    """
    iterator = iter(dictionary.items())
    next(islice(iterator, n, n), None)
    item = next(iterator, None)
    if item is None:
        return None
    else:
        return item[1]


def validate_callable_protocol(function: Any, protocol: Any) -> None:
    """
    Validates whether a function meets a given callable protocol

    :param function: Function to check against the Protocol
    :param protocol:
        A callable protocol i.e. a class that extends Protocol and has a private `__call()__` method with the desired
        signature
    :return: None
    :raises ValueError: If function/protocol is None
    :raises TypeError: If function does not conform to the protocol, this will describe how the function fails to
                       conform
    """
    if function is None:
        raise ValueError("function cannot be None")
    if protocol is None:
        raise ValueError("protocol cannot be None")

    # Handle the case where the user provides us an instance of our protocol directly i.e. they've sub-classed our
    # protocol and overridden the __call__() method
    if inspect.isclass(function):
        if callable(function):
            function = function.__call__
        else:
            function = None
    signature = __get_signature__(function)
    if signature is None:
        raise TypeError(f"{function} is not a function and so cannot conform to a protocol")

    # We expect our protocol to have a __call__() method and that's the signature we want to validate against
    sig_inspection = None
    if callable(protocol):
        sig_inspection = protocol.__call__
    required_signature = inspect.signature(sig_inspection)  # type: ignore
    if required_signature is None:
        raise TypeError(f"{protocol} is not a protocol whose validity can be checked")

    has_self = False
    adj = 0
    for i, parameter_tuple in enumerate(required_signature.parameters.items()):
        name, parameter = parameter_tuple

        # Special handling for self parameter
        # Since a protocol is a class its __call__() method will have a self parameter, the function we are trying to
        # validate meets the protocol may not have this if it is just a pure function, as opposed to a subclass of our
        # Protocol class
        if i == 0 and name == "self":
            has_self = True
            if "self" not in signature.parameters.keys():
                adj = 1
            continue

        try:
            actual_parameter: Parameter = __get_nth_value__(signature.parameters, i - adj)  # type: ignore
            if actual_parameter is None:
                raise TypeError(f"Function {function} is missing required parameter {name} of type "
                                f"{parameter.annotation}")

            if parameter.annotation != actual_parameter.annotation:
                if actual_parameter.annotation == inspect.Signature.empty or parameter.annotation != Any:
                    raise TypeError(f"Wrong parameter type for parameter {name} ({actual_parameter.name}) "
                                    f"for protocol {str(protocol)}, "
                                    f"expected {parameter.annotation} but function {function} has "
                                    f"{actual_parameter.annotation}")
        except IndexError:
            raise TypeError(
                f"Missing required parameter {name} of type {parameter.annotation} on function {function}"
            ) from None

    # Check that the function doesn't have any extraneous parameters, remember to account for the fact that the protocol
    # will have a self parameter that the function may be missing
    expected_parameters = len(required_signature.parameters)
    if has_self and "self" not in signature.parameters.keys():
        expected_parameters -= 1

    if len(signature.parameters) != expected_parameters:
        # Extraneous parameters are allowed only if they are keyword args
        if len(signature.parameters) == expected_parameters + 1:
            extra_param: Parameter = __get_nth_value__(signature.parameters,  # type: ignore
                                                       len(signature.parameters) - 1)
            if extra_param.kind == Parameter.VAR_KEYWORD:
                return

        raise TypeError(f"Wrong number of parameters for protocol {str(protocol)}, expected {expected_parameters} "
                        f"but function {function} has {len(signature.parameters)}")


def check_kafka_broker_available(kafka_conf: dict):
    """
    Attempt to list topics on the broker and confirm the broker is responding to requests.
    """
    admin_client = AdminClient(kafka_conf)
    admin_client.list_topics(timeout=10)


def clean_hostname(hostname):
    if "KUBERNETES_SERVICE_HOST" in os.environ:
        return clean_hostname_k8s(hostname)

    # 255 characters limit on group.id, but we prepend to it
    cleaned_hostname = re.sub(r"[^\w]+", "_", hostname)
    return cleaned_hostname[:200]


def clean_hostname_k8s(hostname):

    segments = re.split(r"[-\W_]+", hostname)

    if len(segments) == 1:
        # hash or something we cannot split
        hostname = re.sub(r"[\s\W,]+", "_", segments[0])
        return hostname

    filtered_segments = []
    if len(segments) >= 2:
        # e.g mop-bridge-planner-dc66bbd44-aaswz last element needs dropped
        last_two = segments[-2:]
        segments = segments[:-2]

        # second last elem is char only needs checking
        if re.fullmatch(r"[a-zA-Z]+", last_two[0]):
            # add them back to the list - maybe no hash at all
            segments.extend(last_two)

        filtered_segments = [segment for segment in segments if re.fullmatch(r"[a-zA-Z]+", segment)]
        return "_".join(filtered_segments)

    # not enough segments
    return "_".join(segments)


def generate_group_id():
    hostname = socket.gethostname()
    frame = inspect.stack()[1]
    filename, lineno = frame.filename, frame.lineno
    del frame
    unique_string = f"{filename}:{lineno}"
    unique_hash = hashlib.sha256(unique_string.encode()).hexdigest()[:10]
    hostname = clean_hostname(hostname)
    group_id = f"{hostname}_{unique_hash}"
    return group_id
