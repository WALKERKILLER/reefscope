"""Load the complete trained coral model from a single safetensors file.

Includes the frozen EPFL-ECEO CoralscapesV2 SegFormer-B5, trained nonbleached
head and automatic image-feature guard. Original v2 inference functions are
copied unchanged from the verified training kit; no external weight directory
or adaptation.pt is needed. Requires the supplied pinned Transformers version.
Source model license and notices are shipped alongside the checkpoint.
"""
import argparse
import hashlib
import json
from contextlib import nullcontext
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.nn import functional as F
from safetensors import safe_open
from safetensors.torch import load_file
from transformers import SegformerConfig, SegformerForSemanticSegmentation, SegformerImageProcessor


class CoralHead(nn.Module):
    def __init__(self, channels, width=64):
        super().__init__()
        self.projections = nn.ModuleList([
            nn.Sequential(nn.Conv2d(c, width, 1), nn.GroupNorm(8, width), nn.GELU()) for c in channels
        ])
        self.fuse = nn.Sequential(nn.Conv2d(width * len(channels), width, 3, padding=1),
                                  nn.GroupNorm(8, width), nn.GELU(), nn.Conv2d(width, 1, 1))

    def forward(self, features):
        shape = features[0].shape[-2:]
        projected = [F.interpolate(layer(x), shape, mode="bilinear", align_corners=False)
                     for layer, x in zip(self.projections, features)]
        return self.fuse(torch.cat(projected, dim=1))


def fingerprint(base):
    h = hashlib.sha256()
    for name, value in base.state_dict().items():
        h.update(name.encode())
        h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def amp_context(device, precision):
    if precision == "fp32":
        return nullcontext()
    if precision != "bf16" or torch.device(device).type != "cuda":
        raise ValueError("bf16 precision requires a CUDA device")
    with torch.cuda.device(device):
        if not torch.cuda.is_bf16_supported():
            raise ValueError("Selected GPU/runtime does not support BF16")
    return torch.autocast(device_type="cuda", dtype=torch.bfloat16)


def resize_short(image, short_edge, resample):
    scale = short_edge / min(image.size)
    return image.resize((round(image.width * scale), round(image.height * scale)), resample)


