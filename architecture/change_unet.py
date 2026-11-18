"""ImageNet-initialized U-Net for two-pass water segmentation and flood change."""
import numpy as np
import torch
from torch import nn
from torchvision.models import resnet18

class Block(nn.Sequential):
    def __init__(self,inputs,outputs):
        super().__init__(nn.Conv2d(inputs,outputs,3,padding=1,bias=False),nn.GroupNorm(8,outputs),nn.ReLU(),
                         nn.Conv2d(outputs,outputs,3,padding=1,bias=False),nn.GroupNorm(8,outputs),nn.ReLU())
class FloodChangeUNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder=resnet18(weights=None)
        self.encoder.conv1=nn.Conv2d(6,64,7,stride=2,padding=3,bias=False)
        self.encoder.fc=nn.Identity()
        self.d3=Block(512+256,256);self.d2=Block(256+128,128)
        self.d1=Block(128+64,64);self.d0=Block(64+64,32)
        self.full=Block(32+6,16);self.head=nn.Conv2d(16,3,1)
        self.register_buffer('input_mean',torch.zeros(1,6,1,1))
        self.register_buffer('input_std',torch.ones(1,6,1,1))
    def train(self,mode=True):
        super().train(mode)
        # Freeze pretrained encoder batch statistics for the small batch size.
        for module in self.encoder.modules():
            if isinstance(module,nn.BatchNorm2d):module.eval()
        return self
    def forward(self,x):
        x=(x-self.input_mean)/self.input_std
        e=self.encoder
        stem=e.relu(e.bn1(e.conv1(x)))
        a=e.layer1(e.maxpool(stem));b=e.layer2(a);c=e.layer3(b);d=e.layer4(c)
        def up(value,skip):return nn.functional.interpolate(value,size=skip.shape[-2:],mode='bilinear',align_corners=False)
        d=self.d3(torch.cat([up(d,c),c],1));d=self.d2(torch.cat([up(d,b),b],1))
        d=self.d1(torch.cat([up(d,a),a],1));d=self.d0(torch.cat([up(d,stem),stem],1))
        return self.head(self.full(torch.cat([up(d,x),x],1)))
def create_model():return FloodChangeUNet()

def normalize(raw):
    valid=np.isfinite(raw).all(0)&(raw>0).all(0)
    image=(np.clip(10*np.log10(np.maximum(raw,1e-8)),-40,10)+40)/50
    image=np.nan_to_num(image,nan=0,posinf=1,neginf=0).astype('float32')
    image[:,~valid]=0
    return image,valid

def make_features(pre,post):
    a,va=normalize(pre);b,vb=normalize(post);valid=va&vb
    image=np.concatenate([a,b,b-a],axis=0);image[:,~valid]=0
    return image,valid
def predict_mask(pre,post,valid,model,device,patch=256):
    image,observed=make_features(pre,post);ok=valid&observed
    image[:,~ok]=0;h,w=ok.shape;output=np.full((h,w),255,dtype='uint8');model.eval()
    with torch.inference_mode():
        for y in range(0,h,patch):
            for x in range(0,w,patch):
                tensor=torch.from_numpy(image[:,y:y+patch,x:x+patch].copy())[None].to(device)
                label=model(tensor).argmax(1)[0].cpu().numpy()
                output[y:y+patch,x:x+patch]=(label==2).astype('uint8')
    output[~ok]=255
    return output
