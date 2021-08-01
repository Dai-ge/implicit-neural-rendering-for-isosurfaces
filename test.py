from model import *
from train_dataset import *
import matplotlib.pyplot as plt
import numpy as np
from model import *
from train_dataset import *
import argparse
import os
from tqdm import tqdm
from torch.nn import MSELoss
import time
from datetime import datetime
import numpy as np
from loss_comp import *
import sys
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


class Test():
    def __init__(self, config):
        self.epochs = 1
        self.time = time.time()
        self.batch_size = config.batch_size
        #############################
        data = TrainDataset(text_path=config.input_txt,
                            img_root_path=config.input_image,
                            side_length=config.output_shape)
        self.dataloader = DataLoader(data, batch_size=self.batch_size)
        self.net = torch.load('.\\net.pkl', map_location=device)
        self.net.to(device=device)
        #self.optimizer = torch.optim.Adam(lr=1e-4, params=self.net.parameters())
        self.loss_fuc = MSELoss()
        self.loss = None
    # matrix for x values
    def matrix_x(self, length):
        # create 2d matrix
        matrix = torch.zeros([length, length, 1]).to(device)

        # init tmp value and step number
        tmp = -1
        step_num = length * length - 1
        # assign value (-1 to 1, by row and then by col)
        for i in range(length):
            for j in range(length):
                matrix[i][j] = tmp
                tmp += 2 / step_num

        # return matrix
        return matrix

    # matrix for y values
    def matrix_y(self, length):
        # create 2d matrix
        matrix = torch.zeros([length, length, 1]).to(device)

        # init tmp value and step number
        tmp = -1
        step_num = length * length - 1
        # assign value (-1 to 1, by row and then by col)
        for i in range(length):
            for j in range(length):
                matrix[j][i] = tmp
                tmp += 2 / step_num

        # return matrix
        return matrix

    # matrix for x and y values
    def matrix_x_y(self, length):
        return self.concat_matrix_2(self.matrix_x(length), self.matrix_y(length))

    def matrix_single_txt(self, length, v):
        # create 2d matrix
        matrix = torch.zeros([length, length, 1]).to(device)

        # add v as value
        matrix = torch.add(matrix, v)

        # return matrix
        return matrix

    def matrix_txt(self, length, v1, v2, v3):
        return self.concat_matrix_3(self.matrix_single_txt(length, v1),
                                    self.matrix_single_txt(length, v2),
                                    self.matrix_single_txt(length, v3))

    def concat_matrix_2(self, a, b):
        res = torch.cat((a, b), dim=-1)
        return res

    def concat_matrix_3(self, a, b, c):
        res = torch.cat((a, b, c), dim=-1)
        return res


    def test(self):
        print("Start Testing:")

        for _, data in enumerate(self.dataloader):
            txt_data, label_img = data

            # Concat by row, and then reshape txt to have row of 3
            txt_data = torch.cat(txt_data, dim=0).reshape(3, -1)

            # transpose row and col
            txt_data = torch.transpose(txt_data, 0, 1)

            height, width = label_img.shape[-1], label_img.shape[-1]

            assert height == width
            length = height or width

            # train a batch of images
            for ind in range(self.batch_size):
                self.test_one_img(label_img[ind], txt_data[ind], length)


    def test_one_img(self, label_img, txt_data, length):

        with torch.no_grad():
            # obtain three values (isovalue, alpha, beta)
            v1, v2, v3 = txt_data[0], txt_data[1], txt_data[2]

            # concate matrix to obtain input data
            input_data = self.concat_matrix_2(self.matrix_x_y(length), self.matrix_txt(length, v1, v2, v3))

            # prepare input and GT
            ground_truth = label_img

            input_data, ground_truth = self.prepare(input_data, ground_truth)

            # obtain output from model
            output, _ = self.net(input_data)

            # permute the output
            output = output.permute(2, 0, 1)

            # the MSE loss
            self.loss = self.loss_fuc(output, ground_truth)
            print("loss is", self.loss)

            self.visualize(output)

    def write_log(self, loss):
        with open(f'log{datetime.now().strftime("%m%d")}.txt', 'a') as f:
            f.write(
                f'time:{datetime.now().strftime("%m/%d_%H:%M:%S")}, loss:{loss},  '
                f'time_consuming:{time.time() - self.time:.2f}s\n')
        self.time = time.time()

    def prepare(self, *args):
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        if len(args) > 1:
            return (a.float().to(device) for a in args)

    def visualize(self, output):
        fig, axes = plt.subplots(1, 1, figsize=(6, 6))
        #print("output is", output)
        axes.imshow(output.cpu().detach().numpy().transpose(1,2,0))
        #print("outout for vis is", output.cpu().detach().numpy().transpose(1,2,0))
        plt.savefig('recent.png')

        sys.exit(0)




if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--input_image', type=str,
                        default='.\\tiny_vorts0008_normalize_dataset')
    parser.add_argument('--input_txt', type=str, default='.\\tiny_vorts0008_normalize_dataset\\vorts0008_infos.txt')
    parser.add_argument('--output_shape', type=int, default=512)  # the paper uses 256 for this one
    parser.add_argument('--batch_size', type = int, default=4)
    config = parser.parse_args()

    test = Test(config)

    test.test()