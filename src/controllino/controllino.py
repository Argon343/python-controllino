# SPDX-FileCopyrightText: 2021 8tronix GmbH, Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import abc
import collections
import json
import queue
import serial
import threading
import traceback
import time
from typing import Callable, TypeVar

from controllino import _id

_VALUE_TYPE = TypeVar('ValueType')
_RX = 'RX_'
_READY = 'READY'
_ERROR = 'ERROR'  # General error message, not bound to specific job
_ERR = 'ERR_'  # Error message bound to job
_INVALID = _ERR + '_COMMAND_INVALID'
GRAIN = 0.001
DELIM = b'\r\n'
NOT_FOUND = object()
verbose = False

# TODO Forward ERR_ commands to the respective futures!


class ControllinoError(Exception):
    """Raise on server-side runtime error."""


# serial device {{{


# Based on
# https://github.com/araffin/python-arduino-serial/blob/master/robust_serial/threads.py
class Base:
    """Base API for serial devices running 8tronix Controllino
    protocoll.

    Controlls two daemons, ``_message_thread`` and ``_command_thread``,
    which handle incoming and outgoing messages, respectively.
    """

    def __init__(self,
                 ser: serial.Serial,
                 error_callback: Optional[Callable[[Exception], None]] = None) -> None:
        """Args:
            ser: The underlying serial device
            error_callback:
                Function to call on critical server-side error

        By default, the error callback will write to the API's error
        queue, which should be checked regularly by the consumer using
        ``process_errors``. By *critical* server-side error we mean an
        error that caused one of the daemon threads to terminate.
        """
        self._serial = ser
        self._serial_lock = threading.Lock()
        self._pending = []  # Commands waiting for a reply.
        self._pending_lock = threading.Lock()
        self._cmd_queue = queue.Queue()
        self._error_queue = queue.Queue()
        self._stop_event = threading.Event()
        if error_callback is None:
            def error_callback(e): return self._error_queue.put(e)
        self._message_thread = _MessageThread(self._serial,
                                              self._serial_lock,
                                              self._pending,
                                              self._pending_lock,
                                              self._stop_event,
                                              error_callback)
        self._command_thread = _CommandThread(self._serial,
                                              self._serial_lock,
                                              self._cmd_queue,
                                              self._stop_event,
                                              error_callback)
        self._id_manager = _id.IdManager()
        self._message_thread.start()
        self._command_thread.start()

    def submit(self, cmd: Command) -> tuple[Future, ...]:
        """Submit a command.

        Returns:
            The futures used to handle the commands results

        Raises:
            RuntimeError:
                If submitting the commnads would exceeded the maximum
                number of jobs
        """
        cmd.job = self._id_manager.pop()

        with self._pending_lock:
            self._pending.append(cmd)
        self._cmd_queue.put(cmd)

        return cmd.future

    def process_errors(self, abort: bool = False) -> None:
        """Check for server-side errors that led to the termination of
        the command or message daemon.

        Args:
            abort: Terminate all daemons on failure if ``True``

        Raises:
            Exception:
                The first error in the error queue, if available
        """
        try:
            e = self._error_queue.get_nowait()
        except queue.Empty:
            return

        if abort:
            self._stop_event.set()
        raise e

    def open(self) -> tuple[Future]:
        """Query readiness from the client device.

        Returns:
            A ``Future`` which is done once readiness is signalled.

        Raises:
            Exception:
                The first error in the error queue, if available
        """
        # Create a pending `CmdReady`, but don't queue it. We're waiting
        # for the device to signal readiness.
        cmd = CmdReady()
        cmd.job = self._id_manager.pop()
        with self._pending_lock:
            self._pending.append(cmd)
        return cmd.future

    def kill(self):
        """Close without grace."""
        self._stop_event.set()
        self._serial.close()


class Controllino(Base):
    """Utility API class which offers class methods for command
    submission.

    See the documentation of ``Base.submit`` and of the respective
    ``Cmd*`` classes for details.
    """

    def get_signal(self, pin: str) -> Future:
        return self.submit(CmdGetSignal(pin))

    def set_signal(self, pin: str, value: _VALUE_TYPE) -> Future:
        return self.submit(CmdSetSignal(pin, value))

    def set_pin_mode(self, pin: str, mode: str) -> Future:
        return self.submit(CmdSetPinMode(pin, mode))

    def get_pin_mode(self, pin: str) -> Future:
        return self.submit(CmdGetPinMode(pin))

    def load_pin_modes(self) -> Future:
        return self.submit(CmdLoadPinModes())

    def save_pin_modes(self) -> Future:
        return self.submit(CmdSavePinModes())

    def reset_pin_modes(self) -> Future:
        return self.submit(CmdResetPinModes())

    def trigger_pulse(self, pin: str) -> Future:
        return self.submit(CmdTriggerPulse(pin))

    def log_signal(self, pin: str, period: int) -> Future:
        # period in ms
        return self.submit(CmdLogSignal(pin, period))

    def end_log_signal(self, pin: str) -> Future:
        return self.submit(CmdEndLogSignal(pin))


