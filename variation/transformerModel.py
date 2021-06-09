import torch
import resnetMod
import torch
import torch.nn as nn
from torch.nn import functional as F
from torch.autograd import Variable
from MyTransformer import *


class selfAttentionModel(nn.Module):
    def __init__(self, num_classes=61, mem_size=512):
        super(selfAttentionModel, self).__init__()
        self.num_classes = num_classes
        self.resNet = resnetMod.resnet34(True, True)
        self.mem_size = mem_size
        self.weight_softmax = self.resNet.fc.weight
        self.transf = MyTransformer()
        self.avgpool = nn.AvgPool2d(7)
        self.dropout = nn.Dropout(0.7)
        self.fc = nn.Linear(mem_size, self.num_classes)
        self.classifier = nn.Sequential(self.dropout, self.fc)

    def forward(self, inputVariable):
        predictions = []
        for t in range(inputVariable.size(0)):
            logit, feature_conv, feature_convNBN = self.resNet(inputVariable[t])
            
		
	    n_frames, n_channels, h, w = feature_conv.size()	# n_channels = 512 and h x w = 7x7
	    mbedding = torch.squeeze(torch.squeeze(self.avgpool(feature_conv),3),2)
	    
	    logit = self.transf(embedding[k])
            final_logit = nn.Linear(2048,61)
	    predictions.append(final_logit)
	logits.view(inputVariable.size(0), -1)
        return probs
