import datetime
import logging
from terminal_color import Color
from sources.flux_calibrator import FluxCalibrator
from sources.bandpass_calibrator import BandpassCalibrator
from sources.phase_calibrator import PhaseCalibrator
from sources.target_source import TargetSource
from sources.continuum_source import ContinuumSource
from sources.line_source import LineSource


class PipelineStage(object):
    def __init__(self, measurement_set):
        self.measurement_set = measurement_set

    def _log_timing(stage_func):
        def stage_func_wrapper(*args):
            start_time = datetime.datetime.now()
            stage_func(*args)
            end_time = datetime.datetime.now()
            logging.info(Color.LightCyan + Color.UNDERLINE + 'Time spent in ' + stage_func.__name__ + '= ' + str(
                abs((end_time - start_time).seconds)) + " seconds" + Color.ENDC)

        return stage_func_wrapper

    @_log_timing
    def flux_calibration(self):
        logging.info(Color.SOURCE_HEADING + "Flux Calibration" + Color.ENDC)
        flux_calibrator = FluxCalibrator(self.measurement_set)
        flux_calibrator.run_setjy()
        flux_calibrator.reduce_data()

    @_log_timing
    def bandpass_calibration(self):
        logging.info(Color.SOURCE_HEADING + "Bandpass Calibration" + Color.ENDC)
        bandpass_calibrator = BandpassCalibrator(self.measurement_set)
        bandpass_calibrator.calibrate()
        bandpass_calibrator.run_tfcrop()
        bandpass_calibrator.run_rflag()
        bandpass_calibrator.calibrate()

    @_log_timing
    def phase_calibration(self):
        logging.info(Color.SOURCE_HEADING + "Phase Calibration" + Color.ENDC)
        phase_calibrator = PhaseCalibrator(self.measurement_set)
        phase_calibrator.calibrate()
        phase_calibrator.reduce_data()

    @_log_timing
    def target_source(self, target_source_exec_steps):
        logging.info(Color.SOURCE_HEADING + "Target Source Calibration" + Color.ENDC)
        target_source = TargetSource(self.measurement_set)
        target_source.calibrate()
        line_source = LineSource(target_source.line())
        if target_source_exec_steps['run_auto_flagging']:
            line_source.run_tfcrop()
            line_source.run_rflag()
        if target_source_exec_steps['create_continuum']:
            continuum_source = ContinuumSource(line_source.continuum())
            continuum_source.reduce_data()
            continuum_source.self_calibrate()
            line_source.reduce_data()
        if target_source_exec_steps['create_line_image']:
            line_source.apply_calibration()
            line_source.create_line_image()
