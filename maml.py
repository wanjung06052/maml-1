from __future__ import print_function
# import numpy as np
# import sys
import tensorflow as tf

# try:
    # import special_grads
# except KeyError as e:
    # print('WARN: Cannot define MaxPoolGrad, likely already defined for this version of tensorflow: %s' % e,
          # file=sys.stderr)

from utils import mse, xent, conv_block, normalize  # FIXME


class MAML(object):
    def __init__(
        self,
        dim_input: int=1,
        dim_output: int=1,
        num_updates: int=1,
        update_lr: float=1e-3,
        meta_lr: float=1e-3,
        test_num_updates: int=5,
        stop_grad: bool=False,
        meta_batch_size: int=25,
        metatrain_iterations: int=15000,
        norm: str="batch_norm",
    ):
        self.dim_input = dim_input
        self.dim_output = dim_output
        self.num_updates = num_updates
        self.update_lr = update_lr
        self.meta_lr = tf.placeholder_with_default(meta_lr, ())
        # self.classification = False
        self.test_num_updates = test_num_updates
        self.stop_grad = stop_grad
        self.meta_batch_size = meta_batch_size
        self.metatrain_iterations = metatrain_iterations
        self.norm = norm

        # if FLAGS.datasource == 'sinusoid':
        self.dim_hidden = [40, 40]
        self.loss_func = mse
        self.forward = self.forward_fc
        self.construct_weights = self.construct_fc_weights
        # elif FLAGS.datasource == 'omniglot' or FLAGS.datasource == 'miniimagenet':
            # self.loss_func = xent
            # self.classification = True
            # if FLAGS.conv:
                # self.dim_hidden = FLAGS.num_filters
                # self.forward = self.forward_conv
                # self.construct_weights = self.construct_conv_weights
            # else:
                # self.dim_hidden = [256, 128, 64, 64]
                # self.forward=self.forward_fc
                # self.construct_weights = self.construct_fc_weights
            # if FLAGS.datasource == 'miniimagenet':
                # self.channels = 3
            # else:
                # self.channels = 1
            # self.img_size = int(np.sqrt(self.dim_input/self.channels))
        # else:
            # raise ValueError('Unrecognized data source.')

    def construct_model(self, input_tensors=None, prefix='metatrain_'):
        # a: training data for inner gradient
        # b: test data for meta gradient
        if input_tensors is None:
            self.inputa = tf.placeholder(tf.float32)  # FIXME rename
            self.inputb = tf.placeholder(tf.float32)
            self.labela = tf.placeholder(tf.float32)
            self.labelb = tf.placeholder(tf.float32)
        # else:
            # self.inputa = input_tensors['inputa']
            # self.inputb = input_tensors['inputb']
            # self.labela = input_tensors['labela']
            # self.labelb = input_tensors['labelb']

        with tf.variable_scope('model', reuse=None) as training_scope:
            # if 'weights' in dir(self):  # TODO correct?
                # training_scope.reuse_variables()
                # weights = self.weights
            # else:
                # Define the weights
            self.weights = weights = self.construct_weights()

            # outputbs[i] and lossesb[i] is the output and loss after i+1 gradient updates
            losses_a = []
            outputs_a = []
            losses_b = []
            outputs_b = []
            # accuracies_a = []
            # accuracies_b = []
            num_updates = max(self.test_num_updates, self.num_updates)
            outputs_b = [[]]*num_updates
            losses_b = [[]]*num_updates
            # accuraciesb = [[]]*num_updates

            def task_metalearn(inp, reuse=True):
                """ Perform gradient descent for one task in the meta-batch. """
                inputa, inputb, labela, labelb = inp
                task_outputs_b = []
                task_losses_b = []

                # if self.classification:
                    # task_accuraciesb = []

                # only reuse on the first iter
                task_output_a = self.forward(inputa, weights, reuse=reuse)
                task_loss_a = self.loss_func(task_output_a, labela)

                grads = tf.gradients(task_loss_a, list(weights.values()))
                if self.stop_grad:
                    grads = [tf.stop_gradient(grad) for grad in grads]
                gradients = dict(zip(weights.keys(), grads))
                fast_weights = dict(zip(weights.keys(), [weights[key] - self.update_lr*gradients[key] for key in weights.keys()]))
                output = self.forward(inputb, fast_weights, reuse=True)
                task_outputs_b.append(output)
                task_losses_b.append(self.loss_func(output, labelb))

                for j in range(num_updates - 1):
                    loss = self.loss_func(self.forward(inputa, fast_weights, reuse=True), labela)
                    grads = tf.gradients(loss, list(fast_weights.values()))
                    if self.stop_grad:
                        grads = [tf.stop_gradient(grad) for grad in grads]
                    gradients = dict(zip(fast_weights.keys(), grads))
                    fast_weights = dict(zip(fast_weights.keys(), [fast_weights[key] - self.update_lr*gradients[key] for key in fast_weights.keys()]))
                    output = self.forward(inputb, fast_weights, reuse=True)
                    task_outputs_b.append(output)
                    task_losses_b.append(self.loss_func(output, labelb))

                task_output = [task_output_a, task_outputs_b, task_loss_a, task_losses_b]

                # if self.classification:
                    # task_accuracya = tf.contrib.metrics.accuracy(tf.argmax(tf.nn.softmax(task_output_a), 1), tf.argmax(labela, 1))
                    # for j in range(num_updates):
                        # task_accuraciesb.append(tf.contrib.metrics.accuracy(tf.argmax(tf.nn.softmax(task_outputs_b[j]), 1), tf.argmax(labelb, 1)))
                    # task_output.extend([task_accuracy_a, task_accuracies_b])

                return task_output

            if self.norm is not 'None':
                # to initialize the batch norm vars, might want to combine this, and not run idx 0 twice.
                unused = task_metalearn((self.inputa[0], self.inputb[0], self.labela[0], self.labelb[0]), False)

            out_dtype = [tf.float32, [tf.float32]*num_updates, tf.float32, [tf.float32]*num_updates]
            # if self.classification:
                # out_dtype.extend([tf.float32, [tf.float32]*num_updates])

            result = tf.map_fn(
                task_metalearn,
                elems=(self.inputa, self.inputb, self.labela, self.labelb),
                dtype=out_dtype,
                parallel_iterations=self.meta_batch_size
            )

            # if self.classification:
                # outputs_a, outputs_b, lossesa, lossesb, accuraciesa, accuraciesb = result
            # else:
            outputs_a, outputs_b, losses_a, losses_b = result

        ## Performance & Optimization
        if 'train' in prefix:
            self.total_loss1 = total_loss1 = tf.reduce_sum(losses_a) / tf.to_float(self.meta_batch_size)
            self.total_losses2 = total_losses2 = [tf.reduce_sum(losses_b[j]) / tf.to_float(self.meta_batch_size) for j in range(num_updates)]
            # after the map_fn
            self.outputs_a, self.outputs_b = outputs_a, outputs_b
            # if self.classification:
                # self.total_accuracy1 = total_accuracy1 = tf.reduce_sum(accuracies_a) / tf.to_float(self.meta_batch_size)
                # self.total_accuracies2 = total_accuracies2 = [tf.reduce_sum(accuracies_b[j]) / tf.to_float(self.meta_batch_size) for j in range(num_updates)]
            self.pretrain_op = tf.train.AdamOptimizer(self.meta_lr).minimize(total_loss1)

            if self.metatrain_iterations > 0:
                optimizer = tf.train.AdamOptimizer(self.meta_lr)
                self.gvs = gvs = optimizer.compute_gradients(self.total_losses2[self.num_updates-1])
                # if FLAGS.datasource == 'miniimagenet':
                    # gvs = [(tf.clip_by_value(grad, -10, 10), var) for grad, var in gvs]
                self.metatrain_op = optimizer.apply_gradients(gvs)
        else:  # metaval_
            self.metaval_total_loss1 = total_loss1 = tf.reduce_sum(losses_a) / tf.to_float(self.meta_batch_size)
            self.metaval_total_losses2 = total_losses2 = [tf.reduce_sum(losses_b[j]) / tf.to_float(self.meta_batch_size) for j in range(num_updates)]
            # if self.classification:
                # self.metaval_total_accuracy1 = total_accuracy1 = tf.reduce_sum(accuraciesa) / tf.to_float(self.meta_batch_size)
                # self.metaval_total_accuracies2 = total_accuracies2 =[tf.reduce_sum(accuraciesb[j]) / tf.to_float(self.meta_batch_size) for j in range(num_updates)]

        # Summaries
        tf.summary.scalar(prefix+'Pre-update loss', total_loss1)

        # if self.classification:
            # tf.summary.scalar(prefix+'Pre-update accuracy', total_accuracy1)

        for j in range(num_updates):
            tf.summary.scalar(prefix+'Post-update loss, step ' + str(j+1), total_losses2[j])
            # if self.classification:
                # tf.summary.scalar(prefix+'Post-update accuracy, step ' + str(j+1), total_accuracies2[j])

    # Network construction functions (fc networks and conv networks)
    def construct_fc_weights(self):
        weights = {}
        weights['w1'] = tf.Variable(tf.truncated_normal([self.dim_input, self.dim_hidden[0]], stddev=0.01))
        weights['b1'] = tf.Variable(tf.zeros([self.dim_hidden[0]]))

        for i in range(1, len(self.dim_hidden)):  # FIXME
            weights['w'+str(i+1)] = tf.Variable(tf.truncated_normal([self.dim_hidden[i-1], self.dim_hidden[i]],
                                                                    stddev=0.01))
            weights['b'+str(i+1)] = tf.Variable(tf.zeros([self.dim_hidden[i]]))

        weights['w'+str(len(self.dim_hidden)+1)] = tf.Variable(tf.truncated_normal([self.dim_hidden[-1], self.dim_output], stddev=0.01))
        weights['b'+str(len(self.dim_hidden)+1)] = tf.Variable(tf.zeros([self.dim_output]))

        return weights

    def forward_fc(self, inp, weights, reuse: bool=False):
        hidden = normalize(tf.matmul(inp, weights['w1']) + weights['b1'], activation=tf.nn.relu, reuse=reuse, scope='0')

        for i in range(1, len(self.dim_hidden)):  # FIXME
            hidden = normalize(tf.matmul(hidden, weights['w'+str(i+1)]) + weights['b'+str(i+1)], activation=tf.nn.relu, reuse=reuse, scope=str(i+1))

        return tf.matmul(hidden, weights['w'+str(len(self.dim_hidden)+1)]) + weights['b'+str(len(self.dim_hidden)+1)]
