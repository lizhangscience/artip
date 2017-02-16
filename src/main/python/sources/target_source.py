from configs.config import ALL_CONFIGS, GLOBAL_CONFIG, OUTPUT_PATH
from helpers import is_last_element, create_dir
from sources.source import Source

from measurement_set import MeasurementSet


class TargetSource(Source):
    def __init__(self, measurement_set):
        self.source_type = 'target_source'
        self.config = ALL_CONFIGS[self.source_type]
        self.source_id = GLOBAL_CONFIG['target_src_field']
        super(TargetSource, self).__init__(measurement_set)

    def calibrate(self):
        flux_cal_field = GLOBAL_CONFIG['flux_cal_field']
        phase_cal_field = GLOBAL_CONFIG['phase_cal_field']
        self.measurement_set.casa_runner.apply_target_source_calibration(flux_cal_field, phase_cal_field, self.config)

    def line(self):
        line_ms_path, line_output_path = self.prepare_output_dir("line")
        self.measurement_set.split(line_ms_path, {'datacolumn': 'corrected', 'field': self.source_id})
        return MeasurementSet(line_ms_path, line_output_path)

    def continuum(self):
        continuum_ms_path, continuum_output_path = self.prepare_output_dir("continuum")
        spw = "{0}:{1}".format(self.config['spw'], self.config['continuum']['channels_to_avg'])
        width = self.config['continuum']['width']
        self.measurement_set.split(continuum_ms_path,
                                   {'datacolumn': 'data', 'spw': spw, 'width': width,
                                    'field': self.source_id})
        return MeasurementSet(continuum_ms_path, continuum_output_path)

    def prepare_output_dir(self, new_dir):
        output_path = self.measurement_set.get_output_path() + "/" + new_dir
        create_dir(output_path)
        ms_path = output_path + "/{0}.ms".format(new_dir)
        return ms_path, output_path
