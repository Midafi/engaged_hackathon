import numpy as np
from scipy.io import wavfile
import frequency
import features
from scipy.ndimage import measurements


class TimeSeries(object):
    """
    Base class for TimeSeries data eg audio wave or spectrogram
    Time is always along series axis=0
    """
    def __init__(self, series=None, sample_rate=None):
        if series is not None:
            self.series = series
            self.sample_rate = sample_rate

    def snippet(self, start_time=None, end_time=None):
        """
        Returns a wave object of audio extracted between the timestamps
        start_time and end_time can be none, which will extract all the way to
        the start or end of the file respectively
        """
        start_point = self.time_to_position(start_time)
        end_point = self.time_to_position(end_time)

        wav_snippet = self.series[start_point:end_point]

        return self.__class__(wav_snippet, self.sample_rate)
        # self.series[start_point:end_point]
        #

    def time_to_position(self, time):
        """
        Converts a time to a position in the audio signal
        """
        if time is None:
            return None
        else:
            return int(float(time) / self.sample_rate)

    def get_length(self):
        return self.series.shape[0] / self.sample_rate


class Wave(TimeSeries):
    """
    An audio wave snippet.
    Functionality for extracing segments by time etc
    """
    def load_from_wav(self, wav_path):
        """
        Loads audio waveform from a .wav file
        """
        self.sample_rate, self.series = wavfile.read(wav_path)

    def play(self):
        pass


class Spectrogram(TimeSeries):
    """
    Spectrogram for an audio snippet
    """
    # def __init__(self, wave_in=None, **options):

    #     if wave_in is not None:
    #         self.from_wave(wave_in, **options)

    def from_wave(self, wave_in, **options):
        """
        Generates spectrogram from an audio wave file
        NOTE that the spectrogram is stored with the time along axis=0
        Should transpose to plot
        """
        self.nfft = options['nfft']
        self.window_width = options['window_width']
        self.overlap = options['overlap']

        self.series = frequency.spectrogram(wave_in.series, wave_in.sample_rate, **options).T
        self.sample_rate = options['window_width']

        if hasattr(wave_in, 'annotations'):
            self.annotations = wave_in.annotations


class LabelledTimeseries(TimeSeries):
    """
    TimeSeries clip which has labels attached to it. Should have methods to extract
    all the regions with a certain label etc
    """
    def set_annotations(self, annotations):
        self.annotations = annotations
        self.labelset = set(
            [annotation['Label'] for annotation in annotations])

    def snippets_with_labels(self, include_labels=None):
        """
        Returns list of all audio snippets with the specified label(s)
        include_labels and exclude_labels should be lists of strings or just a string
        include_label: If none, returns all snippets
        """
        # convert the labels to a list if they are just a string
        if include_labels is None:
            include_labels = self.labelset
        elif isinstance(include_labels, basestring):
            include_labels = [include_labels]

        # loop over each annotation and build the list of snippets
        snippets = []
        for annotation in self.annotations:
            if annotation['Label'] in include_labels:

                snippet = self.snippet(
                    annotation['LabelStartTime_Seconds'],
                    annotation['LabelEndTime_Seconds']
                    )
                snippets.append(snippet)

        return snippets

    def snippets_except_labels(self, exclude_labels=None):
        """
        Returns list of snippets which have labels not in the 'exclude_labels'
        list
        TODO - perhaps this should instead return the entire part?
        if exclude_labels is None, then return *all* unlabelled sections
        """

        if isinstance(exclude_labels, basestring):
            exclude_labels = [exclude_labels]

        # create vector which is one whenever one of the exclude labels occurs
        is_label = np.zeros(self.series.shape[0])

        for annotation in self.annotations:
            if annotation['Label'] in exclude_labels:
                start_point = self.time_to_position(annotation['LabelStartTime_Seconds'])
                end_point = self.time_to_position(annotation['LabelEndTime_Seconds'])
                is_label[start_point:end_point] += 1

        # now extract the snippets from which there are no labels
        labs, nlabels = measurements.label(is_label==0)

        snippets = []
        for lab in range(1, nlabels+1):
            snippet = Wave(self.series[labs==lab], self.sample_rate)
            snippets.append(snippet)

        return snippets


class LabelledWave(Wave, LabelledTimeseries):
    pass


class LabelledSpectrogram(Spectrogram, LabelledTimeseries):
    pass