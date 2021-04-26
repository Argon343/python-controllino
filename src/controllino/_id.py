# SPDX-FileCopyrightText: 2021 8tronix GmbH, Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

"""Utility module for job ID handling."""

import json


class IdManager:
    """Dispenses and recycles IDs.

    Beware! The ``pop`` and ``put`` operations are *not* thread-safe.
    """

    def __init__(self, size: int = 2**8 - 1) -> None:
        """Args:
        size: The maximum number of IDs
        """
        self._size = size
        self._queue = list(range(size))

    def pop(self) -> Id:
        """Get a job ID.

        Raises:
            RuntimeError: If the maximum number of IDs is exceeded
        """
        # FIXME Raise a more specific error on empty queue!
        if not self._queue:
            raise RuntimeError("maximum number of jobs exceeded")
        return Id(self._queue.pop(0), self)

    def put(self, value) -> None:
        """Recycle an ID."""
        self._queue.append(value)


class Id:
    """A disposable ID which is tied to a managed which is responsible
    for recycling.

    The ID wraps an integer value which is used to identify the ID (any
    type of wrapped value is possible, but an immutable is prefered). If
    the ``Id`` object is serialized using ``json``, then the wrapped
    value must be JSON-serializable (see ``JsonEncoder``).
    """

    def __init__(self, value: int, manager: IdManager) -> None:
        """Args:
        value: The wrapped value
        manager:
            A reference to the manager that ``self`` was issued from
        """
        self._value = value
        self._manager = manager

    @property
    def value(self) -> int:
        """The wrapped value."""
        return self._value

    def destroy(self) -> None:
        """Destroy/recycle the ID.

        In most use-cases, this method should only be called before
        deleting ``self``.

        We do not override ``Id.__del__``, as we do not want to rely on
        garbage collection occuring in a timely fashion.
        """
        self._manager.put(self._value)


# FIXME Maybe just serialize ``id.value`` directly?
class JsonEncoder(json.encoder.JSONEncoder):
    def default(self, o):
        """Serialize an ``Id`` by serializing its wrapped value."""
        if isinstance(o, Id):
            return o.value
        super().default()
