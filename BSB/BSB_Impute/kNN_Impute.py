import gzip
import io
import random
import numpy as np
from BSB.BSB_Impute.Imputation.GenomeImputation import GenomeImputation
from BSB.BSB_Utils.MatrixIterator import OpenMatrix


class ImputeMissingValues:
    """

            :param batch_size:
            :param imputation_window_size:
            :param k:
            :param threads:
            :param verbose:
            :param sep:
            :param output_path:
    """

    def __init__(self, input_matrix_file=None, batch_size=None, imputation_window_size=3000000, k=5,
                 threads=4, verbose=False, sep='\t', output_path=None, randomize_batch=False,
                 meth_matrix=None, meth_site_order=None, sample_ids=None):
        self.input_matrix_file = input_matrix_file
        self.meth_matrix = meth_matrix
        self.meth_site_order = meth_site_order
        self.sample_ids = sample_ids
        self.batch_commands = [0, False]
        if batch_size:
            self.batch_commands = [batch_size, randomize_batch]
        self.output_matrix = None
        if output_path:
            self.output_matrix = self.get_output_matrix(output_path)
        self.tqdm_disable = False if verbose else True
        self.sep = sep
        self.imputation_kwargs = dict(imputation_window_size=imputation_window_size,
                                      k=k,
                                      threads=threads,
                                      verbose=verbose)

    def impute_values(self):
        imputation_order = [count for count in range(len(self.sample_ids[1]))]
        if self.batch_commands[1]:
            random.shuffle(imputation_order)
        if not self.batch_commands[0]:
            self.batch_commands[0] = len(self.sample_ids[1])
        imputation_batches = self.process_batch(imputation_order)
        for batch in imputation_batches:
            batch_array, sample_labels = self.get_batch_data(batch)
            batch_impute = self.launch_genome_imputation(batch_array, sample_labels)
            print(self.meth_matrix[:, batch])
            print(batch_impute.genomic_array)

    def process_batch(self, imputation_order):
        batches = []
        if not self.batch_commands[0]:
            self.batch_commands[0] = len(self.sample_ids)
        batch_number = int(len(imputation_order) / self.batch_commands[0])
        batch_remainder = len(imputation_order) % self.batch_commands[0]
        if float(batch_remainder) / float(self.batch_commands[0]) <= .6 and batch_remainder != 0:
            batch_addition = int(batch_remainder / batch_number)
            self.batch_commands[0] += batch_addition + 1
            print(f'Adjusting batch size, new batch size = {self.batch_commands[0]}')
        start, end = 0, self.batch_commands[0]
        while True:
            batch_order = imputation_order[start: end]
            if not batch_order:
                break
            batches.append(batch_order)
            start += self.batch_commands[0]
            end += self.batch_commands[0]
        return batches

    def get_batch_data(self, batch):
        batch_array = self.meth_matrix[:, batch]
        sample_labels = [self.sample_ids[1][sample] for sample in batch]
        return batch_array, sample_labels

    def import_matrix(self):
        sample_ids, site_order, site_values = None, [], []
        for line_label, line_values in OpenMatrix(self.input_matrix_file):
            if not sample_ids:
                sample_ids = line_label, line_values
            else:
                site_order.append(line_label)
                site_values.append(line_values)
        self.meth_matrix = np.asarray(site_values)
        self.meth_site_order = site_order
        self.sample_ids = sample_ids

    @staticmethod
    def get_output_matrix(output_path):
        if output_path.endswith('.gz'):
            out = io.BufferedWriter(gzip.open(output_path, 'wb'))
        else:
            out = open(output_path, 'r')
        return out

    def launch_genome_imputation(self, meth_array, sample_labels):
        imputation_kwargs = dict(self.imputation_kwargs)
        imputation_kwargs.update(dict(genomic_array=meth_array,
                                      sample_labels=sample_labels,
                                      row_labels=self.meth_site_order))
        knn_imputation: GenomeImputation = GenomeImputation(**imputation_kwargs)
        knn_imputation.impute_windows()
        return knn_imputation
