# SPDX-FileCopyrightText: 2021 8tronix GmbH, Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json


class IdManager:

    def __init__(self, size: int = 2**8-1):
        self._size = size
        self._queue = list(range(size))

    def pop(self):
        if not self._queue:
            raise RuntimeError('maximum number of jobs exceeded')  # TODO
        return Id(self._queue.pop(0), self)

    def put(self, value):
        self._queue.append(value)


class Id:

    def __init__(self, value: int, manager: IdManager):
        self._value = value
        self._manager = manager

    @property
    def value(self):
        return self._value

    def destroy(self):
        self._manager.put(self._value)


class JsonEncoder(json.encoder.JSONEncoder):

    def default(self, o):
        if isinstance(o, Id):
            return o.value
        super().default()
