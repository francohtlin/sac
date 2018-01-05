"""Tests for real_nvp distribution."""

from tensorflow.python.platform import test
import tensorflow as tf
import numpy as np

from sac.distributions.real_nvp_bijector import CouplingBijector

def TRANSLATION_FN_WITHOUT_BIAS(inputs):
    return 5 * inputs ** 2

def SCALE_FN_WITHOUT_BIAS(inputs):
    return 3 * inputs

BIAS = 2
def TRANSLATION_FN_WITH_BIAS(inputs):
    return TRANSLATION_FN_WITHOUT_BIAS(inputs) - BIAS

def SCALE_FN_WITH_BIAS(inputs):
    return SCALE_FN_WITHOUT_BIAS(inputs) - BIAS

DEFAULT_2D_INPUTS = np.array([
    [ 0, 0],
    [ 0, 1],
    [ 1, 0],
    [ 1, 1]
], dtype=np.float32)

class CouplingBijectorTest(test.TestCase):
    def test_forward(self):
        odd_layer = CouplingBijector(
            parity="odd",
            name="coupling_odd",
            translation_fn=TRANSLATION_FN_WITH_BIAS,
            scale_fn=SCALE_FN_WITH_BIAS
        )

        even_layer = CouplingBijector(
            parity="even",
            name="coupling_even",
            translation_fn=TRANSLATION_FN_WITH_BIAS,
            scale_fn=SCALE_FN_WITH_BIAS
        )

        inputs = tf.constant(DEFAULT_2D_INPUTS)
        odd_forward_out = odd_layer.forward(inputs)
        odd_forward_log_det_jacobian = odd_layer.forward_log_det_jacobian(
            inputs)

        even_forward_out = even_layer.forward(odd_forward_out)
        even_forward_log_det_jacobian = even_layer.forward_log_det_jacobian(
            odd_forward_out)

        # Verify that the true side of the mask comes out as identity
        with self.test_session() as session:
            (inputs_num,
             odd_forward_out_num,
             even_forward_out_num,
             odd_forward_log_det_jacobian_num,
             even_forward_log_det_jacobian_num) = session.run((
                 inputs,
                 odd_forward_out,
                 even_forward_out,
                 odd_forward_log_det_jacobian,
                 even_forward_log_det_jacobian,
             ))

        self.assertAllEqual(odd_forward_out_num[:, 1], inputs_num[:, 1])
        self.assertAllEqual(even_forward_out_num[:, 0], odd_forward_out_num[:, 0])

        self.assertAllEqual(odd_forward_log_det_jacobian_num,
                            SCALE_FN_WITH_BIAS(inputs_num[:, 1]))
        self.assertAllEqual(even_forward_log_det_jacobian_num,
                            SCALE_FN_WITH_BIAS(odd_forward_out_num[:, 0]))

    def test_forward_without_bias(self):
        layer_without_bias = CouplingBijector(
            parity="odd",
            name="coupling_odd",
            translation_fn=TRANSLATION_FN_WITHOUT_BIAS,
            scale_fn=SCALE_FN_WITHOUT_BIAS
        )

        layer_with_bias = CouplingBijector(
            parity="odd",
            name="coupling_odd",
            translation_fn=TRANSLATION_FN_WITH_BIAS,
            scale_fn=SCALE_FN_WITH_BIAS
        )

        inputs = tf.constant(DEFAULT_2D_INPUTS)
        forward_out_with_bias = layer_with_bias.forward(inputs)
        forward_out_without_bias = layer_without_bias.forward(inputs)

        with self.test_session() as session:
            (inputs_num,
             forward_out_with_bias_num,
             forward_out_without_bias_num) = session.run(
                 (inputs, forward_out_with_bias, forward_out_without_bias))

        # Should return identity for "odd" axis
        # Should return different results for "with" and "without" bias

        self.assertAllEqual(
            forward_out_with_bias_num,
            np.array([[-2.        ,  0.        ],
                      [ 3.        ,  1.        ],
                      [-1.86466467,  0.        ],
                      [ 5.71828175,  1.        ]], dtype=np.float32)
        )

        self.assertAllEqual(
            forward_out_without_bias_num,
            np.array([[  0.        ,   0.        ],
                      [  5.        ,   1.        ],
                      [  1.        ,   0.        ],
                      [ 25.08553696,   1.        ]], dtype=np.float32)
        )

    def test_forward_inverse_returns_identity(self):
        layer1 = CouplingBijector(
            parity="odd",
            name="coupling_1",
            translation_fn=TRANSLATION_FN_WITH_BIAS,
            scale_fn=SCALE_FN_WITH_BIAS
        )
        layer2 = CouplingBijector(
            parity="even",
            name="coupling_2",
            translation_fn=TRANSLATION_FN_WITH_BIAS,
            scale_fn=SCALE_FN_WITH_BIAS
        )

        inputs = tf.constant(DEFAULT_2D_INPUTS)
        forward_out = layer1.forward(inputs)
        forward_out = layer2.forward(forward_out)
        inverse_out = layer2.inverse(forward_out)
        inverse_out = layer1.inverse(inverse_out)

        with self.test_session():
            self.assertAllClose(inputs.eval(), inverse_out.eval())

    def test_get_mask(self):
        inputs = tf.constant([[0,0], [0,1], [1,0], [1,1]], dtype=tf.float32)
        EXPECTED = {"odd": [0,1], "even": [1,0]}
        for parity, expected_mask in EXPECTED.items():
            layer = CouplingBijector(
                parity=parity,
                name="coupling_" + parity,
                translation_fn=lambda x: None,
                scale_fn=lambda x: None)
            mask = layer.get_mask(inputs, tf.float32)

            with self.test_session():
                self.assertAllEqual(
                    mask.eval(), tf.constant(expected_mask).eval())

if __name__ == '__main__':
  test.main()
