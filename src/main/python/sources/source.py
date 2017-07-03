import itertools
from logger import logger
from analysers.angular_dispersion import AngularDispersion
from analysers.closure_analyser import ClosureAnalyser
from analysers.detailed_analyser import DetailedAnalyser
from casa.flag_reasons import BAD_ANTENNA, BAD_ANTENNA_TIME, BAD_BASELINE_TIME, BAD_TIME
from configs import config, pipeline_config
from terminal_color import Color
from report import Report


class Source(object):
    def __init__(self, measurement_set):
        self.measurement_set = measurement_set

    def run_rflag(self):
        self.measurement_set.casa_runner.r_flag(self.source_type)

    def run_tfcrop(self):
        self.measurement_set.casa_runner.tfcrop(self.source_type)

    def calibrate(self):
        raise NotImplementedError("Not implemented")

    def reduce_data(self):
        self.flag_antennas()
        self.calibrate()
        self.flag_and_calibrate_in_detail()

    def flag_antennas(self):
        self.analyse_antennas_on_angular_dispersion()
        self.analyse_antennas_on_closure_phases()

        scan_ids = self.measurement_set.scan_ids_for(self.source_ids)
        Report(self.measurement_set.antennas()).generate_report(scan_ids)

        self.measurement_set.flag_bad_antennas(self.source_ids)
        self.extend_flags()
        self.measurement_set.casa_runner.flagdata(BAD_ANTENNA)

    def flag_and_calibrate_in_detail(self):
        logger.info(Color.HEADER + "Started Detail Flagging..." + Color.ENDC)
        detailed_analyser = DetailedAnalyser(self.measurement_set, self.config)
        self._flag_bad_time(BAD_TIME, detailed_analyser.analyse_time, True)
        self._flag_bad_time(BAD_ANTENNA_TIME, detailed_analyser.analyse_antennas, False)
        self._flag_bad_time(BAD_BASELINE_TIME, detailed_analyser.analyse_baselines, False)

    def _flag_bad_time(self, reason, analyser, run_only_once):
        polarizations = config.GLOBAL_CONFIG['polarizations']
        spw = config.GLOBAL_CONFIG['default_spw']
        scan_ids = self.measurement_set.scan_ids_for(self.source_ids)
        spw_polarization_scan_product = list(itertools.product(spw, polarizations, scan_ids))

        if run_only_once:
            self.analyse_and_flag_once(reason, analyser, spw_polarization_scan_product)
        else:
            self.analyse_and_flag_until_bad(reason, analyser, spw_polarization_scan_product)

    def analyse_and_flag_until_bad(self, reason, analyser, spw_polarization_scan_product):
        while True:
            bad_time_present = analyser(spw_polarization_scan_product)
            if bad_time_present:
                logger.info(Color.HEADER + 'Flagging {0} in CASA'.format(reason) + Color.ENDC)
                self.measurement_set.casa_runner.flagdata(reason)
                self.calibrate()
            else:
                logger.info(Color.OKGREEN + 'No {0} Found'.format(reason) + Color.ENDC)
                break

    def analyse_and_flag_once(self, reason, analyser, spw_polarization_scan_product):
        bad_time_present = analyser(spw_polarization_scan_product)
        if bad_time_present:
            logger.info(Color.HEADER + 'Flagging {0} in CASA'.format(reason) + Color.ENDC)
            self.measurement_set.casa_runner.flagdata(reason)
            self.calibrate()
        else:
            logger.info(Color.OKGREEN + 'No {0} Found'.format(reason) + Color.ENDC)

    def analyse_antennas_on_closure_phases(self):
        logger.info(Color.HEADER + "Identifying bad Antennas based on closure phases..." + Color.ENDC)
        closure_analyser = ClosureAnalyser(self.measurement_set, self.source_type)
        closure_analyser.identify_antennas_status()

    def analyse_antennas_on_angular_dispersion(self):
        logger.info(
            Color.HEADER + "Identifying bad Antennas based on angular dispersion in phases..." + Color.ENDC)
        r_analyser = AngularDispersion(self.measurement_set, self.source_type)
        r_analyser.identify_antennas_status()
