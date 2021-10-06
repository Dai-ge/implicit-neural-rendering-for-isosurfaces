import os
import torch
from PIL import Image
from torch import nn
from torch.utils.data import Dataset,DataLoader
import torchvision.transforms as transforms
import pandas as pd
import numpy as np
import re
from torchvision.transforms import Resize, Compose, ToTensor, Normalize
#####调试用####
import sys
from torchvision.transforms.transforms import Compose
from tqdm import tqdm
#############
class TrainDataset(Dataset):
    def __init__(self,txt_file_root_path,img_file_root_path,sidelen=512,reload_bool=False):
        super(TrainDataset,self).__init__()

        #train_images_numbs = 2363 # 0.7*24389
        ## evry time sample (512*512)/2 pixels of each image

        
        self.sidelen=sidelen
        dataset_dir = txt_file_root_path
        # save_dir = '/afs/crc.nd.edu/user/p/pgu/Research/Isosurface_rendering/isosurfaces_rendering_45resi_connec_72images/result/'
        # model_path = '/afs/crc.nd.edu/user/p/pgu/Research/Isosurface_rendering/isosurfaces_rendering_45resi_connec_72images/saved_model/'

        
        self.txt_file_root_path=txt_file_root_path
        self.imgs_root_path=img_file_root_path
        self.txt_file_path=os.path.join(self.imgs_root_path,'vorts0008_infos.txt')
        self.imgs_name=self.__CollectFilePath()
        self.samples_num = 48000 #48000  #24000

        ###Data_Loading###
        self.train_images_indices=list(range(1,len(self.imgs_name)+1))
        self.coordinates,self.coordinates_tensor= self.get_mgrid(sidelen, dim=2)
        self.isovalue_theta_phi_input,self.pixel_ground_truth=self.ReadTrainingData(dataset_dir,self.train_images_indices)
        self.training_data_input, self.training_data_gt=self.GetTrainingData(self.isovalue_theta_phi_input,self.pixel_ground_truth,self.coordinates)
        
    def __getitem__(self,idx):
        return self.training_data_gt[idx],self.training_data_input[idx]

    def __len__(self):
        return len(self.training_data_gt)

    def GetTestingData_Testing(self):
        '''
        constructing the testing input with whole image to test the novel testing image
        '''
        samples = self.sidelen**2
        for e in self.isovalue_theta_phi_input:
            #print('e', e)
            ensembles = [e] * samples
            ensembles = torch.from_numpy(np.array(ensembles))
            #print('ensembles', ensembles)
            #print(ensembles[0])
            #print(ensembles[1])
            #index = np.random.randint(low=0,high=img_width*img_height, size=samples)
            #print('torch.FloatTensor(ensembles) ', ensembles.float())
            test_input_ = torch.cat([ensembles.float(),self.coordinates_tensor],1)

            break#!only one image is enough for test
            #print('test_coords_input',test_coords_input)
            # test_coords_input.append(test_input_)
        #testing_data_input = torch.FloatTensor(test_coords_input)
        return test_input_

    def ReadTrainingData(self,dataset_dir, train_images_indices):
        '''Read the iso, theta, and phi data from txt
            get the iso, theta, and phi and RGB values for training giving train_images_indices
        '''
        file = open(dataset_dir+'/vorts0008_infos.txt','r')
        Lines = file.readlines()

        isovalue_theta_phi_all = []
        for line in Lines:
            isovalue_theta_phi = []
            for c in line.split():
                #print(float(c))
                isovalue_theta_phi.append(float(c))
            isovalue_theta_phi_all.append(isovalue_theta_phi)

        isovalue_theta_phi_input = []
        pixel_ground_truth = []
        for i in train_images_indices:
            #np.array([-0.9333 -1.000 -0.8571])
            isovalue_theta_phi = isovalue_theta_phi_all[i-1]
            #print('isovalue_theta_phi', isovalue_theta_phi)
            isovalue_theta_phi_input.append(isovalue_theta_phi)
            
            
            path = dataset_dir+'/vorts0008_render_' + '{:03d}'.format(i) + '.png'
            #print('path', path)
            pixels_RGB = self.get_pxiels(path, 512)
            pixels_RGB_numpy = pixels_RGB.numpy()
            pixel_ground_truth.append(pixels_RGB_numpy)


        return isovalue_theta_phi_input, pixel_ground_truth

    def get_pxiels(self,path, sidelength):
        '''load the image and get the corresponding pixel RGB values that used for GT'''
        img = Image.open(path)
        transform = Compose([
            ToTensor(),
        ])
        img2 = transform(img)
        pixels = img2.permute(1, 2, 0)
        #print('pixels max', pixels.max())
        #print('pixels min', pixels.min())


        #print('pixels', pixels)
        #print('pixels shape', pixels.shape) # torch.Size([512, 512, 3])
        #pixels = pixels.view(sidelength*sidelength, 3)
        #print('pixels view', pixels)
        #print('pixels shape', pixels.shape)
        pixels_view = pixels.view(-1, 3)
        #print('pixels_view ', pixels_view)
        #print('pixels_view shape', pixels_view.shape)
        #print('pixels_view max', pixels_view.max())
        #print('pixels_view min', pixels_view.min())

        #print('pixels_view[56783]', pixels_view[56783])
        #print('pixels[56783]', pixels[56783])
        #print('test pixels', pixels-pixels_view)
        #print('check nonzeros', torch.nonzero(pixels-pixels_view))
        # print(torch.nonzero(torch.tensor([[0.0, 0.0, 0.0, 0.0],
        #                          [0.0, 0.0, 0.0, 0.0],
        #                         [0.0, 0.0, 0.0, 0.0],
        #                          [0.0, 0.0, 0.0,0.0]])))
        return pixels_view

    def GetTrainingData(self,isovalue_theta_phi_input,pixel_ground_truth,coordinates):
        '''
        constructing the training input and RGB GT values for trianing
        '''
        coords_input = []
        pixels_values = []
        samples = self.sidelen**2
        iso = np.zeros((self.samples_num,1))
        theta = np.zeros((self.samples_num,1))
        phi = np.zeros((self.samples_num,1))

        for idx,e in enumerate(isovalue_theta_phi_input):
            #print('e', e)
            #ensembles = [e] * samples_num#samples_num len(indeices)
            #print('ensembles', ensembles)
            #print(ensembles[0])
            #print(ensembles[1])
            index = np.random.randint(low=0,high=samples, size=self.samples_num)#indeices#np.random.randint(low=0,high=samples, size=samples_num)#batch_size*factor) #[0,512*512-1] #np.random.randint(1,samples, 2)
            #print('index', index)
            #print('index min', index.min())
            #print('index max', index.max())
            #print('coordinates[index]',coordinates[index])
            


            iso.fill(e[0])
            theta.fill(e[1])
            phi.fill(e[2])
            
            coords_input+=list(np.concatenate((iso,theta,phi,coordinates[index]),axis=1))#list(coordinates[index])#list(np.concatenate((ensembles,coordinates[index]),axis=1))
            
            # coords_input.append(coordinates[index])

            
            # coords_input +=list(np.concatenate((ensembles,coordinates[index]),axis=1))#list(coordinates[index])#list(np.concatenate((ensembles,coordinates[index]),axis=1))
            # print('coords_input',coords_input)
            
            
            pixels_values+=list(pixel_ground_truth[idx][index])
            #print('pixels_values',pixels_values)

        

        # print('np.asarray(coords_input)',np.asarray(coords_input))

        # training_data_input_test = torch.FloatTensor(coords_input)
        # print('training_data_input_test',training_data_input_test)

        training_data_input = torch.FloatTensor(np.asarray(coords_input))
        training_data_gt = torch.FloatTensor(np.asarray(pixels_values))
        #print('training_data_input',training_data_input)
        #print('training_data_input shape',training_data_input.shape)
        

        #print('training_data_gt',training_data_gt)

        return training_data_input, training_data_gt

    def __CollectFilePath(self, rename=False):
        """返回一个指定目录下(self.img_root_path)所有的png图像文件路径的列表

        Args:
            rename (bool, optional): [如果此参数为True，则重新命名所有的图像文件，保证所有图像文件名称为长度相等的统一格式]. Defaults to False.

        Returns:
            [list]: [一个含有所有图像路径的列表]
        """
        imgs_name=[]
        parten = re.compile(r'[0-9]{4}')
        if rename:
            for root, dirs_name, files_name in os.walk(self.imgs_root_path):
                for file_name in files_name:
                    if file_name[-3:] == 'txt':
                        continue
                    else:
                        if parten.search(file_name[9:]) == None:
                            new_name = 'vorts0008_render_0' + file_name[-7:]
                            new_path = os.path.join(root, new_name)
                            old_path = os.path.join(root, file_name)
                            os.rename(old_path, new_path)

        for root, dirs_name, files_name in os.walk(self.imgs_root_path):
            for file_name in files_name:
                if file_name[-3:] == 'txt':
                    continue
                else:
                    imgs_name.append(file_name)
        return imgs_name

    def get_mgrid(self,sidelen, dim=2):
        '''Generates a flattened grid of (x,y,...) coordinates in a range of -1 to 1.'''
        if isinstance(sidelen, int):
            sidelen = dim * (sidelen,)

        if dim == 2:
            pixel_coords = np.stack(np.mgrid[:sidelen[0], :sidelen[1]], axis=-1)[None, ...].astype(np.float32)
            pixel_coords[0, :, :, 0] = pixel_coords[0, :, :, 0] / (sidelen[0] - 1)
            pixel_coords[0, :, :, 1] = pixel_coords[0, :, :, 1] / (sidelen[1] - 1)
        elif dim == 3:
            pixel_coords = np.stack(np.mgrid[:sidelen[0], :sidelen[1], :sidelen[2]], axis=-1)[None, ...].astype(np.float32)
            pixel_coords[..., 0] = pixel_coords[..., 0] / max(sidelen[0] - 1, 1)
            pixel_coords[..., 1] = pixel_coords[..., 1] / (sidelen[1] - 1)
            pixel_coords[..., 2] = pixel_coords[..., 2] / (sidelen[2] - 1)
        else:
            raise NotImplementedError('Not implemented for dim=%d' % dim)

        pixel_coords -= 0.5
        pixel_coords *= 2.
        pixel_coords = torch.Tensor(pixel_coords).view(-1, dim)
        coords_numpy = pixel_coords.numpy()
        
        return coords_numpy, pixel_coords


if __name__ == "__main__":
    txt_file_root_path='./data/train_data'
    img_file_root_path= './data/train_data'

    t=DataLoader(TrainDataset(txt_file_root_path,img_file_root_path))
    for data in t:
        label,input_data=data
        print(label.shape)
        print(input_data.shape)
        break
