from common.experiment_base import Experiment
from image_classifier_experiment.model.classifier import ImageClassifierTrainer, ClassifierOperator
from PIL import Image, ImageOps
import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
import glob
import os
import math
import time
import csv


class ClassifierExperiment(Experiment):
    def __init__(self, config={}):
        # the inputted config takes precedence over the default
        config = {**{
            'EPOCHS': 10,
            'input_shape': (28, 28),
            'asset_opts': {
                'save_assets': False,
                'dir': './image_classifier_experiment/generated_plots/'
            },
            'dataset': tf.keras.datasets.fashion_mnist,
            'custom_image_dir': './image_classifier_experiment/custom images/fashion_mnist/*.jpg',
            'labels': [0, 8, 8, 3, 2],
            'class_names': [
                'T-shirt/top',  # 0
                'Trouser',  # 1
                'Pullover',  # 2
                'Dress',  # 3
                'Coat',  # 4
                'Sandal',  # 5
                'Shirt',  # 6
                'Sneaker',  # 7
                'Bag',  # 8
                'Ankle boot'  # 9
            ],
        }, **config}

        self.config = config

        super().__init__()

    def _execute(self):
        """Executes the training then returns results like (test_image_results, custom_image_results)"""

        # grab the dataset from the config
        dataset = self.config['dataset']

        # build the trainer and execute the training with the dataset given
        TRAINER = ImageClassifierTrainer(dataset.load_data(), config={
            'input_shape': self.config['input_shape'],
            'nodes': 128,
            'EPOCHS': self.config['EPOCHS'],
            'num_classes': len(self.config['class_names'])
        })
        (processed_data, trained_tf_model, history) = TRAINER.run()

        # build an operator instance with the trained model
        OPERATOR = ClassifierOperator(trained_tf_model)

        # Plot loss and accuracy if able to
        if len(history.history.keys()) > 0:
            OPERATOR.plot(history)

        # evaluate the model
        _, (test_images, test_labels) = processed_data
        (test_loss, test_acc) = OPERATOR.evaluate((test_images, test_labels))

        # use the trained model to predict the result of the test images
        predictions_array = OPERATOR.use(test_images)

        # plot the predictions against the real labels and save if desired
        self.__plot_multi_predictions(predictions_array,
                                      test_labels,
                                      test_images,
                                      15,
                                      plot_title="First 15 Image Results")

        # print the loss and save to a csv file if desired
        test_image_results = {
            "EPOCHS": self.config['EPOCHS'],
            "loss": test_loss,
            "accuracy": test_acc
        }
        self.__print_dict(f"{self.config['EPOCHS']}EPOCHS Test Images", test_image_results)

        # obtain all custom images from given directory and preprocess them
        custom_imgs = []
        for f in sorted(glob.glob(self.config['custom_image_dir']), key=os.path.basename):
            # process the images into a raw data format
            img = Image.open(f)
            img = img.resize(self.config['input_shape'])
            img = ImageOps.grayscale(img)
            img = ImageOps.invert(img)
            img = np.asarray(img)

            # once converted use the trainer's preprocessing function as well
            img = TRAINER.manual_preprocess(img)

            # append post processed images to an array
            custom_imgs.append(img)
        custom_imgs = np.array(custom_imgs)

        # use the trained model to predict the custom images
        custom_predictions_array = OPERATOR.use(custom_imgs)

        # evaluate the predctions on the custom images
        correct_labels = self.config['labels']
        (custom_test_loss, custom_test_acc) = OPERATOR.evaluate((custom_imgs, np.array(correct_labels)))

        # plot the custom predictions and save if desired
        self.__plot_multi_predictions(custom_predictions_array,
                                      correct_labels,
                                      custom_imgs,
                                      len(correct_labels),
                                      plot_title="Custom Image Results")

        # print the loss and save if desired
        custom_image_results = {
            "EPOCHS": self.config['EPOCHS'],
            "loss": custom_test_loss,
            "accuracy": custom_test_acc
        }
        self.__print_dict(f"{self.config['EPOCHS']}EPOCHS Custom Images", custom_image_results)

        return test_image_results, custom_image_results

    def __plot_image(self, predictions_array, true_label, img):
        """Plots a single image with the predicted and true label"""

        plt.grid(False)
        plt.xticks([])
        plt.yticks([])

        plt.imshow(img, cmap=plt.cm.binary)

        predicted_label = np.argmax(predictions_array)
        if predicted_label == true_label:
            color = 'blue'
        else:
            color = 'red'

        plt.xlabel("{} {:2.0f}% ({})".format(self.config['class_names'][predicted_label],
                                             100 * np.max(predictions_array),
                                             self.config['class_names'][true_label]),
                   color=color)

    def __plot_value_array(self, predictions_array, true_label):
        """Plots the predicted liklihoods of each class"""

        plt.grid(False)
        plt.xticks(range(10))
        plt.yticks([])
        thisplot = plt.bar(range(10), predictions_array, color="#777777")
        plt.ylim([0, 1])
        predicted_label = np.argmax(predictions_array)

        thisplot[predicted_label].set_color('red')
        thisplot[true_label].set_color('blue')

    def __plot_multi_predictions(self, predictions, test_labels, test_images, num_images,
                                 plot_title="Multi Prediction Results"):
        """Plots multiple images and their class probabilities that the model provided"""

        # Plot the first X test images, their predicted labels, and the true labels.
        # Color correct predictions in blue and incorrect predictions in red.
        num_rows = math.ceil(num_images / 3)
        num_cols = 3
        fig = plt.figure(figsize=(2 * 2 * num_cols, 2 * num_rows))
        fig.suptitle(plot_title, fontsize=16)

        for i in range(num_images):
            plt.subplot(num_rows, 2 * num_cols, 2 * i + 1)
            self.__plot_image(predictions[i], test_labels[i], test_images[i])
            plt.subplot(num_rows, 2 * num_cols, 2 * i + 2)
            self.__plot_value_array(predictions[i], test_labels[i])
        plt.tight_layout()

        self.__print_plot(plot_title)

    def __print_plot(self, prefix):
        """Saves the plot if desired, then prints"""

        if self.config['asset_opts']['save_assets']:
            plot_name = f"{self.config['asset_opts']['dir']}{self.config['EPOCHS']}EPOCHS {prefix}-{int(time.time())}.png"
            print(f"saving plot... ({plot_name})")
            plt.savefig(plot_name)

        plt.show()

    def __print_dict(self, prefix, dict):
        """Saves a given dictionary to the asset directory if desired then prints"""

        if self.config['asset_opts']['save_assets']:
            asset_name = f"{self.config['asset_opts']['dir']}{prefix}-{int(time.time())}.csv"
            print(f"saving asset... ({asset_name})")
            # open file for writing, "w" is writing
            w = csv.writer(open(asset_name, "w"))

            # loop over dictionary keys and values
            for key, val in dict.items():
                # write every key and value to file
                w.writerow([key, val])
        print(dict)


