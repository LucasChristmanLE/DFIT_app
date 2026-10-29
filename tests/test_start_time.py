"""TestData.start_time: the wall clock at t_s = 0, used to suggest the job date."""

import datetime as dt
import os
import struct
import time

from dfit_tool import io_load
from tests.test_dbs import write_dbs


def test_csv_start_time_is_first_timestamp(tmp_path):
    p = tmp_path / "dt.csv"
    p.write_text(
        "DateTime,Pressure (psi)\n"
        "2019-05-04 23:59:58,5000.0\n"
        "2019-05-04 23:59:59,4995.0\n"
        "2019-05-05 00:00:00,4990.0\n"
    )
    td = io_load.load_csv(str(p))
    assert td.start_time == dt.datetime(2019, 5, 4, 23, 59, 58)


def test_csv_elapsed_fallback_has_no_start_time(tmp_path):
    p = tmp_path / "elapsed_only.csv"
    p.write_text(
        "Elapsed (min),Pressure (psi)\n"
        "0.00000,5000.0\n"
        "0.01667,4995.0\n"
        "0.03334,4990.0\n"
    )
    td = io_load.load_csv(str(p))
    assert td.start_time is None


def _dbs_with_start(tmp_path, unix_s):
    path = tmp_path / "start.dbs"
    write_dbs(path, [("P", "PRES")], [(0, 1.0), (1, 2.0)], interval_min=1.0)
    data = bytearray(path.read_bytes())
    struct.pack_into("<I", data, 4, unix_s)
    path.write_bytes(bytes(data))
    return path


def test_dbs_start_time_from_header(tmp_path):
    unix_s = 1557010800  # 2019-05-04 23:00 UTC
    td = io_load.load_dbs(str(_dbs_with_start(tmp_path, unix_s)))
    assert td.start_time == dt.datetime.fromtimestamp(unix_s)


def test_dbs_start_after_file_mtime_is_rejected(tmp_path):
    # A clock a year off, or a start later than the file was written, is not a data start.
    td = io_load.load_dbs(str(_dbs_with_start(tmp_path, int(time.time()) + 10 * 86400)))
    assert td.start_time is None


def test_dbs_2038_sentinel_is_rejected(tmp_path):
    td = io_load.load_dbs(str(_dbs_with_start(tmp_path, 0x7FFFFFFF)))
    assert td.start_time is None


def test_dbs_pre_1990_start_is_rejected(tmp_path):
    path = _dbs_with_start(tmp_path, 0)
    os.utime(path, (1557010800, 1557010800))
    td = io_load.load_dbs(str(path))
    assert td.start_time is None
