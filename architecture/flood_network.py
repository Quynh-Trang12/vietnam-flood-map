"""Compact U-Net baseline, initialized from existing ImageNet ResNet-18 weights."""
import sys
from pathlib import Path
import torch
from torch import nn

PROJECT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(PROJECT/'04-Implementation/Training/Sprint1-Training'))
from change_unet import FloodChangeUNet,Block


class Network(FloodChangeUNet):
    def __init__(self,channels=9):
        super().__init__()
        self.encoder.conv1=nn.Conv2d(channels,64,7,stride=2,padding=3,bias=False)
        self.full=Block(32+channels,16)
        self.input_mean=torch.zeros(1,channels,1,1);self.input_std=torch.ones(1,channels,1,1)


def initialize(channels,stats,device):
    net=Network(channels).to(device)
    path=PROJECT/'03-Data-and-Models/Data/Processed/Sprint1/pretrained/resnet18-f37072fd.pth'
    initial=torch.load(path,map_location='cpu',weights_only=True)
    initial={k:v for k,v in initial.items() if not k.startswith('fc.')}
    rgb=initial['conv1.weight'];radar=rgb.mean(1,keepdim=True).repeat(1,2,1,1)*1.5
    if channels==9:
        extra=torch.zeros(rgb.shape[0],7,7,7);extra[:,:3]=rgb[:,[2,1,0]]*.5
        extra[:,3:6]=rgb.mean(1,keepdim=True).repeat(1,3,1,1)*.5
        initial['conv1.weight']=torch.cat([radar,extra],dim=1)
    else:initial['conv1.weight']=radar
    net.encoder.load_state_dict(initial,strict=True)
    net.input_mean.copy_(torch.tensor(stats['mean'][:channels],dtype=torch.float32,device=device).view(1,channels,1,1))
    net.input_std.copy_(torch.tensor(stats['std'][:channels],dtype=torch.float32,device=device).view(1,channels,1,1))
    return net