def run_classifier_experiment():
    """Function to run the image classifier experiment"""

    # Based off of https://www.tensorflow.org/tutorials/keras/classification

    epoch_list = [0, 5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 100]
    experiment1_results = {
        'test': {
            'epochs': epoch_list,
            'loss': [],
            'accuracy': [],
        },
        'custom': {
            'epochs': epoch_list,
            'loss': [],
            'accuracy': [],
        }
    }
    experiment2_results = {
        'test': {
            'epochs': epoch_list,
            'loss': [],
            'accuracy': [],
        },
        'custom': {
            'epochs': epoch_list,
            'loss': [],
            'accuracy': [],
        }
    }

    for EPOCHS in epoch_list:
        # execute experiment with Fashion MNIST
        experiment1 = ClassifierExperiment({
            'EPOCHS': EPOCHS,
            'asset_opts': {
                'save_assets': True,
                'dir': './image_classifier_experiment/generated_assets/fashion_mnist/'
            },
            'dataset': tf.keras.datasets.fashion_mnist,
            'custom_image_dir': './image_classifier_experiment/custom images/fashion_mnist/*.jpg',
            'labels': [0, 8, 8, 3, 2, 1, 4, 5, 9, 7, 6],
            'class_names': [
                'T-shirt/top',  # 0
                'Trouser',  # 1
                'Pullover',  # 2
                'Dress',  # 3
                'Coat',  # 4
                'Sandal',  # 5
                'Shirt',  # 6
                'Sneaker',  # 7
                'Bag',  # 8
                'Ankle boot'  # 9
            ],
        })
        test_image_results1, custom_image_results1 = experiment1.run()
        experiment1_results['test']['loss'].append(test_image_results1['loss'])
        experiment1_results['test']['accuracy'].append(test_image_results1['accuracy'])
        experiment1_results['custom']['loss'].append(custom_image_results1['loss'])
        experiment1_results['custom']['accuracy'].append(custom_image_results1['accuracy'])

        # execute experiment with MNIST
        experiment2 = ClassifierExperiment({
            'EPOCHS': EPOCHS,
            'asset_opts': {
                'save_assets': True,
                'dir': './image_classifier_experiment/generated_assets/mnist/'
            },
            'dataset': tf.keras.datasets.mnist,
            'custom_image_dir': './image_classifier_experiment/custom images/mnist/*.png',
            'labels': [0, 0, 1, 9, 8, 2, 4, 3, 5, 7, 6],
            'class_names': [
                '0',  # 0
                '1',  # 1
                '2',  # 2
                '3',  # 3
                '4',  # 4
                '5',  # 5
                '6',  # 6
                '7',  # 7
                '8',  # 8
                '9'  # 9
            ],
        })
        test_image_results2, custom_image_results2 = experiment2.run()
        experiment2_results['test']['loss'].append(test_image_results2['loss'])
        experiment2_results['test']['accuracy'].append(test_image_results2['accuracy'])
        experiment2_results['custom']['loss'].append(custom_image_results2['loss'])
        experiment2_results['custom']['accuracy'].append(custom_image_results2['accuracy'])

    # plot results for test data
    plt.plot('epochs', 'loss', data=experiment1_results['test'], label='Fashion MNIST')
    plt.plot('epochs', 'loss', data=experiment2_results['test'], label='MNIST')
    plt.xlabel('EPOCHS')
    plt.ylabel('Loss')
    plt.title('Test Data Fashion MNIST vs MNIST')
    plt.legend()
    plt.savefig("./image_classifier_experiment/generated_assets/Test Data Fashion MNIST vs MNIST.png")
    plt.show()

    # plot results for custom data
    plt.plot('epochs', 'loss', data=experiment1_results['custom'], label='Fashion MNIST')
    plt.plot('epochs', 'loss', data=experiment2_results['custom'], label='MNIST')
    plt.xlabel('EPOCHS')
    plt.ylabel('Loss')
    plt.title('Custom Data Fashion MNIST vs MNIST')
    plt.legend()
    plt.savefig("./image_classifier_experiment/generated_assets/Custom Data Fashion MNIST vs MNIST.png")
    plt.show()
