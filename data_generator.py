import numpy as np
from tensorflow.python.platform import flags


class SinusoidDataGenerator(object):
    """
    Data Generator capable of generating batches of sinusoid data.
    A "class" is considered a class of omniglot digits or a particular sinusoid function.
    """
    def __init__(self, num_samples_per_class, batch_size):
        """
        Args:
            num_samples_per_class: num samples to generate per class in one batch
            batch_size: size of meta batch size (e.g. number of functions)
        """
        self.batch_size = batch_size
        self.num_samples_per_class = num_samples_per_class
        self.num_classes = 1  # by default 1 (only relevant for classification problems)

        # self.generate = self.generate_sinusoid_batch
        self.amp_range = [0.1, 5.0]
        self.phase_range = [0, np.pi]
        self.input_range = [-5.0, 5.0]
        self.dim_input = 1
        self.dim_output = 1

    def generate(self, input_idx: int=None, is_training: bool=False):
        # input_idx is used during qualitative testing the number of examples
        # used for the grad update
        amp = np.random.uniform(self.amp_range[0], self.amp_range[1], [self.batch_size])
        phase = np.random.uniform(self.phase_range[0], self.phase_range[1], [self.batch_size])
        outputs = np.zeros([self.batch_size, self.num_samples_per_class, self.dim_output])
        init_inputs = np.zeros([self.batch_size, self.num_samples_per_class, self.dim_input])

        for func in range(self.batch_size):
            init_inputs[func] = np.random.uniform(
                self.input_range[0], self.input_range[1], [self.num_samples_per_class, 1])

            if input_idx is not None:
                init_inputs[:, input_idx:, 0] = np.linspace(self.input_range[0], self.input_range[1], num=self.num_samples_per_class-input_idx, retstep=False)

            outputs[func] = amp[func] * np.sin(init_inputs[func]-phase[func])

        return init_inputs, outputs, amp, phase
