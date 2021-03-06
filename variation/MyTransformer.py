import torch
import torch.nn as nn
from torch.nn import functional as F
from torch.autograd import Variable
import math
import numpy as np

class MyTransformer(nn.Module):
    def __init__(self, num_frames):
        super(MyTransformer, self).__init__()
        self.d_k = 61
        self.d_v = 61
        self.d_model = 610
        self.d_ff = 2048
        self.heads = 10
        self.num_frames = num_frames
        self.batch_size = 0
        self.W_q = torch.nn.init.xavier_normal_(Variable(torch.randn(self.d_model, self.d_k).type(torch.cuda.FloatTensor), requires_grad=True))
        self.W_k = torch.nn.init.xavier_normal_(Variable(torch.randn(self.d_model, self.d_k).type(torch.cuda.FloatTensor), requires_grad=True))
        self.W_v = torch.nn.init.xavier_normal_(Variable(torch.randn(self.d_model, self.d_v).type(torch.cuda.FloatTensor), requires_grad=True))
        self.W_o = torch.nn.init.xavier_normal_(Variable(torch.randn(self.heads*self.d_v, self.d_model).type(torch.cuda.FloatTensor), requires_grad=True))
        self.fc1 = nn.Linear(self.d_model*self.num_frames, self.d_ff,1)
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(0.1)
        self.fc2 = nn.Linear(self.d_ff, self.d_model*self.num_frames,1)
        self.classifier = nn.Sequential(self.fc1,self.activation,self.dropout,self.fc2)
        nn.init.xavier_normal_(self.fc1.weight)
        nn.init.constant_(self.fc1.bias, 0)
        nn.init.xavier_normal_(self.fc2.weight)
        nn.init.constant_(self.fc2.bias, 0)



    def forward(self,frame):
        self.batch_size = frame.size(0)
        frame_position = self.positionalencoding(frame.size(1))
        frame2 = frame + frame_position
        multi_head_output = self.temporal_attention(frame.squeeze(0))
        transformer_output = self.MLP_head(multi_head_output)
        return transformer_output


    def temporal_attention(self,frame):
        outputs = []
        for j in range(frame.size(0)):
            batch_outputs = []
            for i in range(self.heads):
                Query = torch.mm(frame[j],self.W_q)
                Key = torch.mm(frame[j],self.W_k)
                Value = torch.mm(frame[j],self.W_v)

                single_head_output = self.self_attention(Query,Key,Value)
                batch_outputs.append(single_head_output)
            heads_concat_output = torch.cat(batch_outputs,axis=1)
            outputs.append(heads_concat_output)
        outputs = torch.stack(outputs,dim=0)
        multi_head_output = torch.mm(heads_concat_output,self.W_o)
        multi_head_output = multi_head_output + frame
        layer_normalization1 = nn.LayerNorm(multi_head_output.size()[1:], elementwise_affine=False)
        multi_head_output = layer_normalization1(multi_head_output) #the error says "RuntimeError: expected scalar type Double but found Float" but actually works if I cast to float from double, bello    
        
        multi_head_output = torch.unsqueeze(multi_head_output,2)
        return multi_head_output


    def self_attention(self,Query,Key,Value):
        Key_T = torch.transpose(Key,0,1)
        Query_Key_T = torch.div(torch.matmul(Query,Key_T),math.sqrt(self.d_k))
        attention = F.softmax(Query_Key_T,dim=-1)
        self_attention_output = torch.matmul(attention,Value)
        return self_attention_output


    def MLP_head(self,multi_head_output):
        out = self.classifier(multi_head_output.squeeze(2).view(self.batch_size,-1))
        out = out.view(self.batch_size,-1,self.d_model) + multi_head_output.squeeze(2)
        layer_normalization2 = nn.LayerNorm(out.size()[1:], elementwise_affine=False)
        out = layer_normalization2(out)
        out = torch.mean(out,1).view(self.batch_size,-1) #not really sure if mean is the best thing, BERT and VTN use the CLS token
        return out
    
    def get_angles(self,pos, i, d_model):
        angle_rates = 1 / np.power(10000, (2 * (i//2)) / np.double(self.d_model))
        return pos * angle_rates

    def positionalencoding(self,position):
        # NOTE the code is from https://www.tensorflow.org/tutorials/text/transformer, not ours
        angle_rads = self.get_angles(np.arange(position)[:, np.newaxis],np.arange(self.d_model)[np.newaxis, :],self.d_model)
  
        # apply sin to even indices in the array; 2i
        angle_rads[:, 0::2] = np.sin(angle_rads[:, 0::2])
  
        # apply cos to odd indices in the array; 2i+1
        angle_rads[:, 1::2] = np.cos(angle_rads[:, 1::2])
    
        pos_encoding = angle_rads[np.newaxis, ...]
        pos_encoding = torch.tensor(pos_encoding).cuda()
        return pos_encoding
