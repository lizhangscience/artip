import logging
from models.baseline import Baseline
from helpers import *
import numpy
from terminal_color import Color


class AmplitudeMatrix:
    def __init__(self, measurement_set, polarization, scan_id, config, matrix={}):
        self._measurement_set = measurement_set
        self._polarization = polarization
        self._scan_id = scan_id
        self._config = config
        self.amplitude_data_matrix = self._generate_matrix() if measurement_set else matrix

    def _generate_matrix(self):
        antennaids = self._measurement_set.antenna_ids(self._polarization, self._scan_id)
        amplitude_data_column = self._config['detail_flagging']['amplitude_data_column']
        amplitude_data_matrix = {}
        data = self._measurement_set.get_data({'start': self._config['channel'], 'width': self._config['width']},
                                              self._polarization,
                                              {'scan_number': self._scan_id},
                                              ["antenna1", "antenna2", amplitude_data_column, 'flag'])
        amplitudes = data[amplitude_data_column][0][0]
        antenna2_list = data['antenna2']
        antenna1_list = data['antenna1']
        flags = data['flag'][0][0]

        # TODO remove duplicate baselines
        for antenna1 in antennaids:
            for antenna2 in antennaids:
                if antenna1 < antenna2:
                    primary_antenna = antenna1
                    secondary_antenna = antenna2
                else:
                    primary_antenna = antenna2
                    secondary_antenna = antenna1

                if primary_antenna == secondary_antenna: continue

                baseline_indexes = numpy.logical_and(antenna1_list == primary_antenna,
                                                     antenna2_list == secondary_antenna).nonzero()[0]
                amplitude_data = numpy.array([])
                for index in baseline_indexes:
                    if flags[index]:
                        amplitude_data = numpy.append(amplitude_data, numpy.nan)
                    else:
                        amplitude_data = numpy.append(amplitude_data, amplitudes[index])

                baseline = Baseline(primary_antenna, secondary_antenna)
                amplitude_data_matrix[baseline] = amplitude_data
        return amplitude_data_matrix

    def filter_by_antenna(self, antenna_id):
        antenna_matrix = dict((baseline, amp_data) for baseline, amp_data in self.amplitude_data_matrix.iteritems() if
                              baseline.contains(antenna_id))

        return AmplitudeMatrix(None, None, None, self._config, antenna_matrix)

    def filter_by_baseline(self, baseline):
        return AmplitudeMatrix(None, None, None, self._config,
                               {baseline: self.amplitude_data_matrix[baseline]})

    def readings_count(self):
        return len(self.amplitude_data_matrix[list(self.amplitude_data_matrix)[0]])

    def is_nan(self):
        return all(numpy.isnan(amp) for amp in numpy.array(self.amplitude_data_matrix.values()).flatten())

    def median(self):
        if self.is_nan(): return numpy.nan
        return numpy.nanmedian(self.amplitude_data_matrix.values())

    def mad(self):
        if self.is_nan(): return numpy.nan
        matrix = self.amplitude_data_matrix.values()
        return numpy.nanmedian(abs(numpy.array(matrix) - numpy.nanmedian(matrix)))

    def mad_sigma(self):
        return 1.4826 * self.mad()

    def mean(self):
        if self.is_nan(): return numpy.nan
        return numpy.nanmean(self.amplitude_data_matrix.values())

    def mean_sigma(self):
        if self.is_nan(): return numpy.nan
        return numpy.nanstd(self.amplitude_data_matrix.values())

    def is_empty(self):
        return len(numpy.array(self.amplitude_data_matrix.values()).flatten()) == 0

    def is_bad(self, global_median, global_sigma):
        matrix_median = self.median()
        matrix_sigma = self.mad_sigma()
        if numpy.isnan(matrix_median) or numpy.isnan(matrix_sigma): return False

        deviated_median = self._deviated_median(global_median, global_sigma, matrix_median)
        scattered_amplitude = self._scattered_amplitude(global_sigma, matrix_sigma)
        if deviated_median or scattered_amplitude:
            logging.debug(Color.UNDERLINE + "matrix=" + str(self.amplitude_data_matrix) + Color.ENDC)
            logging.debug(Color.UNDERLINE + " median=" + str(matrix_median) + ", median sigma=" + str(matrix_sigma)
                          + ", mean=" + str(self.mean()) + ", mean sigma=" + str(self.mean_sigma()) + Color.ENDC)
            logging.debug(Color.WARNING + "median deviated=" + str(deviated_median) + ", amplitude scattered=" + str(
                    scattered_amplitude) + Color.ENDC)
        return deviated_median or scattered_amplitude

    def _deviated_median(self, global_median, global_sigma, actual_median):
        return abs(actual_median - global_median) > (self._config['detail_flagging']['mad_scale_factor'] * global_sigma)

    def _scattered_amplitude(self, global_sigma, actual_sigma):
        return actual_sigma > (self._config['detail_flagging']['mad_scale_factor'] * global_sigma)

    def __repr__(self):
        return "AmpMatrix=" + str(self.amplitude_data_matrix) + " med=" + \
               str(self.median()) + " mad sigma=" + str(self.mad_sigma())
