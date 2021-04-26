# SPDX-FileCopyrightText: 2021 8tronix GmbH, Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import functools
import pytest
import time

from unittest import mock

from controllino import controllino

WAIT = 0.1
TIMEOUT = 1.0


class DummySerial:

    def __init__(self):
        self._buffer = b''
        self.write = mock.Mock()
        self.close = mock.Mock()

    @property
    def in_waiting(self) -> int:
        return len(self._buffer)

    def put(self, data: str) -> None:
        self._buffer += data

    def read(self, size: int = 1) -> str:
        result = self._buffer[0:size]
        self._buffer = self._buffer[size:]
        return result


@pytest.mark.skip
class TestMessageThread:
    pass


@pytest.mark.skip
class TestCommandThread:
    pass


@pytest.mark.skip
class TestControllino:
    pass


class TestBase:

    @pytest.mark.timeout(TIMEOUT)
    def test_open(self):
        base = controllino.Base(DummySerial())
        future = base.open()
        assert not future.wait(WAIT)

        with base._serial_lock:
            cmd = {'command': 'RX_READY', 'job': 0}
            base._serial.put(controllino._encode(cmd))

        done = future.wait(WAIT)
        base.process_errors()
        assert done

    @pytest.fixture
    def base(self):
        ser = DummySerial()
        _base = controllino.Base(ser)
        future = _base.open()
        assert not future.wait(WAIT)

        with _base._serial_lock:
            cmd = {'command': 'RX_READY', 'job': 0}
            _base._serial.put(controllino._encode(cmd))

        done = future.wait(WAIT)
        _base.process_errors()
        assert done
        yield _base

        _base.kill()
        _base._serial.close.assert_called_once()

    @pytest.mark.timeout(TIMEOUT)
    def test_kill(self, base):
        with base._serial_lock:
            cmd = {'command': 'RX_STOP', 'job': 1}
            base._serial.put(controllino._encode(cmd))
        base.kill()
        base._serial.close.assert_called_once()
        base._serial.close.reset_mock()  # Reset for test at the end of ``base`` fixture!

    @pytest.mark.timeout(TIMEOUT)
    def test_set_signal(self, base):
        future = base.submit(controllino.CmdSetSignal('DAC0', 12))
        assert not future.wait(WAIT)

        with base._serial_lock:
            base._serial.write.assert_called_once_with(
                controllino._encode({'command': 'SET_OUTPUT', 'pin': 'DAC0', 'level': 12, 'job': 1}))
            cmd = {'command': 'RX_SET_OUTPUT',
                   'pin': 'DAC0', 'level': 12, 'job': 1}
            base._serial.put(controllino._encode(cmd))

        done = future.wait(WAIT)
        base.process_errors()
        assert done
        base.process_errors()

    @pytest.mark.timeout(TIMEOUT)
    def test_get_signal(self, base):
        future = base.submit(controllino.CmdGetSignal('A0'))
        assert not future.wait(WAIT)

        with base._serial_lock:
            base._serial.write.assert_called_once_with(
                controllino._encode({'command': 'GET_INPUT', 'pin': 'A0', 'job': 1}))
            value = 123
            cmd = {'command': 'RX_GET_INPUT',
                   'pin': 'A0', 'level': value, 'job': 1}
            base._serial.put(controllino._encode(cmd))

        done = future.wait(WAIT)
        base.process_errors()
        assert done
        assert future.result() == value

    @pytest.mark.timeout(TIMEOUT)
    def test_set_pin_mode(self, base):
        pin = 'D30'
        mode = 'INPUT'
        future = base.submit(controllino.CmdSetPinMode(pin, mode))
        assert not future.wait(WAIT)

        with base._serial_lock:
            base._serial.write.assert_called_once_with(
                controllino._encode({'command': 'SET_PIN_MODE', 'pin': pin, 'mode': mode, 'job': 1}))
            cmd = {'command': 'RX_SET_PIN_MODE',
                   'pin': pin, 'mode': mode, 'job': 1}
            base._serial.put(controllino._encode(cmd))

        done = future.wait(WAIT)
        base.process_errors()
        assert done
        base.process_errors()

    @pytest.mark.timeout(TIMEOUT)
    def test_get_pin_mode(self, base):
        pin = 'D30'
        mode = 'INPUT'
        future = base.submit(controllino.CmdGetPinMode(pin))
        assert not future.wait(WAIT)

        with base._serial_lock:
            base._serial.write.assert_called_once_with(
                controllino._encode({'command': 'GET_PIN_MODE', 'pin': pin, 'job': 1}))
            cmd = {'command': 'RX_GET_PIN_MODE',
                   'pin': pin, 'mode': mode, 'job': 1}
            base._serial.put(controllino._encode(cmd))

        done = future.wait(WAIT)
        base.process_errors()
        assert done
        assert future.result() == mode

    @pytest.mark.timeout(TIMEOUT)
    def test_load_pin_modes(self, base):
        future = base.submit(controllino.CmdLoadPinModes())
        assert not future.wait(WAIT)

        with base._serial_lock:
            base._serial.write.assert_called_once_with(
                controllino._encode({'command': 'LOAD_PIN_MODES', 'job': 1}))
            cmd = {'command': 'RX_LOAD_PIN_MODES', 'job': 1}
            base._serial.put(controllino._encode(cmd))

        done = future.wait(WAIT)
        base.process_errors()
        assert done
        base.process_errors()

    @pytest.mark.timeout(TIMEOUT)
    def test_save_pin_modes(self, base):
        future = base.submit(controllino.CmdSavePinModes())
        assert not future.wait(WAIT)

        with base._serial_lock:
            base._serial.write.assert_called_once_with(
                controllino._encode({'command': 'SAVE_PIN_MODES', 'job': 1}))
            cmd = {'command': 'RX_SAVE_PIN_MODES', 'job': 1}
            base._serial.put(controllino._encode(cmd))

        done = future.wait(WAIT)
        base.process_errors()
        assert done
        base.process_errors()

    @pytest.mark.timeout(TIMEOUT)
    def test_reset_pin_modes(self, base):
        future = base.submit(controllino.CmdResetPinModes())
        assert not future.wait(WAIT)

        with base._serial_lock:
            base._serial.write.assert_called_once_with(
                controllino._encode({'command': 'RESET_PIN_MODES', 'job': 1}))
            cmd = {'command': 'RX_RESET_PIN_MODES', 'job': 1}
            base._serial.put(controllino._encode(cmd))

        done = future.wait(WAIT)
        base.process_errors()
        assert done
        base.process_errors()

    @pytest.mark.timeout(TIMEOUT)
    def test_trigger_pulse(self, base):
        pin = 'D40'
        future = base.submit(controllino.CmdTriggerPulse(pin))
        assert not future.wait(WAIT)

        with base._serial_lock:
            base._serial.write.assert_called_once_with(
                controllino._encode({'command': 'TRIGGER_PULSE', 'pin': pin, 'job': 1}))
            cmd = {'command': 'RX_TRIGGER_PULSE', 'pin': pin, 'job': 1}
            base._serial.put(controllino._encode(cmd))

        done = future.wait(WAIT)
        base.process_errors()
        assert done
        base.process_errors()

    @pytest.mark.timeout(TIMEOUT)
    @pytest.mark.parametrize('cmd, error', [
        pytest.param({'command': 'RX_UNKNOWN', 'job': 8}, controllino.ControllinoError,
                     id='unexpected job id'),
        pytest.param({'command': 'ERR_PANIC'}, controllino.ControllinoError,
                     id='error without job id'),
        pytest.param({'command': 'RX_UNKNOWN'}, controllino.ControllinoError,
                     id='unexpected reply type'),
        pytest.param({'cmd': 'RX_UNKNOWN'}, KeyError,
                     id='missing "command" field')
    ])
    def test_failure(self, cmd, error, base):
        with base._serial_lock:
            base._serial.put(controllino._encode(cmd))
        time.sleep(WAIT)
        with pytest.raises(error):
            base.process_errors()

    @pytest.mark.timeout(TIMEOUT)
    def test_failure_in_future(self, base):
        future = base.submit(controllino.CmdLoadPinModes())

        with base._serial_lock:
            cmd = {'command': 'ERR_LOAD_PIN_MODES', 'job': 1}
            base._serial.put(controllino._encode(cmd))

        done = future.wait(WAIT)
        base.process_errors()
        assert done
        with pytest.raises(controllino.ControllinoError):
            future.result()

    def test_log_signal(self, base):
        request, recording = base.submit(controllino.CmdLogSignal('A0', 1000))

        with base._serial_lock:
            base._serial.put(controllino._encode(
                {'command': 'RX_LOG_SIGNAL', 'pin': 'A0', 'job': 1, 'time': 0.0, 'value': 1.0, 'done': False}))

        done = request.wait(WAIT)
        base.process_errors()
        request.result()  # Check for errors!
        assert not recording.wait(WAIT)

        with base._serial_lock:
            base._serial.put(controllino._encode(
                {'command': 'RX_LOG_SIGNAL', 'pin': 'A0', 'job': 1, 'time': 1.0, 'value': -0.5, 'done': False}))
            base._serial.put(controllino._encode(
                {'command': 'RX_LOG_SIGNAL', 'pin': 'A0', 'job': 1, 'time': 2.0, 'value': -2.0, 'done': False}))

        assert not recording.wait(WAIT)

        with base._serial_lock:
            base._serial.put(controllino._encode(
                {'command': 'RX_LOG_SIGNAL', 'pin': 'A0', 'job': 1, 'time': 3.0, 'value': -3.5, 'done': True}))

        done = recording.wait(WAIT)
        base.process_errors()
        assert done
        result = recording.result()
        assert result.time == [0.0, 1.0, 2.0, 3.0]
        assert result.values == [1.0, -0.5, -2.0, -3.5]

    def test_end_log_signal(self, base):
        future = base.submit(controllino.CmdEndLogSignal('A0'))
        with base._serial_lock:
            base._serial.put(controllino._encode(
                {'command': 'RX_END_LOG_SIGNAL', 'pin': 'A0', 'job': 1}))
        done = future.wait(WAIT)
        base.process_errors()
        assert done

    def test_multiple_jobs(self, base):
        future1 = base.submit(controllino.CmdGetSignal('A1'))
        future2 = base.submit(controllino.CmdGetSignal('A2'))
        assert not future1.wait(WAIT)
        assert not future2.wait(WAIT)

        with base._serial_lock:
            value1 = 123
            value2 = 456
            cmd = {'command': 'RX_GET_INPUT',
                   'pin': 'A2', 'level': value2, 'job': 2}
            base._serial.put(controllino._encode(cmd))
            cmd = {'command': 'RX_GET_INPUT',
                   'pin': 'A1', 'level': value1, 'job': 1}
            base._serial.put(controllino._encode(cmd))

        done1 = future1.wait(WAIT)
        done2 = future2.wait(WAIT)
        base.process_errors()
        assert done1
        assert done2
        assert future1.result() == value1
        assert future2.result() == value2

    def test_error_correction(self, base):
        future = base.submit(controllino.CmdGetSignal('A2'))
        assert not future.wait(WAIT)

        with base._serial_lock:
            value = -0.12
            cmd = {'command': 'RX_GET_INPUT',
                   'pin': 'A2', 'level': value, 'job': 1}
            flawed_msg = b'_' + controllino._encode(cmd)
            base._serial.put(flawed_msg)

        assert future.wait(WAIT)
        base.process_errors()
        assert future.result() == value

    def test_debug(self, base, capsys):
        with base._serial_lock:
            cmd = {'command': 'DEBUG', 'info': 'foo'}
            base._serial.put(controllino._encode(cmd))

        time.sleep(WAIT)
        base.process_errors()
        captured = capsys.readouterr()
        assert captured.out == 'foo\n'