# Based on
# https://github.com/araffin/python-arduino-serial/blob/master/robust_serial/threads.py
class _MessageThread(threading.Thread):
    """Daemon thread for handling incoming messages from the client
    device.
    """

    # FIXME Don't share ``pending`` and ``pending_lock`` with the
    # ``Base`` object. Instead, encapsulate ``pending(_lock)?`` and use
    # a ``push`` method to thread-safely enqueue commands.
    def __init__(self,
                 ser: serial.Serial,
                 serial_lock: threading.Lock,
                 pending: list[Command],
                 pending_lock: threading.Lock,
                 stop_event: threading.Event,
                 error_callback: Optional[Callable[[Exception], None]] = None) -> None:
        """Args:
            ser: The underlying serial device
            serial_lock:
                A lock for thread-safe access to the underlying serial
                device
            pending:
                A list of pending responses from the client device that
                the daemon must handle
            stop_event: An event for terminating the daemon
            error_callback:
                A callback function for critical errors in this daemon
        """
        super().__init__()
        self.daemon = True

        self._serial = ser
        self._serial_lock = serial_lock
        self._stop_event = stop_event
        self._pending = pending
        self._pending_lock = pending_lock
        self._error_callback = error_callback
        self._buffer = b''

    def run(self):
        # FIXME The catch-all is for logic errors. Design is meh and not
        # very useful in production.
        try:
            while not self._stop_event.is_set():
                self._run_impl()
                time.sleep(GRAIN)
        except Exception as e:
            self._error_callback(e)
        # Note that there is no clear separation of fatal and non-fatal
        # errors. For example, a JSON error caused by a formatting
        # error breaks the while loop, although such an error is
        # certainly not fatal. A clear separation would require to go
        # through all calls made in ``_run_impl`` and ``_receive`` and
        # separate the errors that may raise fatal and non-fatal errors.

    def _run_impl(self):
        with self._serial_lock:
            byte_count = self._serial.in_waiting

        if byte_count == 0:
            return

        with self._serial_lock:
            self._buffer += self._serial.read(byte_count)

        chunks = self._buffer.split(DELIM)
        self._buffer = chunks.pop(-1)
        chunks = [each + DELIM for each in chunks]

        assert all(each.endswith(DELIM) for each in chunks)
        replies = [json.loads(each) for each in chunks]  # Note: json.JSONDecodeError is considered a logic error and will result in termination of the loop.  # noqa: E501
        for each in replies:
            self._receive(each)

    def _receive(self, reply):
        command_type = reply['command']  # TODO Raise error if command field is missing!

        job = reply.get('job')
        if job is None:
            if command_type.startswith(_ERROR):  # General error
                self._error_callback(ControllinoError(
                    f'controllino: received error msg: {reply}'))
            else:
                self._error_callback(ControllinoError(
                    f'controllino: received out-of-turn reply that is not an error: {reply}'))
            return

        with self._pending_lock:
            index = next((index for index, each in enumerate(self._pending)
                          if each.job.value == job),
                         None)
            if index is None:
                self._error_callback(ControllinoError(
                    f'controllino: receiver reply with invalid job id: {reply}'))
                return
            cmd = self._pending[index]

            if cmd.update(reply):
                cmd.job.destroy()
                del self._pending[index]


# Based on
# https://github.com/araffin/python-arduino-serial/blob/master/robust_serial/threads.py
class _CommandThread(threading.Thread):
    """Daemon thread for handling outgoing messages to the client
    device.
    """

    def __init__(self,
                 ser: serial.Serial,
                 serial_lock: threading.Lock,
                 cmd_queue: queue.Queue,
                 stop_event: threading.Event,
                 error_callback: Optional[Callable[[Exception], None]] = None) -> None:
        """Args:
            ser: The underlying serial device
            serial_lock:
                A lock for thread-safe access to the underlying serial
                device
            cmd_queue: A queue of submitted commands
            stop_event: An event for terminating the daemon
            error_callback:
                A callback function for critical errors in this daemon
        """
        super().__init__()
        self.daemon = True

        self._serial = ser
        self._serial_lock = serial_lock
        self._cmd_queue = cmd_queue
        self._stop_event = stop_event
        self._error_callback = error_callback

    def run(self):
        try:
            while not self._stop_event.is_set():
                try:
                    cmd = self._cmd_queue.get_nowait()
                except queue.Empty:
                    time.sleep(GRAIN)
                    continue
                self._serial.write(_encode(cmd.serialize()))
        except Exception as e:
            self._error_callback(e)


