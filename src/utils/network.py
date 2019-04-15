import numpy as np
from keras import models, layers, callbacks, optimizers
from .layers import Mask, PredictionCapsule, FeatureCapsule
from .losses import margin_loss
from .dataset import dataset_generator, get_dataset

class CapsNet:
    """Capsule neural network for Face Recognition.

    A neural network using a CapsNet architecture with capsules mapped to each
    biometric property which wetend to recognise. Produces an identity tensor
    for each given image, where each member is corresponding to configuration
    and weights in capsules.
    """

    def __init__(self, input_shape, bins):
        """CapsNet instance constructor.

        Args:
            input_shape: Input data shape - [width, height, channels]
            bins: Number of predicted faces

        """
        # Input layer
        x = layers.Input(shape=input_shape)

        # Encoder
        conv = layers.Conv2D(
            filters=256,
            kernel_size=9,
            strides=1,
            padding='valid',
            activation='relu',
            name='encoder_conv'
        )(x)
        feature_caps = FeatureCapsule(
            capsule_dim=8,
            channels_count=32,
            kernel_size=9,
            strides=2,
            padding='valid',
            name='encoder_feature_caps'
        )(conv)
        prediction_caps = PredictionCapsule(
            capsule_count=bins,
            capsule_dim=16,
            routing_iters=3,
            name='encoder_pred_caps'
        )(feature_caps)

        # Decoder
        y = layers.Input(shape=(bins,))

        decoder = models.Sequential(
            name='decoder',
            layers=[
                layers.Dense(
                    units=512,
                    activation='relu',
                    input_dim=16*bins,
                    name='decoder_dense_1'
                ),layers.Dense(
                    units=1024,
                    activation='relu',
                    name='decoder_dense_2'
                ),
                layers.Dense(
                    units=np.prod(input_shape),
                    activation='sigmoid',
                    name='decoder_dense_3'
                ),
                layers.Reshape(
                    target_shape=input_shape,
                    name='decoder_reshape'
                )
            ]
        )

        masked_train = Mask()([prediction_caps, y])
        masked_inference = Mask()(prediction_caps)

        # Models
        self.models = dict(
            train=models.Model(
                [x, y],
                [prediction_caps, decoder(masked_train)]
            ),
            inference=models.Model(
                x,
                [feature_caps, prediction_caps, decoder(masked_inference)]
            )
        )


    def train(self, data, batch_size=100, epochs=50,
              lr=0.001, lr_decay=0.4, decoder_loss_weight=.4,
              save_dir=None):
        """Train the network.

        Args:
            data (tuple): Tuple containing train and test data along with their labels

        Returns:
            A trained TensorFlow model

        """
        (x_train, y_train), (x_test, y_test) = data

        # Callback
        cb = [
            callbacks.CSVLogger(f'{save_dir}/log.csv'),
            callbacks.LearningRateScheduler(lambda e: lr * (lr_decay ** e)),
            callbacks.ModelCheckpoint(
                f'{save_dir}/weights.{{epoch:02d}}.h5', 'val_capsnet_acc',
                save_best_only=True, save_weights_only=True, verbose=1
            ),
            callbacks.TensorBoard(
                f'{save_dir}/tensorboard_logs', batch_size=batch_size
            ),
        ]

        self.models['train'].compile(
            optimizer=optimizers.Adam(lr=lr),
            loss=[margin_loss, 'mse'],
            loss_weights=[1., decoder_loss_weight],
            metrics={'capsnet': 'accuracy'}
        )

        self.models['train'].fit_generator(
            generator=dataset_generator(x_train, y_train),
            steps_per_epoch=int(y_train.shape[0] / batch_size),
            epochs=epochs,
            validation_data=[x_test, y_test],
            callbacks=cb
        )

        self.models['train'].save_weights(f'{save_dir}/model.h5')

    def inference(self, data):
        pass
