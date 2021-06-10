import torch
import resnetMod
import torch
import torch.nn as nn
from torch.nn import functional as F
from torch.autograd import Variable
from MyTransformer2 import *


class selfAttentionModel(nn.Module):
    def __init__(self, num_classes=61, mem_size=512):
        super(selfAttentionModel, self).__init__()
        self.num_classes = num_classes
        self.resNet = resnetMod.resnet34(True, True)
        self.mem_size = mem_size
        self.ss_task = ss_task()
        self.weight_softmax = self.resNet.fc.weight
        self.transf = MyTransformer()
        self.avgpool = nn.AvgPool2d(7)
        self.dropout = nn.Dropout(0.7)
        self.conv_f = nn.Conv1d(512, 61, kernel_size=1, stride=1)
        self.fc = nn.Linear(self.mem_size, self.num_classes)
        self.classifier = nn.Sequential(self.dropout, self.fc)
        nn.init.xavier_normal_(self.conv_f.weight)
        nn.init.constant_(self.conv_f.bias, 0)
        

    def forward(self, inputVariable):
        logits = []
        for t in range(inputVariable.size(0)):
            logit, feature_conv, feature_convNBN = self.resNet(inputVariable[t])
            bz, nc, h, w = feature_conv.size()    #bz = batch size    #nc = number of channels    #h = height   #w = width
            embedding = torch.squeeze(torch.squeeze(self.avgpool(feature_conv),3),2)
            logit = self.transf(embedding)
            final_logit = self.fc(logit.cuda())
            logits.append(final_logit.view(1,-1))
            if stage == 2:
                ss_task_feats = self.ss_task(feature_conv) # a tensor of size [32,7*7] is returned
                ss_task_feats = ss_task_feats.view(feature_conv.size(0), 7*7) #now that it is a regression problem no more 2 and no more softmax needed
                feats_ss.append(ss_task_feats)
        
        if stage == 2:
            feats_ss = torch.stack(feats_ss,0)
            feats_ss = feats_ss.permute(1,0,2)        
            feats_ss = feats_ss.view(bz, inputVariable.size(0), 7*7)
        logits = torch.stack(logits,axis=0).squeeze(1)
        return logits, feats_ss