def starts(size, tile):
    result = list(range(0, max(size - tile, 0) + 1, max(tile // 2, 1)))
    if result[-1] != size - tile:
        result.append(size - tile)
    return result


@torch.no_grad()
def predict_probability(base, processor, head, image, crop, device, precision="fp32"):
    base.eval()
    head.eval()
    original_size = image.size
    image = resize_short(image.convert("RGB"), crop, Image.Resampling.BILINEAR)
    total = torch.zeros((image.height, image.width), dtype=torch.float32)
    count = torch.zeros_like(total)
    for y in starts(image.height, crop):
        for x in starts(image.width, crop):
            piece = image.crop((x, y, x + crop, y + crop))
            pixels = processor(images=piece, do_resize=False, return_tensors="pt")["pixel_values"].to(device)
            with amp_context(device, precision):
                features = base.segformer(pixels, output_hidden_states=True, return_dict=True).hidden_states
                logits = head(features)
            score = F.interpolate(logits.float(), (crop, crop), mode="bilinear", align_corners=False)
            total[y:y+crop, x:x+crop] += score[0, 0].sigmoid().cpu()
            count[y:y+crop, x:x+crop] += 1
    result = F.interpolate((total / count)[None, None], (original_size[1], original_size[0]),
                           mode="bilinear", align_corners=False)[0, 0]
    return result.numpy()


def configure():
    torch.set_num_threads(6)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


@torch.inference_mode()
def original_predict(base, processor, image, device="cuda"):
    """Same resize-to-multiple-of-32 and FP32 source argmax as supplied bundle."""
    image = image.convert("RGB")
    w, h = image.size
    scale = min(1., 1024 / max(w, h))
    size = (max(32, round(w * scale / 32) * 32), max(32, round(h * scale / 32) * 32))
    pixels = processor(images=image.resize(size, Image.Resampling.BILINEAR), do_resize=False,
                       return_tensors="pt")["pixel_values"].to(device)
    outputs = base(pixel_values=pixels, output_hidden_states=True, return_dict=True)
    logits = outputs.logits.float()
    best = torch.full((h, w), -torch.inf, device=device)
    labels = torch.zeros((h, w), dtype=torch.uint8, device=device)
    for start in range(0, 96, 8):
        chunk = F.interpolate(logits[:, start:start+8], (h, w), mode="bilinear", align_corners=False)[0]
        value, index = chunk.max(0)
        replace = value > best
        labels[replace] = (index[replace] + start).to(torch.uint8)
        best = torch.maximum(best, value)
    source = labels.cpu().numpy()
    table = np.ones(96, dtype=np.uint8)
    table[base.coral_bundle_config["bleached_source_ids"]] = 2
    parts = []
    for feature in outputs.hidden_states:
        for value in [feature.float().mean((2, 3)), feature.float().std((2, 3), correction=0)]:
            parts.append(F.normalize(value, dim=1))
    embedding = F.normalize(torch.cat(parts, dim=1), dim=1)[0].cpu().numpy()
    return table[source], embedding


def guard_score(embedding, local_reference, official_reference, k=3):
    x = np.asarray(embedding, dtype=np.float32)
    def nearest(ref):
        similarity = np.asarray(ref, dtype=np.float32) @ x
        n = min(k, len(similarity))
        return float(np.partition(similarity, -n)[-n:].mean())
    return nearest(local_reference) - nearest(official_reference)


def refine(original, probability, threshold, activate=True):
    if original.shape != probability.shape or not np.isfinite(probability).all():
        raise ValueError("Invalid refinement probability")
    if (not np.isin(original, [0, 1, 2, 255]).all() or not 0 <= threshold <= 1
            or np.any((probability < 0) | (probability > 1))):
        raise ValueError("Invalid class encoding/threshold")
    result = original.copy()
    if activate:
        eligible = (original == 0) | (original == 1)
        result[eligible] = (probability[eligible] >= threshold).astype(np.uint8)
    if not np.array_equal(result == 2, original == 2):
        raise AssertionError("Changed bleaching decisions")
    return result


def active_score(record, embedding):
    score = guard_score(embedding, record["guard_local_reference"].numpy(), record["guard_official_reference"].numpy())
    return score > record["guard_threshold"], score


@torch.inference_mode()
def infer(record, base, processor, head, image, device, original=None, embedding=None):
    if original is None or embedding is None:
        original, embedding = original_predict(base, processor, image, device)
    active, score = active_score(record, embedding)
    if active:
        probability = predict_probability(base, processor, head, image, record["crop"], device, record["precision"])
        result = refine(original, probability, record["threshold"])
    else:
        result = original.copy()
    return result, original, {"guard_active": active, "guard_score": score}


class CoralModel:
    """Inference model; model weights and configuration come from one file."""
    def __init__(self,weights,device='cuda'):
        configure()
        self.device=device
        with safe_open(str(weights),framework='pt',device='cpu') as stream:
            metadata=stream.metadata()
        if not metadata or 'coral_final' not in metadata:raise ValueError('Not a complete coral checkpoint')
        self.config=json.loads(metadata['coral_final'])
        if self.config['format']!='reef-coral-final/v1':raise ValueError('Unsupported coral format')
        state=load_file(str(weights),device='cpu')
        raw=self.config['source_model_config']
        self.base=SegformerForSemanticSegmentation(SegformerConfig.from_dict(raw['source_config']))
        self.base.load_state_dict({k[5:]:v for k,v in state.items() if k.startswith('base.')},strict=True)
        self.base.coral_bundle_config=raw
        self.base.requires_grad_(False)
        self.base.eval()
        if fingerprint(self.base)!=self.config['inference']['base_sha256']:raise ValueError('Base fingerprint mismatch')
        self.base.to(device)
        self.head=CoralHead(self.config['inference']['channels'])
        self.head.load_state_dict({k[5:]:v for k,v in state.items() if k.startswith('head.')},strict=True)
        self.head.requires_grad_(False)
        self.head.eval()
        self.head.to(device)
        expected={'base.'+k for k in self.base.state_dict()}|{'head.'+k for k in self.head.state_dict()}|{'guard.local_reference','guard.official_reference'}
        if set(state)!=expected:raise ValueError('Unexpected checkpoint tensor names')
        self.processor=SegformerImageProcessor.from_dict(self.config['preprocessor_config'])
        self.record=dict(self.config['inference'])
        self.record['guard_local_reference']=state['guard.local_reference']
        self.record['guard_official_reference']=state['guard.official_reference']

    @torch.inference_mode()
    def predict_with_details(self,image):
        return infer(self.record,self.base,self.processor,self.head,image.convert('RGB'),self.device)

    def predict(self,image):
        """Return uint8 HxW IDs: 0 background, 1 nonbleached, 2 bleached."""
        return self.predict_with_details(image)[0]


def main():
    parser=argparse.ArgumentParser(description='Inference from one complete trained coral checkpoint')
    parser.add_argument('--weights',default=str(Path(__file__).with_name('coral_scs_enhanced_v2.safetensors')))
    sources=parser.add_mutually_exclusive_group(required=True)
    sources.add_argument('--image');sources.add_argument('--images')
    parser.add_argument('--out',required=True);parser.add_argument('--device',default='cuda')
    args=parser.parse_args()
    files=[Path(args.image)] if args.image else sorted(p for p in Path(args.images).rglob('*') if p.suffix.lower() in ['.jpg','.jpeg','.png','.bmp','.tif','.tiff'])
    if not files or len({p.stem for p in files})!=len(files):parser.error('Need images with unique filename stems')
    out=Path(args.out)
    if out.exists():raise FileExistsError('Choose a new output directory')
    model=CoralModel(args.weights,args.device)
    out.mkdir(parents=True)
    for name in ['labels','colors','overlays']:(out/name).mkdir()
    palette=np.array([[0,0,0],[0,160,70],[255,255,255]],dtype=np.uint8)
    results=[]
    for i,path in enumerate(files):
        with Image.open(path) as source:
            image=source.convert('RGB')
            mask,baseline,detail=model.predict_with_details(image)
            if not np.isin(mask,[0,1,2]).all() or not np.array_equal(mask==2,baseline==2):raise AssertionError('Invalid output or bleaching change')
            Image.fromarray(mask).save(out/'labels'/(path.stem+'.png'))
            colors=palette[mask]
            Image.fromarray(colors).save(out/'colors'/(path.stem+'.png'))
            overlay=np.asarray(image).copy();fg=mask!=0
            overlay[fg]=np.rint(.6*overlay[fg]+.4*colors[fg]).astype(np.uint8)
            preview=Image.fromarray(overlay);preview.thumbnail((1600,1600))
            preview.save(out/'overlays'/(path.stem+'.jpg'),quality=92)
        results.append({'image':path.name,'bleached_changed_pixels':0,**detail})
        print(f'{i+1}/{len(files)} {path.name}: saved',flush=True)
    (out/'prediction-report.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
