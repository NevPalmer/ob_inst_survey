@call mamba activate working

@REM python c:/scripts/ob_inst_survey/log_nmea_to_file.py ^
@REM --ipaddr 192.168.1.107 ^
@REM --ipport 50000 ^
@REM --ipprot TCP ^
@REM --outfilepath ../logs/nmea/ ^
@REM --outfileprefix NMEA

python c:/scripts/ob_inst_survey/log_nmea_to_file.py ^
--ipaddr 0.0.0.0 ^
--ipport 7150 ^
--ipprot UDP ^
--outfilepath C:/logs/nmea/ ^
--outfileprefix NMEA ^
--filesplit 24
@REM --ipaddr 138.71.128.182 ^
@REM --ipaddr 138.71.128.106 ^
@REM --ipport 6044 ^

@call mamba deactivate
