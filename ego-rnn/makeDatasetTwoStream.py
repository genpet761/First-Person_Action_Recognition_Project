import os
import torch
from torch.utils.data import Dataset
from PIL import Image
import numpy as np
import random
import glob
import sys

def gen_split(root_dir,train_dataset_folder, stackSize = 5):
    DatasetX = [] #Path to RGB frame
    DatasetY = []
    DatasetF = []
    Labels = [] #Labels
    NumFrames = [] #
    root_dir = os.path.join(root_dir, 'flow_x_processed')
    for dir_user in train_dataset_folder:
        print('Splittin in ' + dir_user + ' folder')
        class_id = 0
        dir = os.path.join(root_dir, dir_user) #Folder effettiva dove mettere i file
        action_sorted = sorted(os.listdir(dir))
        for target in action_sorted:
          dir1 = os.path.join(dir, target) #/ego-rnn/content/GTEA61/flow_x_processed/S4/close_peanut ,/ego-rnn/content/GTEA61/flow_x_processed/S4/close_mustard ..
          insts = sorted(os.listdir(dir1)) # folder 1, 2 ,3 in each action
          if insts != []:
            for inst in insts:
              inst_dir = os.path.join(dir1, inst)
              numFrames = len(glob.glob1(inst_dir, '*[0-9].png')) # nome dei file per ogni azione [0-9 indica numero generico]
              if numFrames >= stackSize: # numero di frame sufficiente
                NumFrames.append(numFrames) # numero di frame x ogni folder
                DatasetX.append(inst_dir)
                Labels.append(class_id) # numero della classe del azione
                DatasetF.append(os.path.join(inst_dir.replace('flow_x_processed', 'processed_frames2'), "rgb"))
                #print(inst_dir)
                DatasetY.append(inst_dir.replace('flow_x_processed', 'flow_y_processed'))
            class_id += 1
    return DatasetX, DatasetY, DatasetF, Labels, NumFrames



class makeDataset(Dataset):
    def __init__(self, root_dir,train_dataset_folder, spatial_transform=None, sequence=False, stackSize=5,
                 train=True, numSeg=5, fmt='.png', phase='train', seqLen = 16):
        """
        Args:
            root_dir (string): Directory with all the images.
            transform (callable, optional): Optional transform to be applied
                on a sample.
        """

        self.imagesX, self.imagesY, self.imagesF, self.labels, self.numFrames = gen_split(
            root_dir, train_dataset_folder, stackSize)
        self.spatial_transform = spatial_transform
        self.train = train
        self.numSeg = numSeg
        self.sequence = sequence
        self.stackSize = stackSize
        self.fmt = fmt
        self.phase = phase
        self.seqLen = seqLen

    def __len__(self):
        return len(self.imagesX)

    def __getitem__(self, idx):
        vid_nameX = self.imagesX[idx]
        vid_nameY = self.imagesY[idx]
        vid_nameF = self.imagesF[idx]
        label = self.labels[idx]
        numFrame = self.numFrames[idx]
        inpSeqSegs = []
        self.spatial_transform.randomize_parameters()
        if self.sequence is True:
            if numFrame <= self.stackSize:
                frameStart = np.ones(self.numSeg)
            else:
                frameStart = np.linspace(1, numFrame - self.stackSize, self.numSeg)
            for startFrame in frameStart:
                inpSeq = []
                for k in range(self.stackSize):
                    i = k + int(startFrame)
                    fl_name = vid_nameX + '/flow_x_' + str(int(round(i))).zfill(5) + '.png'
                    img = Image.open(fl_name)
                    inpSeq.append(self.spatial_transform(img.convert('L'), inv=True, flow=True))
                    # fl_names.append(fl_name)
                    fl_name = vid_nameY + '/flow_y_' + str(int(round(i))).zfill(5) + '.png'
                    img = Image.open(fl_name)
                    inpSeq.append(self.spatial_transform(img.convert('L'), inv=False, flow=True))
                inpSeqSegs.append(torch.stack(inpSeq, 0).squeeze())
            inpSeqSegs = torch.stack(inpSeqSegs, 0)
        else:
            if numFrame <= self.stackSize:
                startFrame = 1
            else:
                if self.phase == 'train':
                    startFrame = random.randint(1, numFrame - self.stackSize)
                else:
                    startFrame = np.ceil((numFrame - self.stackSize)/2)
            inpSeq = []
            for k in range(self.stackSize):
                i = k + int(startFrame)
                fl_name = vid_nameX + '/flow_x_' + str(int(round(i))).zfill(5) + '.png'
                img = Image.open(fl_name)
                inpSeq.append(self.spatial_transform(img.convert('L'), inv=True, flow=True))
                # fl_names.append(fl_name)
                fl_name = vid_nameY + '/flow_y_' + str(int(round(i))).zfill(5) + '.png'
                img = Image.open(fl_name)
                inpSeq.append(self.spatial_transform(img.convert('L'), inv=False, flow=True))
            inpSeqSegs = torch.stack(inpSeq, 0).squeeze(1)
        inpSeqF = []
        for i in np.linspace(1, numFrame, self.seqLen, endpoint=False):
            fl_name = vid_nameF + '/' + 'rgb' + str(int(np.floor(i))).zfill(4) + self.fmt
            img = Image.open(fl_name)
            inpSeqF.append(self.spatial_transform(img.convert('RGB')))
        inpSeqF = torch.stack(inpSeqF, 0)
        return inpSeqSegs, inpSeqF, label#, vid_nameF#, fl_name