def _encode(data: dict) -> bytes:
    """Encode a message into raw bytes according to the Controllino
    protocol.

    Args:
        data: The message to be encoded

    """
    msg = json.dumps(data, cls=_id.JsonEncoder)
    msg += '\r\n'
    msg = msg.encode('utf-8')
    return msg


class Future:
    """Class that represents future results of pending commands on
    daemon threads.

    A future has a *result*, which may be accessed using ``result()``.
    Is is set (usually by the daemon thread) using ``set_result()``,
    in which case the future is marked as *done*.

    If the computation on the daemon thread has raised an error instead,
    the daemon uses ``set_error()`` to move the error into the future.
    In this case the error is reraised if ``result()`` is called.
    """

    def __init__(self):
        self._result = None
        self._error = None
        self._done = threading.Event()

    def result(self) -> Any:
        """Get the result of the future.

        Returns:
            The result of the future, provided it is set

        Raises:
            Exception:
                The error that occured during computation, provided it
                was set

        Shall only be accessed when the future is done. Calling this
        method before the future is done is undefined behavior.
        """
        if self._error is not None:
            raise self._error
        return self._result

    def set_result(self, result: Any = None) -> None:
        """Set the result of the future and mark the future as done.

        Args:
            result: The result

        The result will be return when ``result`` is called.
        """
        self._result = result
        self._done.set()

    def set_error(self, error: Exception) -> None:
        """Set an error as the result of the future and mark the future
        as done.

        Args:
            error: The error

        The error will be raised when ``result`` is called. Note
        that despite representing a failed task, the future will be
        marked as *done* when calling ``set_error``.
        """
        self._error = error
        self._done.set()

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Thread-safely wait until the future is done.

        Args:
            timeout: Timeout in seconds

        Returns:
            ``True`` if and only if the future is done

        If ``timeout`` is specified, the method will return after
        ``timeout`` seconds. Otherwise, the function will halt until the
        future is done.
        """
        return self._done.wait(timeout)

    def done(self) -> bool:
        """Thread-safely return ``True`` if and only if the future is
        done.
        """
        return self.wait(-1)


# }}} serial device


# commands {{{


class Command(abc.ABC):  # FIXME Should be called AbstractCommand...?
    """ABC for commands issued to client device.

    Attributes:
        job (Optional[_id.Id]): The job id of the command

    Commands are identified (on the server and the client) using their
    manually assigned *job id*, which must be unique in the sense that
    at any point in time, every job id occurs in *at most* one command.

    We use the ``Command`` objects not just to send data to the client
    device, but also to track the result of the computation on the
    client. The ``futures`` property, which consists of one or more
    ``Future`` objects, is used to track the result.

    The usual interpretation of ``future`` is: If ``future`` is done,
    then this means that the command was executed (not necessarily
    successfully), the reply from the client device has arrived on the
    server and the result or error of the computation on the client
    device was set as result of the future.
    """

    def __init__(self):
        self._future = Future()
        self.job: Optional[_id.Id] = None

    @property
    def future(self) -> Union[Future, tuple[Future, ...]]:
        """Return the futures of the command.

        Note that by default, a single future is returned, but children
        of this class (e.g. ``CmdLogSignal``) may opt to return a tuple
        of futures.
        """
        return self._future

    def serialize(self) -> dict:
        """Return a representation of the command data as ``dict``.

        By *command data*, we mean all data relevant to the execution of
        the command on the client device (most likely, this will be all
        the fields of the implementation *except* the future). The job
        id must be stored under the key `'job'`.

        Default implementation, may be overridden by subclasses.
        """
        data = self._serialize()
        data['job'] = self.job
        return data

    def update(self, reply: dict) -> bool:
        """Update the state of the pending command.

        Returns:
            ``True`` if job is done, ``False`` otherwise.

        Default implementation, may be overridden by subclasses.
        """
        if self._error(self._future, reply):
            return True

        if reply['command'] == _RX + self.serialize()['command']:
            return self._update(reply)

    def _serialize(self) -> dict:
        """Serialize the command data *without* the job id and future.

        This is a utility method, used by the default implementation of
        ``serialize``.
        """
        pass

    def _update(self, reply: dict) -> bool:
        """Mark the command's future as done.

        Returns: ``True``

        This is a utility method, used by the default implementation of
        ``update``.
        """
        self._future.set_result()
        return True

    def _error(self, future: Future, reply: dict) -> bool:
        """Forward any error from ``reply`` to ``future``.

        Returns:
            ``True`` if the reply contained an error, ``False``
            otherwise

        This is a utility method, used by the default implementation of
        ``update``.
        """
        command_type = reply['command']  # TODO Raise error if command field is missing!
        if (command_type == _ERR + self.serialize()['command']
                or command_type == 'ERR_COMMAND_INVALID'):
            future.set_error(ControllinoError(f'controllino error: {reply}'))
            return True

        return False  # FIXME Ignore?


class CmdGetSignal(Command):

    def __init__(self, signal: str):
        super().__init__()
        self._signal = signal

    def _update(self, reply: dict) -> bool:
        self.future.set_result(reply['level'])
        return True

    def _serialize(self) -> dict:
        return {'command': 'GET_INPUT', 'pin': self._signal}


class CmdSetSignal(Command):

    def __init__(self, signal: str, value: Any) -> None:
        super().__init__()
        self._signal = signal
        self._value = value

    def _serialize(self) -> dict:
        return {'command': 'SET_OUTPUT', 'pin': self._signal, 'level': self._value}


class CmdReady(Command):

    def _serialize(self) -> dict:
        return {'command': _READY}


class CmdSetPinMode(Command):

    def __init__(self, pin: str, mode: str) -> None:
        super().__init__()
        self._pin = pin
        self._mode = mode

    def _serialize(self) -> dict:
        return {'command': 'SET_PIN_MODE', 'pin': self._pin, 'mode': self._mode}


class CmdGetPinMode(Command):

    def __init__(self, pin: str) -> None:
        super().__init__()
        self._pin = pin

    def _update(self, reply: dict) -> bool:
        self.future.set_result(reply['mode'])
        return True

    def _serialize(self) -> dict:
        return {'command': 'GET_PIN_MODE', 'pin': self._pin}


class CmdLoadPinModes(Command):

    def _serialize(self) -> dict:
        return {'command': 'LOAD_PIN_MODES'}


class CmdSavePinModes(Command):

    def _serialize(self) -> dict:
        return {'command': 'SAVE_PIN_MODES'}


class CmdResetPinModes(Command):

    def _serialize(self) -> dict:
        return {'command': 'RESET_PIN_MODES'}


class CmdTriggerPulse(Command):

    def __init__(self, pin: str) -> None:
        super().__init__()
        self._pin = pin

    def _serialize(self) -> dict:
        return {'command': 'TRIGGER_PULSE', 'pin': self._pin}


TimeSeries = collections.namedtuple('TimeSeries', ('time', 'values'))


class CmdLogSignal(Command):
    """Command class for logging signals.

    Note: Has two futures, one which represents the success of the
    request (done if logging request is accepted), the other represents
    the results of the logging process (done after receiving last update
    after cancelling the request). The command will be removed from the
    pending queue only if all futures are done.

    If a logging request is declined, the request future will fail and
    the process future will wait forever. If a request if accepted but
    the  logging job fails later on, the process future will finish and
    raise an error.

    Example:
        >>> api = controllino.Controllino(...)
        >>> request, recording = api.log_signal(...)
        >>> request.wait(1.0)
        >>> assert request.done()
        >>> # ...
        >>> # Use `recording` to get results later.
        >>> recording.wait(10.0)
        >>> assert recording.done()
        >>> result = recording.result()

    """

    def __init__(self, signal: str, period: int) -> None:
        super().__init__()
        self._future = (Future(), Future())
        self._signal = signal
        self._period = period
        self._time = []
        self._values = []

    def update(self, reply: dict) -> bool:
        if not self._future[0].done():  # First pass!
            if self._error(self._future[0], reply):
                return True
            self._future[0].set_result()

        if self._error(self._future[1], reply):
            return True

        self._time.append(reply['time'])
        self._values.append(reply['value'])
        done = reply['done']
        if done:
            self._future[1].set_result(TimeSeries(self._time, self._values))
        return done

    def _serialize(self) -> dict:
        return {'command': 'LOG_SIGNAL', 'pin': self._signal, 'period': self._period}


class CmdEndLogSignal(Command):

    def __init__(self, signal: str) -> None:
        super().__init__()
        self._signal = signal

    def _serialize(self) -> dict:
        return {'command': 'END_LOG_SIGNAL', 'pin': self._signal}


# }}} commands
